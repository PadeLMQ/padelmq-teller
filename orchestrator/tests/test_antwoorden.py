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
        self._next_id += 1
        return self._next_id

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


class EigenReactiesTellenNietAlsAntwoord(TempCase):
    """De orkestrator schrijft met de token van de eigenaar.

    Zijn eigen terugkoppeling komt daardoor bij de volgende ronde terug als een
    reactie van de eigenaar. Zonder deze grens leest hij zijn eigen tekst als
    antwoord op zijn eigen vraag. Dat gebeurde echt, op issues #3, #4 en #5 van
    padelmq-ai-product-engine: "Ik leg dit vast als: Ik leg dit vast als: ...",
    gevolgd door een afbreking die niemand had gegeven.
    """

    class LuisterendeGitHub:
        """Een client die zijn eigen reacties terugmeldt, zoals GitHub doet."""

        def __init__(self):
            self.comments = []
            self.posted = []
            self.closed = []
            self._next_id = 1000

        def owner_comments(self, repo, number):
            return list(self.comments)

        def comment(self, repo, number, body):
            self._next_id += 1
            self.posted.append(body)
            # Precies het punt: de orkestrator is de eigenaar, dus zijn reactie
            # komt in dezelfde lijst terecht als die van een mens.
            self.comments.append({"id": self._next_id, "body": body,
                                  "user": {"login": "eigenaar"},
                                  "author_association": "OWNER"})
            return self._next_id

        def close_issue(self, repo, number):
            self.closed.append(number)

        def add_owner_comment(self, body):
            self._next_id += 1
            self.comments.append({"id": self._next_id, "body": body,
                                  "user": {"login": "eigenaar"},
                                  "author_association": "OWNER"})

    def setUp(self):
        super().setUp()
        self.project = self.make_project("demo")
        self.project.github_repo = "eigenaar/demo"
        self.scope = self.db.scope("demo")
        self.task_id = self.scope.add_task("Wachtende taak", acceptance=["werkt"])
        self.question_id = self.scope.add_question(
            "Moet README.md dezelfde verduidelijking krijgen?", "block", "vv-1",
            task_id=self.task_id)
        self.scope.set_question(self.question_id, issue_number=42)
        self.scope.set_task(self.task_id, status=TaskStatus.BLOCKED.value,
                            blocked_by_question=self.question_id)

    def test_een_tweede_ronde_leest_de_eigen_terugkoppeling_niet_als_antwoord(self):
        client = self.LuisterendeGitHub()
        client.add_owner_comment("JA. Maak README.md consistent.")

        process_answers(scope=self.scope, project=self.project, client=client)
        na_ronde_1 = len(client.posted)
        self.assertEqual(na_ronde_1, 1, "de eerste ronde hoort één keer terug te koppelen")

        # Tweede ronde: er is geen nieuwe reactie van een mens bijgekomen.
        process_answers(scope=self.scope, project=self.project, client=client)
        self.assertEqual(len(client.posted), na_ronde_1,
                         "de orkestrator reageerde op zijn eigen reactie")

        for _ in range(3):
            process_answers(scope=self.scope, project=self.project, client=client)
        self.assertEqual(len(client.posted), na_ronde_1,
                         "de lus voedt zichzelf nog steeds")
        self.assertNotIn("Ik leg dit vast als: Ik leg dit vast als:",
                         "\n".join(client.posted))

    def test_een_echte_bevestiging_wordt_wel_opgepakt(self):
        """De grens mag geen mens buitensluiten."""
        client = self.LuisterendeGitHub()
        client.add_owner_comment("JA. Maak README.md consistent.")
        process_answers(scope=self.scope, project=self.project, client=client)

        client.add_owner_comment("Ja, klopt.")
        process_answers(scope=self.scope, project=self.project, client=client)

        rij = self.scope.question(self.question_id)
        self.assertEqual(rij["status"], "answered",
                         "de bevestiging van een mens werd niet verwerkt")
        self.assertIn(42, client.closed)


class Paginering(TempCase):
    """Een antwoord op plek 31 is geen antwoord dat er niet is.

    GitHub geeft standaard 30 items per pagina. owner_comments() haalde er maar
    één op. Op issue #4 van padelmq-ai-product-engine stond de beslissing van de
    eigenaar op plek 32: de orkestrator wachtte op iets dat er al ruim tien
    minuten stond.

    De blinde vlek ontstaat pas als een gesprek lang genoeg wordt, dus precies
    bij de issues waar het meeste gebeurd is. Daarom staat hij hier vast.
    """

    class GepagineerdeAPI:
        """Bootst GitHub na: 30 per pagina tenzij er per_page wordt gevraagd."""

        def __init__(self, aantal: int):
            self.items = [{"id": 1000 + i, "body": f"reactie {i}",
                           "user": {"login": "eigenaar"},
                           "author_association": "OWNER"} for i in range(aantal)]
            self.opgevraagd: list[str] = []

        def __call__(self, methode, pad, payload=None):
            self.opgevraagd.append(pad)
            import urllib.parse as up
            vraag = up.parse_qs(up.urlparse(pad).query)
            per = int(vraag.get("per_page", [30])[0])
            pagina = int(vraag.get("page", [1])[0])
            begin = (pagina - 1) * per
            return self.items[begin:begin + per]

    def _client(self, aantal):
        from orchestrator.notify.github import GitHubClient

        client = GitHubClient(token="x")
        api = self.GepagineerdeAPI(aantal)
        client._request = api
        return client, api

    def test_alle_reacties_komen_mee_ook_voorbij_de_eerste_pagina(self):
        client, _ = self._client(32)
        gevonden = client.owner_comments("eigenaar/repo", 4)
        self.assertEqual(len(gevonden), 32,
                         "reacties voorbij de eerste pagina werden niet gezien")
        self.assertEqual(gevonden[-1]["id"], 1031)

    def test_precies_dertig_haalt_geen_overbodige_pagina_op(self):
        """Een volle pagina van 100 vraagt de volgende op; 30 is niet vol."""
        client, api = self._client(30)
        self.assertEqual(len(client.owner_comments("eigenaar/repo", 4)), 30)
        self.assertEqual(len(api.opgevraagd), 1)

    def test_meer_dan_honderd_werkt_ook(self):
        client, _ = self._client(250)
        self.assertEqual(len(client.owner_comments("eigenaar/repo", 4)), 250)

    def test_geen_reacties_is_geen_fout(self):
        client, _ = self._client(0)
        self.assertEqual(client.owner_comments("eigenaar/repo", 4), [])

    def test_opdrachten_ophalen_pagineert_ook(self):
        """Dezelfde fout zou een opdracht onzichtbaar maken."""
        client, _ = self._client(45)
        for item in client._request.items:
            item["labels"] = [{"name": "orch:task"}]
        self.assertEqual(len(client.issues_with_label("eigenaar/repo", "orch:task")), 45)


class VervallenVraag(TempCase):
    """Een vraag die niet te beantwoorden is moet kunnen vervallen.

    Vraag #7 van padelmq-ai-product-engine bood als enige optie de broncode-regel
    met een verzonnen EAN erin. Het enige beantwoordbare antwoord was daarmee een
    bevestiging van precies wat die poort moest tegenhouden. Zo'n vraag mag niet
    beantwoord worden om er vanaf te zijn: er mag nergens komen te staan dat de
    verzonnen waarde klopt.
    """

    class Client:
        def __init__(self, gemarkeerd=()):
            self.gemarkeerd = list(gemarkeerd)
            self.posted = []
            self.closed = []

        def issues_with_label(self, repo, label):
            from orchestrator.answers import VERVALLABEL
            return [{"number": n} for n in self.gemarkeerd] if label == VERVALLABEL else []

        def owner_comments(self, repo, number):
            return []

        def comment(self, repo, number, body):
            self.posted.append((number, body)); return 999

        def close_issue(self, repo, number):
            self.closed.append(number)

    def setUp(self):
        super().setUp()
        self.project = self.make_project("demo")
        self.project.github_repo = "eigenaar/demo"
        self.scope = self.db.scope("demo")
        self.task_id = self.scope.add_task("Variant-resolver", acceptance=["werkt"])
        self.qid = self.scope.add_question(
            "Waar komt de waarde 8712345678906 vandaan?", "block", "vv-ean",
            task_id=self.task_id)
        self.scope.set_question(self.qid, issue_number=24)
        self.scope.set_task(self.task_id, status=TaskStatus.BLOCKED.value,
                            blocked_by_question=self.qid)

    def _verval(self, client):
        from orchestrator.answers import verval_gemarkeerde_vragen
        return verval_gemarkeerde_vragen(scope=self.scope, project=self.project,
                                         client=client)

    def test_de_taak_gaat_terug_in_de_wachtrij(self):
        acties = self._verval(self.Client([24]))
        self.assertTrue(acties)
        self.assertEqual(self.scope.task(self.task_id)["status"], TaskStatus.QUEUED.value)
        self.assertEqual(self.scope.question(self.qid)["status"], "vervallen")
        self.assertIn(24, self.Client([24]).gemarkeerd)

    def test_de_rem_op_herhaalde_opdrachten_gaat_mee_weg(self):
        """Anders is de hervatting zonder effect.

        Dat gebeurde: taak 3 ging terug in de wachtrij en werd binnen veertig
        seconden opnieuw geblokkeerd, omdat prompt en branch onveranderd waren
        en de rem die toestand nog kende.
        """
        self.scope.remember_signature(self.task_id, "impl:onveranderd")
        self.assertTrue(self.scope.signature_seen(self.task_id, "impl:onveranderd"))

        self._verval(self.Client([24]))

        self.assertFalse(self.scope.signature_seen(self.task_id, "impl:onveranderd"))

    def test_er_wordt_geen_beslissing_en_geen_kennisitem_vastgelegd(self):
        """Dit is de kern: nergens mag komen te staan dat de waarde klopt."""
        self._verval(self.Client([24]))

        rij = self.scope.question(self.qid)
        self.assertIsNone(rij["answer"], "er is een antwoord vastgelegd")
        items = self.project.knowledge.load()
        self.assertEqual(items, {}, "er is een kennisitem aangemaakt")

    def test_de_audittrail_zegt_dat_hij_vervallen_is_en_waarom(self):
        self._verval(self.Client([24]))
        soorten = {e["kind"] for e in self.scope.events(limit=50)}
        self.assertIn("vraag-vervallen", soorten)
        self.assertNotIn("beslissing", soorten)

    def test_zonder_label_gebeurt_er_niets(self):
        self.assertEqual(self._verval(self.Client([])), [])
        self.assertEqual(self.scope.task(self.task_id)["status"], TaskStatus.BLOCKED.value)

    def test_een_ander_gemarkeerd_issue_raakt_deze_vraag_niet(self):
        self.assertEqual(self._verval(self.Client([99])), [])
        self.assertEqual(self.scope.question(self.qid)["status"], "open")
