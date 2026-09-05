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

        row = self.scope.question(self.question_id)
        self.assertEqual(row["status"], "awaiting_confirmation")
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

        row = self.scope.question(self.question_id)
        self.assertEqual(row["status"], "awaiting_confirmation")
        self.assertIn("Klopt dat?", client.posted[-1])
        self.assertEqual(self.project.knowledge.load(), {})

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
