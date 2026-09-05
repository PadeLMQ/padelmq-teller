"""De zes garanties uit de herstelronde na taak #4.

Elk defect hieronder is werkelijk opgetreden en kostte een ronde of geld.
"""

import json
import unittest

from orchestrator.knowledge import ItemStatus, KnowledgeStore
from orchestrator.models import CheckResult, TaskStatus, VerificationResult

try:
    from tests.base import TempCase
except ImportError:  # pragma: no cover
    from base import TempCase

try:
    from tests.test_lus import GROEN, PAS_GROEN_MET_BESTAND, Lus
except ImportError:  # pragma: no cover
    from test_lus import GROEN, PAS_GROEN_MET_BESTAND, Lus


def _check(naam: str, groen: bool) -> CheckResult:
    return CheckResult(name=naam, command="x", exit_code=0 if groen else 1, output="")


class G1_SupersededKennisGeeftGeenValseBlock(TempCase):
    """Een verouderde regel mag geen tegenspraak meer veroorzaken."""

    def _store(self) -> KnowledgeStore:
        project = self.make_project("kb")
        store = project.knowledge
        (store.root / "voorkeuren.md").write_text(
            "# voorkeuren\n\n"
            "## VK-1 · Oude regel\n"
            "status: bevestigd\n"
            "datum: 2026-01-01\n"
            "bron: eerdere sessie\n\n"
            "Lint is bewust geen harde check.\n\n"
            "## VK-5 · Nieuwe regel\n"
            "status: bevestigd\n"
            "datum: 2026-09-05\n"
            "bron: D-005\n\n"
            "Lint is de vierde harde check.\n\n"
            "## VK-2 · Iets anders\n"
            "status: bevestigd\n"
            "datum: 2026-01-01\n"
            "bron: eerdere sessie\n\n"
            "Blijft gewoon staan.\n",
            encoding="utf-8",
        )
        return store

    def test_vervallen_item_is_niet_meer_citeerbaar(self):
        store = self._store()
        store.supersede("VK-1", "VK-5")
        items = store.load()
        self.assertIs(items["VK-1"].status, ItemStatus.SUPERSEDED)
        self.assertFalse(items["VK-1"].status.citable,
                         "een vervallen regel telt nog steeds als bron")
        self.assertTrue(items["VK-5"].status.citable)

    def test_de_historie_blijft_staan(self):
        store = self._store()
        store.supersede("VK-1", "VK-5")
        tekst = (store.root / "voorkeuren.md").read_text(encoding="utf-8")
        self.assertIn("Lint is bewust geen harde check", tekst,
                      "de oude tekst is gewist in plaats van gemarkeerd")
        self.assertIn("vervangt: VK-5", tekst)

    def test_supersede_wist_de_rest_van_het_bestand_niet(self):
        """Dit ging echt mis: re.S liet '.' over regelgrenzen lopen.

        Van de vijf items bleef er één regel over.
        """
        store = self._store()
        voor = len(store.load())
        store.supersede("VK-1", "VK-5")
        na = store.load()
        self.assertEqual(len(na), voor, "er zijn items verdwenen")
        self.assertIn("VK-2", na, "een ongerelateerd item is opgeslokt")
        self.assertIn("Blijft gewoon staan", (store.root / "voorkeuren.md").read_text())

    def test_vervallen_item_dat_niet_bestaat_geeft_een_fout(self):
        store = self._store()
        with self.assertRaises(Exception):
            store.supersede("BESTAAT-NIET", "VK-5")

    def test_de_vervangende_regel_wordt_wel_geladen(self):
        store = self._store()
        store.supersede("VK-1", "VK-5")
        context = store.as_prompt_context()
        self.assertIn("vierde harde check", context)


class G2_RodeBaselineHoudtDeReparatieNietTegen(unittest.TestCase):
    def test_al_rood_telt_niet_als_regressie(self):
        baseline = VerificationResult(checks=[_check("tests", True), _check("lint", False)])
        na = VerificationResult(checks=[_check("tests", True), _check("lint", False)])
        self.assertEqual(na.regressies(baseline), [])
        self.assertEqual([c.name for c in na.blijft_rood(baseline)], ["lint"])

    def test_gerepareerd_is_geen_regressie(self):
        baseline = VerificationResult(checks=[_check("lint", False)])
        na = VerificationResult(checks=[_check("lint", True)])
        self.assertEqual(na.regressies(baseline), [])
        self.assertEqual(na.blijft_rood(baseline), [])


class G3_NieuweRegressieWordtNooitWeggewuifd(unittest.TestCase):
    def test_groen_naar_rood_is_altijd_een_regressie(self):
        baseline = VerificationResult(checks=[_check("tests", True), _check("lint", False)])
        na = VerificationResult(checks=[_check("tests", False), _check("lint", False)])
        self.assertEqual([c.name for c in na.regressies(baseline)], ["tests"])

    def test_zonder_baseline_telt_elk_falen(self):
        na = VerificationResult(checks=[_check("tests", False)])
        self.assertEqual([c.name for c in na.regressies(None)], ["tests"])


class G4_PostCheckWordtHardAfgedwongen(Lus):
    def test_falende_post_check_levert_geen_pr(self):
        runner = self.build(checks={"tests": GROEN},
                            steps=[{"write": {"a.py": "x = 1\n"}}])
        self.project.post_checks = {"lint": "python3 -c \"import sys; sys.exit(1)\""}
        uitkomst = runner.run_task(self.task(runner))
        self.assertNotEqual(uitkomst.status, TaskStatus.PR_OPEN)

    def test_geslaagde_post_check_staat_in_de_uitslag(self):
        runner = self.build(checks={"tests": GROEN},
                            steps=[{"write": {"a.py": "x = 1\n"}}])
        self.project.post_checks = {"lint": GROEN}
        runner.run_task(self.task(runner))
        verificaties = [json.loads(r["payload"]) for r in self.scope.events(limit=50)
                        if r["kind"] == "verificatie"]
        self.assertIn("lint", {c["naam"] for c in verificaties[0]["checks"]})


class G5_GeenHerhaaldeBetaaldeBeoordeling(Lus):
    """Dezelfde diff, kennis, uitslag en criteria leveren hetzelfde oordeel op."""

    def test_de_handtekening_dekt_alles_wat_het_oordeel_bepaalt(self):
        from orchestrator.runner import review_handtekening as h

        basis = h("diff", "kennis", "uitslag", ["a", "b"])
        self.assertEqual(basis, h("diff", "kennis", "uitslag", ["b", "a"]),
                         "de vololgorde van criteria zou niets mogen uitmaken")
        for anders in (h("ander", "kennis", "uitslag", ["a", "b"]),
                       h("diff", "ander", "uitslag", ["a", "b"]),
                       h("diff", "kennis", "ander", ["a", "b"]),
                       h("diff", "kennis", "uitslag", ["a", "c"])):
            self.assertNotEqual(basis, anders,
                                "een verandering bleef buiten de handtekening")

    def test_ongewijzigde_toestand_gaat_niet_nog_eens_naar_de_beoordelaar(self):
        """Twee ronden met exact hetzelfde resultaat: de tweede is verspilling."""
        from orchestrator.adapters import ReviewResult
        from orchestrator.models import Verdict

        revise = ReviewResult(verdict=Verdict.REVISE, next_instruction="doe iets")
        runner = self.build(
            steps=[{"write": {"a.py": "x = 1\n"}}, {"write": {"a.py": "x = 1\n"}}],
            reviews=[revise, revise],
        )
        task_id = self.task(runner)

        eerste = runner.run_task(task_id)
        self.assertEqual(eerste.status, TaskStatus.QUEUED)
        na_een = self.reviewer.review_calls

        self.scope.set_task(task_id, status=TaskStatus.QUEUED.value,
                            review_feedback=None)
        tweede = runner.run_task(task_id)

        self.assertEqual(self.reviewer.review_calls, na_een,
                         "de beoordelaar is opnieuw betaald voor dezelfde toestand")
        self.assertEqual(tweede.status, TaskStatus.BLOCKED)
        events = [r for r in self.scope.events(limit=50)
                  if r["kind"] == "herhaalde-beoordeling"]
        self.assertTrue(events, "de tegengehouden herhaling is niet vastgelegd")

    def test_een_nieuwe_toestand_mag_wel_beoordeeld_worden(self):
        runner = self.build(steps=[{"write": {"a.py": "x = 1\n"}}])
        task_id = self.task(runner)
        self.scope.set_task(task_id, last_review_signature="review:iets-heel-anders")
        uitkomst = runner.run_task(task_id)
        self.assertEqual(uitkomst.status, TaskStatus.PR_OPEN)
        self.assertEqual(self.reviewer.review_calls, 1)


class G6_FeedbackBlijftPersistent(Lus):
    def test_verwerkte_feedback_overleeft_een_herstart(self):
        """In het geheugen bewaren volstond niet: een herstart is juist het geval."""
        from orchestrator.adapters import ReviewResult
        from orchestrator.models import Verdict
        from orchestrator.db import Database

        revise = ReviewResult(verdict=Verdict.REVISE, next_instruction="Doe X.")
        runner = self.build(
            steps=[{"write": {"a.py": "x = 1\n"}}, {"write": {"b.py": "y = 2\n"}}],
            reviews=[revise, revise],
        )
        task_id = self.task(runner)
        runner.run_task(task_id)          # feedback opgeslagen
        runner.run_task(task_id)          # feedback verwerkt en verplaatst

        verse = Database(self.settings.db_path)
        self.addCleanup(verse.close)
        taak = verse.scope("demo").task(task_id)
        self.assertIsNotNone(taak["last_review_feedback"],
                             "de verwerkte feedback is weg na een herstart")
        self.assertIn("Doe X.", taak["last_review_feedback"])


if __name__ == "__main__":
    unittest.main()
