"""Zicht op de toestand, zonder in te loggen.

Aanleiding: taak #1 van padelmq-ai-product-engine stond stil in de wachtrij
terwijl de lus leefde, intake werkte en antwoorden verwerkt werden. Van
buitenaf was "wachtrij" niet te onderscheiden van "draait", en de enige manier
om het te zien was de logs van de hostingdienst openen — precies wat de
eigenaar niet hoeft te doen.
"""

import unittest

from tests.base import TempCase

from orchestrator.statusbord import LABEL, bouw, publiceer


class Bord(TempCase):
    def setUp(self):
        super().setUp()
        self.make_project("demo")
        self.db.ensure_project("demo")
        self.scope = self.db.scope("demo")

    def test_toont_status_en_laatste_gebeurtenis_per_taak(self):
        from orchestrator.models import TaskStatus

        tid = self.scope.add_task("Werk CLAUDE.md bij", acceptance=["werkt"])
        self.scope.set_task(tid, status=TaskStatus.QUEUED.value)
        self.scope.log("hersteld", {"detail": "teruggezet in de wachtrij"}, task_id=tid)

        tekst = bouw(self.db, self.settings, ["demo"])
        self.assertIn("Werk CLAUDE.md bij", tekst)
        self.assertIn("`queued`", tekst)
        self.assertIn("hersteld", tekst)
        self.assertIn("teruggezet in de wachtrij", tekst)

    def test_toont_waar_een_taak_op_wacht(self):
        from orchestrator.models import TaskStatus

        tid = self.scope.add_task("Wacht", acceptance=["werkt"])
        qid = self.scope.add_question("Welke kleur?", "block", "vv", task_id=tid)
        self.scope.set_task(tid, status=TaskStatus.BLOCKED.value, blocked_by_question=qid)

        tekst = bouw(self.db, self.settings, ["demo"])
        self.assertIn("`blocked`", tekst)
        self.assertIn(f"| {qid} |", tekst)

    def test_toont_de_uitgaven_tegen_de_grens(self):
        tid = self.scope.add_task("Duur", acceptance=["werkt"])
        self.scope.record_call(phase="implement", role="uitvoerder", model="m",
                               tokens_in=1, tokens_out=1, cached_in=0,
                               cost_eur=1.25, task_id=tid)
        tekst = bouw(self.db, self.settings, ["demo"])
        self.assertIn("1.2500", tekst)

    def test_een_leeg_project_zegt_dat_ook(self):
        self.assertIn("geen taken", bouw(self.db, self.settings, ["demo"]))


class Publicatie(unittest.TestCase):
    class Client:
        def __init__(self, bestaand=None):
            self.bestaand = bestaand or []
            self.aangemaakt = []
            self.bijgewerkt = []

        def issues_with_label(self, repo, label):
            return list(self.bestaand)

        def create_issue(self, repo, titel, body, labels):
            self.aangemaakt.append((titel, body, labels))
            return 42

        def update_issue_body(self, repo, nummer, body):
            self.bijgewerkt.append((nummer, body))

    def test_eerste_keer_wordt_het_issue_aangemaakt(self):
        c = self.Client()
        self.assertEqual(publiceer(c, "eigenaar/repo", "tekst"), 42)
        self.assertEqual(len(c.aangemaakt), 1)
        self.assertIn(LABEL, c.aangemaakt[0][2])

    def test_daarna_wordt_het_bijgewerkt_en_niet_becommentarieerd(self):
        """Een bord dat elke ronde een reactie plaatst is binnen een dag onleesbaar."""
        c = self.Client(bestaand=[{"number": 7}])
        self.assertEqual(publiceer(c, "eigenaar/repo", "nieuwe tekst"), 7)
        self.assertEqual(c.bijgewerkt, [(7, "nieuwe tekst")])
        self.assertEqual(c.aangemaakt, [])

    def test_zonder_repo_gebeurt_er_niets(self):
        c = self.Client()
        self.assertIsNone(publiceer(c, "", "tekst"))
        self.assertEqual(c.aangemaakt, [])


if __name__ == "__main__":
    unittest.main()
