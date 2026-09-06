"""Een taak die zonder vraag vastloopt moet weer op gang gebracht kunnen worden.

De rem op herhaalde betaalde opdrachten meldt zich zonder vraag. Er valt dus
niets te beantwoorden, en zonder een aparte knop staat de taak voorgoed stil.
Dat overkwam taak 3 van padelmq-ai-product-engine: twee blokmeldingen binnen
veertig seconden, geen van beide beantwoordbaar.
"""

from orchestrator.hervatten import HERVATLABEL, hervat_gemarkeerde_taken
from orchestrator.models import TaskStatus
from tests.base import TempCase


class Client:
    def __init__(self, gemarkeerd=(), eigenaar=True):
        self.gemarkeerd = list(gemarkeerd)
        self.eigenaar = eigenaar
        self.posted = []
        self.verwijderd = []

    def issues_with_label(self, repo, label):
        if label != HERVATLABEL:
            return []
        return [{"number": n, "labels": [{"name": HERVATLABEL}]} for n in self.gemarkeerd]

    def issue_author_is_owner(self, repo, issue):
        return self.eigenaar

    def comment(self, repo, number, body):
        self.posted.append((number, body))
        return 999

    def remove_label(self, repo, number, label):
        self.verwijderd.append((number, label))


class Hervatten(TempCase):
    def setUp(self):
        super().setUp()
        self.project = self.make_project("demo")
        self.project.github_repo = "eigenaar/demo"
        self.scope = self.db.scope("demo")
        self.task_id = self.scope.add_task("Variant-resolver", acceptance=["werkt"])
        self.scope.log("opdracht-aangenomen", {"issue": 9, "criteria": 3},
                       task_id=self.task_id)
        self.scope.set_task(self.task_id, status=TaskStatus.BLOCKED.value)

    def _hervat(self, client):
        return hervat_gemarkeerde_taken(scope=self.scope, project=self.project,
                                        client=client)

    def test_de_taak_gaat_terug_in_de_wachtrij(self):
        client = Client([9])
        acties = self._hervat(client)

        self.assertTrue(acties)
        self.assertEqual(self.scope.task(self.task_id)["status"], TaskStatus.QUEUED.value)

    def test_de_rem_op_herhaalde_opdrachten_wordt_gewist(self):
        """Zonder dit blokkeert dezelfde rem de taak meteen opnieuw."""
        self.scope.remember_signature(self.task_id, "impl:onveranderd")

        self._hervat(Client([9]))

        self.assertFalse(self.scope.signature_seen(self.task_id, "impl:onveranderd"))

    def test_alleen_de_handtekeningen_van_deze_taak(self):
        andere = self.scope.add_task("Andere taak", acceptance=["werkt"])
        self.scope.remember_signature(andere, "impl:van-een-andere-taak")

        self._hervat(Client([9]))

        self.assertTrue(self.scope.signature_seen(andere, "impl:van-een-andere-taak"))

    def test_er_wordt_niets_beantwoord_en_niets_besloten(self):
        self._hervat(Client([9]))

        soorten = {e["kind"] for e in self.scope.events(limit=50)}
        self.assertIn("taak-hervat", soorten)
        self.assertNotIn("beslissing", soorten)
        self.assertEqual(self.project.knowledge.load(), {})

    def test_het_label_gaat_er_weer_af(self):
        """Blijft het staan, dan hervat elke ronde opnieuw en betaalt elke ronde."""
        client = Client([9])
        self._hervat(client)

        self.assertIn((9, HERVATLABEL), client.verwijderd)

    def test_de_melding_zegt_dat_het_opnieuw_geld_kost(self):
        client = Client([9])
        self._hervat(client)

        tekst = client.posted[0][1]
        self.assertIn("opnieuw geld", tekst)

    def test_zonder_label_gebeurt_er_niets(self):
        self.assertEqual(self._hervat(Client([])), [])
        self.assertEqual(self.scope.task(self.task_id)["status"], TaskStatus.BLOCKED.value)

    def test_een_issue_zonder_taak_wordt_geweigerd(self):
        client = Client([404])
        acties = self._hervat(client)

        self.assertIn("geen taak gevonden", acties[0])
        self.assertEqual(self.scope.task(self.task_id)["status"], TaskStatus.BLOCKED.value)

    def test_alleen_de_eigenaar_mag_hervatten(self):
        """Anders kan een willekeurige lezer betaalde aanroepen uitlokken."""
        client = Client([9], eigenaar=False)
        acties = self._hervat(client)

        self.assertIn("niet van de eigenaar", acties[0])
        self.assertEqual(self.scope.task(self.task_id)["status"], TaskStatus.BLOCKED.value)
        self.assertEqual(client.posted, [])

    def test_een_afgeronde_taak_wordt_niet_opnieuw_gedaan(self):
        self.scope.set_task(self.task_id, status=TaskStatus.DONE.value)
        client = Client([9])

        self._hervat(client)

        self.assertEqual(self.scope.task(self.task_id)["status"], TaskStatus.DONE.value)
        self.assertIn((9, HERVATLABEL), client.verwijderd)


class TaakBijIssue(TempCase):
    """De koppeling issue -> taak komt uit het logboek, niet uit een tweede lijst."""

    def setUp(self):
        super().setUp()
        self.make_project("demo")
        self.scope = self.db.scope("demo")

    def test_de_koppeling_komt_uit_het_logboek(self):
        taak = self.scope.add_task("Een taak", acceptance=["werkt"])
        self.scope.log("opdracht-aangenomen", {"issue": 9}, task_id=taak)

        self.assertEqual(self.scope.task_for_issue(9), taak)

    def test_een_onbekend_issue_geeft_niets(self):
        self.assertIsNone(self.scope.task_for_issue(9))

    def test_taken_van_een_ander_project_tellen_niet_mee(self):
        self.make_project("ander")
        ander = self.db.scope("ander")
        taak = ander.add_task("Taak van een ander project", acceptance=["werkt"])
        ander.log("opdracht-aangenomen", {"issue": 9}, task_id=taak)

        self.assertIsNone(self.scope.task_for_issue(9))
