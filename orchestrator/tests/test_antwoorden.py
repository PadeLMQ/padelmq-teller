"""Antwoorden komen alleen van jou, en pas na bevestiging worden ze waarheid."""

import json

from orchestrator.answers import answer_locally, process_answers
from orchestrator.models import ItemStatus, TaskStatus
from tests.base import TempCase


class FakeGitHub:
    def __init__(self, comments=None):
        self.comments = comments or []
        self.posted = []
        self.closed = []
        self._next_id = 1000

    def owner_comments(self, repo, number):
        return self.comments

    def comment(self, repo, number, body):
        self.posted.append(body)

    def close_issue(self, repo, number):
        self.closed.append(number)

    def add_owner_comment(self, body):
        self._next_id += 1
        self.comments.append({"id": self._next_id, "body": body,
                              "user": {"login": "eigenaar"}, "author_association": "OWNER"})


class Antwoorden(TempCase):
    def setUp(self):
        super().setUp()
        self.project = self.make_project("demo")
        self.project.github_repo = "eigenaar/demo"
        self.scope = self.db.scope("demo")
        self.task_id = self.scope.add_task("Wachtende taak", acceptance=["werkt"])
        self.question_id = self.scope.add_question(
            "Tonen we btw inclusief of exclusief?", "block", "btw incl of excl",
            task_id=self.task_id,
        )
        self.scope.set_question(self.question_id, issue_number=42)
        self.scope.set_task(self.task_id, status=TaskStatus.BLOCKED.value,
                            blocked_by_question=self.question_id)

    def test_eerste_antwoord_wordt_eerst_teruggekoppeld(self):
        client = FakeGitHub()
        client.add_owner_comment("Inclusief btw.")
        process_answers(scope=self.scope, project=self.project, client=client)

        # De toestand van het gesprek leeft in de antwoordsessie, de enige poort
        # waar alle kanalen doorheen gaan. De vraag zelf blijft open tot er
        # werkelijk iets vastligt, en blijft dus meegenomen worden bij het pollen.
        sessie = self.scope.open_answer_session(self.question_id)
        self.assertIsNotNone(sessie, "er is geen antwoordsessie geopend")
        self.assertEqual(sessie["state"], "awaiting_confirmation")
        self.assertIn(
            self.question_id, [r["id"] for r in self.scope.pending_questions()],
            "de vraag wordt niet meer gepolld",
        )
        self.assertIn("Klopt dat?", client.posted[0])
        self.assertEqual(
            self.scope.task(self.task_id)["status"], TaskStatus.BLOCKED.value,
            "de taak mag pas na bevestiging hervatten",
        )
        self.assertEqual(self.project.knowledge.load(), {},
                         "nog niets in de kennisbasis voor de bevestiging")

    def test_pas_na_bevestiging_wordt_het_een_beslissing(self):
        client = FakeGitHub()
        client.add_owner_comment("Inclusief btw.")
        process_answers(scope=self.scope, project=self.project, client=client)
        client.add_owner_comment("ja")
        process_answers(scope=self.scope, project=self.project, client=client)

        row = self.scope.question(self.question_id)
        self.assertEqual(row["status"], "answered")
        item_id = json.loads(row["answer"])["decision"]
        item = self.project.knowledge.get(item_id)
        self.assertEqual(item.status, ItemStatus.CONFIRMED)
        self.assertIn("Inclusief btw", item.body)
        self.assertEqual(self.scope.task(self.task_id)["status"], TaskStatus.QUEUED.value)
        self.assertEqual(client.closed, [42])

    def test_correctie_leidt_tot_een_nieuwe_terugkoppeling_niet_tot_een_keuze(self):
        client = FakeGitHub()
        client.add_owner_comment("Inclusief btw.")
        process_answers(scope=self.scope, project=self.project, client=client)
        client.add_owner_comment("Nee, exclusief btw voor zakelijke klanten.")
        process_answers(scope=self.scope, project=self.project, client=client)

        sessie = self.scope.open_answer_session(self.question_id)
        self.assertEqual(sessie["state"], "awaiting_confirmation")
        self.assertIn("Klopt dat?", client.posted[-1])
        self.assertEqual(self.project.knowledge.load(), {},
                         "een correctie mag nog niets vastleggen")

    def test_reacties_van_anderen_tellen_niet(self):
        client = FakeGitHub()
        client.comments.append({
            "id": 5, "body": "Doe maar inclusief.",
            "user": {"login": "iemandanders"}, "author_association": "NONE",
        })
        # owner_comments van de echte client filtert dit al; hier bewijzen we dat
        # de verwerking niets doet als er geen eigenaarreactie is.
        client.comments = []
        actions = process_answers(scope=self.scope, project=self.project, client=client)
        self.assertEqual(actions, [])
        self.assertEqual(self.scope.question(self.question_id)["status"], "open")

    def test_antwoord_via_de_opdrachtregel_hervat_de_taak(self):
        item_id = answer_locally(
            scope=self.scope, project=self.project,
            question_id=self.question_id, answer="Inclusief btw.",
        )
        self.assertEqual(self.project.knowledge.get(item_id).status, ItemStatus.CONFIRMED)
        self.assertEqual(self.scope.task(self.task_id)["status"], TaskStatus.QUEUED.value)


class KwaliteitspoortViaGitHub(TempCase):
    """De GitHub-route moet dezelfde poort gebruiken als de opdrachtregel.

    Eerder deed process_answers een eigen, soepeler bevestigingslus en omzeilde
    daarmee de regel van hoogstens één verduidelijking.
    """

    def setUp(self):
        super().setUp()
        self.project = self.make_project("poort")
        self.project.github_repo = "eigenaar/poort"
        self.scope = self.db.scope("poort")
        self.task_id = self.scope.add_task("Wachtende taak", acceptance=["werkt"])
        self.question_id = self.scope.add_question(
            "Tonen we btw inclusief of exclusief?", "block", "btw-vraag",
            options=["inclusief btw", "exclusief btw"], task_id=self.task_id,
        )
        self.scope.set_question(self.question_id, issue_number=7)
        self.scope.set_task(self.task_id, status=TaskStatus.BLOCKED.value,
                            blocked_by_question=self.question_id)

    def _process(self, client):
        return process_answers(scope=self.scope, project=self.project, client=client)

    def test_dubbelzinnig_antwoord_krijgt_een_verduidelijking(self):
        client = FakeGitHub()
        client.add_owner_comment("inclusief of eigenlijk exclusief, kies maar")
        self._process(client)

        self.assertEqual(self.project.knowledge.load(), {},
                         "een dubbelzinnig antwoord is toch vastgelegd")
        self.assertTrue(client.posted, "er is niet gereageerd")
        self.assertIn("enige verduidelijking", client.posted[-1])

    def test_na_de_verduidelijking_blijft_het_geblokkeerd(self):
        """Niet alsnog raden: dat is de kern van de hele opzet."""
        client = FakeGitHub()
        client.add_owner_comment("inclusief of eigenlijk exclusief, kies maar")
        self._process(client)
        client.add_owner_comment("weer allebei eigenlijk, inclusief en exclusief")
        self._process(client)

        self.assertEqual(self.project.knowledge.load(), {})
        self.assertEqual(
            self.scope.task(self.task_id)["status"], TaskStatus.BLOCKED.value,
            "de taak is hervat zonder bruikbaar antwoord",
        )
        self.assertNotIn(42, client.closed)

    def test_duidelijk_antwoord_hervat_exact_dezelfde_taak(self):
        client = FakeGitHub()
        client.add_owner_comment("inclusief btw")
        self._process(client)
        client.add_owner_comment("ja")
        self._process(client)

        row = self.scope.question(self.question_id)
        self.assertEqual(row["status"], "answered")
        item = self.project.knowledge.get(json.loads(row["answer"])["decision"])
        self.assertEqual(item.status, ItemStatus.CONFIRMED)
        self.assertEqual(self.scope.task(self.task_id)["status"], TaskStatus.QUEUED.value)
        self.assertEqual(client.closed, [7])

    def test_antwoord_belandt_nooit_bij_een_ander_project(self):
        """De koppeling loopt via de database, niet via de tekst van een issue."""
        ander = self.make_project("ander-project")
        ander.github_repo = "eigenaar/poort"      # zelfde repository, ander project
        ander_scope = self.db.scope("ander-project")
        ander_taak = ander_scope.add_task("Taak van een ander project",
                                          acceptance=["werkt"])
        ander_vraag = ander_scope.add_question(
            "Heel andere vraag?", "block", "andere-vraag", task_id=ander_taak)
        ander_scope.set_question(ander_vraag, issue_number=7)  # zelfde issuenummer
        ander_scope.set_task(ander_taak, status=TaskStatus.BLOCKED.value)

        client = FakeGitHub()
        client.add_owner_comment("inclusief btw")
        self._process(client)
        client.add_owner_comment("ja")
        self._process(client)

        self.assertEqual(
            ander_scope.question(ander_vraag)["status"], "open",
            "het antwoord is bij de vraag van een ander project beland",
        )
        self.assertEqual(
            ander_scope.task(ander_taak)["status"], TaskStatus.BLOCKED.value,
            "een taak in een ander project is onterecht hervat",
        )
        self.assertEqual(ander.knowledge.load(), {},
                         "de kennisbasis van een ander project is aangeraakt")
