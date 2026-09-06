"""Het eenduidige deel mag alvast, het onduidelijke deel wacht.

Aanleiding: taak #1 van padelmq-ai-product-engine blokkeerde op drie vragen.
Twee acceptatiecriteria waren volstrekt eenduidig (een verouderd getal
vervangen), maar er gebeurde niets — de taak stond helemaal stil.

Wat hier vastligt is vooral de grens: half werk vastleggen is erger dan geen
werk vastleggen, dus het gaat alleen mee als de verificatie het draagt.
"""

import unittest

from orchestrator.cost import CostGuard
from orchestrator.git import GitAdapter, run_git
from orchestrator.models import Question, TaskStatus
from orchestrator.notify import ConsoleNotifier
from orchestrator.runner import Runner
from orchestrator.verify import VerifyAdapter
from tests.base import TempCase
from tests.fakes import FakeExecutor, FakeReviewer

GROEN = "python3 -c \"import sys; sys.exit(0)\""
ROOD_BIJ_BESTAND = (
    "python3 -c \"import pathlib,sys; sys.exit(1 if pathlib.Path('stuk.txt').exists() else 0)\""
)


class Deelwerk(TempCase):
    def _runner(self, *, checks, stappen):
        self.project = self.make_project("demo", checks=checks)
        self.scope = self.db.scope("demo")
        self.settings.executor_model = "executor-test"
        self.settings.reviewer_model = "reviewer-test"
        self.notifier = ConsoleNotifier()
        return Runner(
            settings=self.settings, project=self.project, scope=self.scope,
            executor=FakeExecutor(stappen), reviewer=FakeReviewer(),
            verifier=VerifyAdapter(timeout_seconds=60),
            git=GitAdapter(self.tmp / "worktrees"),
            notifier=self.notifier, cost=CostGuard(self.db, self.settings),
        )

    def _vraag(self):
        return Question(text="Welke waarde moet hier komen?",
                        why_blocking="dat kan ik niet uit de kennis afleiden")

    def test_groen_deelwerk_wordt_vastgelegd_terwijl_de_taak_blokkeert(self):
        runner = self._runner(
            checks={"tests": GROEN},
            stappen=[{"write": {"app.py": "def total(x):\n    return x + 1\n"},
                      "questions": [self._vraag()]}],
        )
        task_id = self.scope.add_task("Doe het eenduidige deel", spec="x",
                                      acceptance=["werkt"])
        uitkomst = runner.run_task(task_id)

        self.assertEqual(uitkomst.status, TaskStatus.BLOCKED,
                         "de taak hoort te blijven wachten op de beslissing")
        log = run_git(self.project.repo_root, "log", "--oneline", f"orch/{task_id}")
        self.assertEqual(len(log.strip().splitlines()), 2,
                         "er hoort precies één commit bovenop main te staan")
        soorten = [e["kind"] for e in self.scope.events(limit=100)]
        self.assertIn("deelwerk-vastgelegd", soorten)

    def test_main_blijft_onaangeroerd(self):
        runner = self._runner(
            checks={"tests": GROEN},
            stappen=[{"write": {"app.py": "x = 1\n"}, "questions": [self._vraag()]}],
        )
        runner.run_task(self.scope.add_task("x", spec="x", acceptance=["werkt"]))
        log = run_git(self.project.repo_root, "log", "--oneline", "main").strip().splitlines()
        self.assertEqual(len(log), 1, "er mag niets op main terechtkomen")

    def test_rood_deelwerk_wordt_niet_vastgelegd(self):
        """Een rode branch is erger dan geen branch: niemand weet dan of hij deugt."""
        runner = self._runner(
            checks={"tests": ROOD_BIJ_BESTAND},
            stappen=[{"write": {"stuk.txt": "kapot\n"}, "questions": [self._vraag()]}],
        )
        task_id = self.scope.add_task("x", spec="x", acceptance=["werkt"])
        uitkomst = runner.run_task(task_id)

        self.assertEqual(uitkomst.status, TaskStatus.BLOCKED)
        # De branch bestaat altijd: die wordt bij het maken van de worktree
        # aangelegd. Wat telt is of er een commit op staat.
        log = run_git(self.project.repo_root, "log", "--oneline", f"orch/{task_id}")
        self.assertEqual(len(log.strip().splitlines()), 1,
                         "rood werk hoort niet vastgelegd te worden")
        soorten = [e["kind"] for e in self.scope.events(limit=100)]
        self.assertIn("deelwerk-niet-vastgelegd", soorten)

    def test_zonder_werk_gebeurt_er_niets(self):
        runner = self._runner(checks={"tests": GROEN},
                              stappen=[{"questions": [self._vraag()]}])
        task_id = self.scope.add_task("x", spec="x", acceptance=["werkt"])
        runner.run_task(task_id)
        soorten = [e["kind"] for e in self.scope.events(limit=100)]
        self.assertNotIn("deelwerk-vastgelegd", soorten)

    def test_er_komt_geen_pull_request(self):
        """Bewaard werk is geen afgerond werk. Een PR zou zeggen 'dit is klaar'."""
        runner = self._runner(
            checks={"tests": GROEN},
            stappen=[{"write": {"app.py": "x = 1\n"}, "questions": [self._vraag()]}],
        )
        task_id = self.scope.add_task("x", spec="x", acceptance=["werkt"])
        runner.run_task(task_id)
        soorten = [e["kind"] for e in self.scope.events(limit=100)]
        self.assertNotIn("pr-geopend", soorten)

    def test_de_prompt_zegt_wat_er_bij_een_openstaande_beslissing_mag(self):
        runner = self._runner(checks={"tests": GROEN}, stappen=[{}])
        task_id = self.scope.add_task("x", spec="x", acceptance=["werkt"])
        prompt = runner._build_prompt(self.scope.task(task_id), ["werkt"], [])
        self.assertIn("Raad nooit", prompt)
        self.assertIn("stop ook niet met alles", prompt)
        self.assertIn("Laat dat deel onaangeroerd", prompt)


if __name__ == "__main__":
    unittest.main()


class VastloperLegtHetWerkVast(TempCase):
    """Bij een rondraaiende taak moet het werk zichtbaar worden.

    Taak #1 van padelmq-ai-product-engine draaide in een kring: de vastloper
    bood optie 3 aan ("leg het vast en open een pull request"), dat antwoord
    werd als beslissing opgeslagen, en daarna liep de lus gewoon opnieuw tegen
    dezelfde poort. Er was geen enkel pad waarlangs die optie werkelijk werd
    uitgevoerd, en de diff was nergens te zien.
    """

    def test_de_diff_wordt_vastgelegd_voordat_de_vraag_gesteld_wordt(self):
        import inspect

        from orchestrator.runner import Runner

        bron = inspect.getsource(Runner)
        blok = bron[bron.index("last_review_signature\") == handtekening"):]
        blok = blok[:blok.index("self.scope.end_run(run_id, \"herhaalde_beoordeling\")")]
        self.assertIn("_deelwerk_vastleggen", blok,
                      "het werk wordt niet vastgelegd, dus de diff blijft onzichtbaar")
        self.assertLess(blok.index("_deelwerk_vastleggen"), blok.index("_park_or_block"),
                        "eerst vastleggen, dan pas vragen -- anders staat het niet in de vraag")

    def test_een_reeds_gedraaide_verificatie_wordt_hergebruikt(self):
        """Opnieuw verifiëren kost minuten en bewijst niets nieuws."""
        import inspect

        from orchestrator.runner import Runner

        bron = inspect.getsource(Runner._deelwerk_vastleggen)
        self.assertIn("if verification is None:", bron,
                      "de verificatie wordt onvoorwaardelijk opnieuw gedraaid")
