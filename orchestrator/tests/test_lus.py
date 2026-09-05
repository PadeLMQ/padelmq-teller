"""De lus van begin tot eind, met echte git en echte verificatie."""

import json

from orchestrator.adapters import ReviewResult
from orchestrator.cost import CostGuard
from orchestrator.git import GitAdapter, run_git
from orchestrator.models import Question, TaskStatus, Verdict
from orchestrator.notify import ConsoleNotifier
from orchestrator.runner import Paused, Runner
from orchestrator.verify import VerifyAdapter
from tests.base import TempCase
from tests.fakes import FakeExecutor, FakeReviewer

GROEN = "python3 -c \"import sys; sys.exit(0)\""
PAS_GROEN_MET_BESTAND = (
    "python3 -c \"import pathlib,sys; sys.exit(0 if pathlib.Path('klaar.txt').exists() else 1)\""
)
# Groen in de repo zoals hij is; rood zodra 'stuk.txt' bestaat. Zo kan de
# uitvoerder de verificatie eerst breken en daarna herstellen.
ROOD_BIJ_BESTAND = (
    "python3 -c \"import pathlib,sys; sys.exit(1 if pathlib.Path('stuk.txt').exists() else 0)\""
)


class Lus(TempCase):
    def build(self, *, checks=None, steps=None, reviews=None, slug="demo"):
        self.project = self.make_project(slug, checks=checks if checks is not None else {"tests": GROEN})
        self.scope = self.db.scope(slug)
        self.settings.executor_model = "executor-test"
        self.settings.reviewer_model = "reviewer-test"
        self.executor = FakeExecutor(steps or [{}])
        self.reviewer = FakeReviewer(reviews=reviews)
        self.notifier = ConsoleNotifier()
        return Runner(
            settings=self.settings,
            project=self.project,
            scope=self.scope,
            executor=self.executor,
            reviewer=self.reviewer,
            verifier=VerifyAdapter(timeout_seconds=60),
            git=GitAdapter(self.tmp / "worktrees"),
            notifier=self.notifier,
            cost=CostGuard(self.db, self.settings),
        )

    def task(self, runner, title="Voeg een functie toe", acceptance=("werkt",)):
        return self.scope.add_task(title, spec="doe iets", acceptance=list(acceptance))

    # -- gelukkige weg -----------------------------------------------------
    def test_groene_weg_levert_een_branch_op_en_raakt_main_niet(self):
        runner = self.build(steps=[{"write": {"app.py": "def total(x):\n    return x + 1\n"}}])
        task_id = self.task(runner)
        outcome = runner.run_task(task_id)

        self.assertEqual(outcome.status, TaskStatus.PR_OPEN)
        branches = run_git(self.project.repo_root, "branch", "--list")
        self.assertIn(f"orch/{task_id}", branches)

        # main heeft nog steeds precies de eerste commit
        log = run_git(self.project.repo_root, "log", "--oneline", "main").strip().splitlines()
        self.assertEqual(len(log), 1, "er mag niets op main gecommit zijn")

        # de wijziging staat wel op de orch-branch
        orch_log = run_git(self.project.repo_root, "log", "--oneline", f"orch/{task_id}")
        self.assertEqual(len(orch_log.strip().splitlines()), 2)

    def test_kosten_worden_per_rol_vastgelegd(self):
        runner = self.build(steps=[{"write": {"app.py": "x = 1\n"}}])
        runner.run_task(self.task(runner))
        rollen = {r["role"] for r in CostGuard(self.db, self.settings).report()}
        self.assertEqual(rollen, {"uitvoerder", "beoordelaar"})

    # -- vragen ------------------------------------------------------------
    def test_vraag_zonder_bron_parkeert_de_taak(self):
        runner = self.build(steps=[
            {"questions": [Question(text="Welke tekst komt op de knop?")]},
        ])
        task_id = self.scope.add_task("A", acceptance=["werkt"])
        self.scope.add_task("onafhankelijk werk", acceptance=["werkt"])  # dus PARK, niet BLOCK

        outcome = runner.run_task(task_id)
        self.assertEqual(outcome.status, TaskStatus.PARKED)
        vragen = self.scope.open_questions("park")
        self.assertEqual(len(vragen), 1)
        self.assertEqual(self.scope.task(task_id)["blocked_by_question"], vragen[0]["id"])
        self.assertEqual(len(run_git(self.project.repo_root, "log", "--oneline", "main")
                             .strip().splitlines()), 1)

    def test_zonder_ander_werk_blokkeert_en_meldt(self):
        runner = self.build(steps=[
            {"questions": [Question(text="Welke tekst komt op de knop?")]},
        ])
        task_id = self.scope.add_task("A", acceptance=["werkt"])
        outcome = runner.run_task(task_id)
        self.assertEqual(outcome.status, TaskStatus.BLOCKED)
        self.assertEqual(len(self.scope.open_questions("block")), 1)
        self.assertTrue(any(m.urgent for m in self.notifier.sent), "BLOCK moet gemeld worden")

    def test_verzonnen_waarde_houdt_de_commit_tegen(self):
        runner = self.build(steps=[
            {"write": {"app.py": "def total(x):\n    verzendkosten = 7.45\n    return x\n"}},
        ])
        task_id = self.scope.add_task("A", acceptance=["werkt"])
        outcome = runner.run_task(task_id)
        self.assertIn(outcome.status, (TaskStatus.PARKED, TaskStatus.BLOCKED))
        self.assertIn("7.45", outcome.detail)
        self.assertEqual(len(run_git(self.project.repo_root, "log", "--oneline", "main")
                             .strip().splitlines()), 1)

    def test_aanname_zonder_bron_houdt_de_commit_tegen(self):
        runner = self.build(steps=[
            {"write": {"app.py": "x = 1\n"},
             "assumptions": ["De marge is dertig procent || "]},
        ])
        task_id = self.scope.add_task("A", acceptance=["werkt"])
        outcome = runner.run_task(task_id)
        self.assertIn(outcome.status, (TaskStatus.PARKED, TaskStatus.BLOCKED))
        self.assertIn("aanname zonder bron", outcome.detail)

    # -- verificatie -------------------------------------------------------
    def test_rode_verificatie_leidt_tot_een_nieuwe_poging_en_dan_groen(self):
        runner = self.build(
            checks={"tests": ROOD_BIJ_BESTAND},
            steps=[
                {"write": {"app.py": "x = 1\n", "stuk.txt": "kapot\n"}},  # breekt de check
                {"delete": ["stuk.txt"]},                                   # herstelt hem
            ],
        )
        outcome = runner.run_task(self.scope.add_task("A", acceptance=["werkt"]))
        self.assertEqual(outcome.status, TaskStatus.PR_OPEN)
        self.assertEqual(len(self.executor.calls), 2)

    def test_tweemaal_dezelfde_fout_stopt_de_taak(self):
        runner = self.build(
            checks={"tests": ROOD_BIJ_BESTAND},
            steps=[
                {"write": {"app.py": "x = 1\n", "stuk.txt": "kapot\n"}},
                {"write": {"app.py": "x = 2\n"}},  # zelfde falende uitslag
            ],
        )
        outcome = runner.run_task(self.scope.add_task("A", acceptance=["werkt"]))
        self.assertEqual(outcome.status, TaskStatus.BLOCKED)
        self.assertIn("dezelfde falende uitslag", outcome.detail)

    def test_rode_baseline_wordt_niet_aan_de_uitvoerder_toegeschreven(self):
        runner = self.build(checks={"tests": PAS_GROEN_MET_BESTAND}, steps=[{}])
        outcome = runner.run_task(self.scope.add_task("A", acceptance=["werkt"]))
        self.assertEqual(outcome.status, TaskStatus.BLOCKED)
        self.assertIn("al rood", outcome.detail)
        self.assertEqual(self.executor.calls, [], "de uitvoerder mag niet gedraaid hebben")

    # -- beoordelaar -------------------------------------------------------
    def test_pass_met_openstaand_criterium_wordt_geen_commit(self):
        runner = self.build(
            steps=[{"write": {"app.py": "x = 1\n"}}],
            reviews=[ReviewResult(verdict=Verdict.PASS, acceptance_missing=["werkt"])],
        )
        task_id = self.scope.add_task("A", acceptance=["werkt"])
        outcome = runner.run_task(task_id)
        self.assertEqual(outcome.status, TaskStatus.QUEUED)
        self.assertEqual(len(run_git(self.project.repo_root, "log", "--oneline", "main")
                             .strip().splitlines()), 1)

    def test_escalatie_van_de_beoordelaar_blokkeert(self):
        runner = self.build(
            steps=[{"write": {"app.py": "x = 1\n"}}],
            reviews=[ReviewResult(verdict=Verdict.ESCALATE,
                                  next_instruction="Dit raakt de prijsstelling.")],
        )
        outcome = runner.run_task(self.scope.add_task("A", acceptance=["werkt"]))
        self.assertEqual(outcome.status, TaskStatus.BLOCKED)

    def test_reviewer_krijgt_geen_geheimen_te_zien(self):
        runner = self.build(steps=[
            {"write": {"app.py": 'CLIENT_SECRET = "zeergeheimewaarde123"\n'}},
        ])
        runner.run_task(self.scope.add_task("A", acceptance=["werkt"]))
        self.assertNotIn("zeergeheimewaarde123", self.reviewer.last_diff)

    # -- randvoorwaarden ---------------------------------------------------
    def test_taak_zonder_acceptatiecriteria_komt_de_lus_niet_in(self):
        runner = self.build()
        task_id = self.scope.add_task("A")
        outcome = runner.run_task(task_id)
        self.assertEqual(outcome.status, TaskStatus.BLOCKED)
        self.assertEqual(self.executor.calls, [])

    def test_noodstop_stopt_alles(self):
        runner = self.build()
        self.settings.stop_file.write_text("stop\n", encoding="utf-8")
        with self.assertRaises(Paused):
            runner.run_task(self.scope.add_task("A", acceptance=["werkt"]))


class Hervatten(Lus):
    """Bruikbaar werk van een eerdere poging mag niet opnieuw betaald worden."""

    def _leg_werk_klaar(self, runner, task_id, bestand="eerder.py", inhoud="# poging 1\n"):
        """Bootst een eerdere poging na: een commit op orch/<id>."""
        worktree = runner.git.create_worktree(
            self.project.repo_root, f"orch/{task_id}", self.project.default_branch
        )
        (worktree.path / bestand).write_text(inhoud, encoding="utf-8")
        sha = runner.git.commit(worktree, "werk uit de eerste poging", "t <t@t>")
        runner.git.remove_worktree(worktree)
        return sha

    def test_groen_bestaand_werk_wordt_hergebruikt_zonder_uitvoerder(self):
        runner = self.build(steps=[{"write": {"nooit.py": "had niet mogen draaien\n"}}])
        task_id = self.task(runner)
        sha = self._leg_werk_klaar(runner, task_id)

        outcome = runner.run_task(task_id)

        self.assertEqual(
            len(self.executor.calls), 0,
            "de uitvoerder is aangeroepen terwijl het bestaande werk groen was",
        )
        self.assertEqual(outcome.status, TaskStatus.PR_OPEN)
        kop = run_git(self.project.repo_root, "rev-parse", f"orch/{task_id}").strip()
        self.assertEqual(kop, sha, "de eerdere commit is niet hergebruikt")

    def test_de_beslissing_staat_in_de_audittrail(self):
        runner = self.build()
        task_id = self.task(runner)
        self._leg_werk_klaar(runner, task_id)
        runner.run_task(task_id)

        events = [r for r in self.scope.events(limit=50) if r["kind"] == "hervatting"]
        self.assertTrue(events, "de hervatting is niet vastgelegd")
        payload = json.loads(events[0]["payload"])
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["commits"], 1)
        self.assertIn("hergebruikt", payload["besluit"])
        self.assertTrue(payload["checks"], "de gedraaide checks ontbreken in de audittrail")

    def test_rood_bestaand_werk_valt_terug_op_implementeren(self):
        """Voldoet het oude werk niet, dan moet de uitvoerder alsnog draaien.

        De check is groen op main en rood zodra stuk.txt bestaat. De baseline
        blijft dus groen, terwijl de eerdere poging rood staat.
        """
        # groen op main (geen stuk.txt), rood zodra stuk.txt bestaat, en weer
        # groen zodra fix.txt ernaast staat. Zo blijft de baseline groen terwijl
        # de eerdere poging rood is, en kan de uitvoerder het met schrijven
        # herstellen.
        check = (
            "python3 -c \"import pathlib,sys; sys.exit(0 if (not "
            "pathlib.Path('stuk.txt').exists()) or pathlib.Path('fix.txt').exists() "
            "else 1)\""
        )
        runner = self.build(checks={"tests": check},
                            steps=[{"write": {"fix.txt": "hersteld\n"}}])
        task_id = self.task(runner)
        self._leg_werk_klaar(runner, task_id, bestand="stuk.txt", inhoud="kapot\n")

        outcome = runner.run_task(task_id)

        self.assertEqual(len(self.executor.calls), 1, "de uitvoerder had moeten draaien")
        self.assertEqual(outcome.status, TaskStatus.PR_OPEN)

    def test_zonder_eerder_werk_verandert_er_niets(self):
        runner = self.build(steps=[{"write": {"app.py": "x = 1\n"}}])
        task_id = self.task(runner)
        runner.run_task(task_id)
        self.assertEqual(len(self.executor.calls), 1)

    def test_de_beoordelaar_ziet_ook_al_vastgelegd_werk(self):
        """Een lege diff laat de beoordelaar alles goedkeuren zonder iets te zien."""
        runner = self.build()
        task_id = self.task(runner)
        self._leg_werk_klaar(runner, task_id, bestand="zichtbaar.py",
                             inhoud="def f():\n    return 1\n")
        runner.run_task(task_id)

        contexten = [
            json.loads(r["payload"]) for r in self.scope.events(limit=50)
            if r["kind"] == "reviewer-context"
        ]
        beoordeling = [c for c in contexten if c.get("fase") == "beoordelen"]
        self.assertTrue(beoordeling, "de beoordelaar is niet aangeroepen")
        self.assertGreater(
            beoordeling[0]["diff_tekens"], 0,
            "de beoordelaar kreeg een lege diff terwijl er werk vastligt",
        )

    def test_onuitvoerbare_verificatie_blokkeert_en_implementeert_niet_opnieuw(self):
        """Exitcode 127 is 'commando niet gevonden': de omgeving, niet het werk.

        Dit gebeurde echt: een verse worktree zonder node_modules gaf 127, de
        orkestrator las dat als 'werk voldoet niet' en betaalde $0,30 voor een
        nieuwe implementatie van werk dat al klaar was.
        """
        # Een script dat alleen in de repo staat en niet in de worktree, net
        # zoals node_modules: de baseline is groen, de worktree geeft 127.
        runner = self.build(
            checks={"tests": "./deps/tool.sh"},
            steps=[{"write": {"nooit.py": "had niet mogen draaien\n"}}],
        )
        deps = self.project.repo_root / "deps"
        deps.mkdir()
        tool = deps / "tool.sh"
        tool.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        tool.chmod(0o755)
        (self.project.repo_root / ".gitignore").write_text("deps/\n", encoding="utf-8")
        run_git(self.project.repo_root, "add", "-A")
        run_git(self.project.repo_root, "-c", "user.name=t", "-c", "user.email=t@t",
                "commit", "-q", "-m", "negeer deps")

        task_id = self.task(runner)
        self._leg_werk_klaar(runner, task_id)

        outcome = runner.run_task(task_id)

        self.assertEqual(outcome.status, TaskStatus.BLOCKED)
        self.assertEqual(
            len(self.executor.calls), 0,
            "er is opnieuw betaald voor implementatie terwijl de verificatie niet kon draaien",
        )
        events = [r for r in self.scope.events(limit=50)
                  if r["kind"] == "verificatie-onuitvoerbaar"]
        self.assertTrue(events, "de onuitvoerbare verificatie is niet vastgelegd")
