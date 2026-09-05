"""Regressiegaranties uit B7.

Elke test hieronder hoort bij een defect dat werkelijk is opgetreden en geld
of een run heeft gekost. Ze staan bij elkaar zodat zichtbaar is welke lessen
door code worden afgedwongen en niet door goede voornemens.
"""

import json
import os
import unittest
from unittest import mock

from orchestrator.adapters.claude import _usage_from_cli
from orchestrator.config import ModelPrice
from orchestrator.cost import Estimate, InconsistentUsage
from orchestrator.models import TaskStatus

try:
    from tests.base import TempCase
except ImportError:  # pragma: no cover
    from base import TempCase

try:
    from tests.test_lus import GROEN, Lus
except ImportError:  # pragma: no cover
    from test_lus import GROEN, Lus


class G3_BetaaldeAanroepAltijdGeboekt(TempCase):
    """Een aanroep is betaald zodra hij gedaan is, ook als de boekhouding klapt."""

    def test_boekhoudfout_stopt_de_run_niet_en_wordt_vastgelegd(self):
        from orchestrator.adapters import Usage
        from orchestrator.cost import CostGuard
        from orchestrator.git import GitAdapter
        from orchestrator.notify import ConsoleNotifier
        from orchestrator.runner import Runner
        from orchestrator.verify import VerifyAdapter
        from tests.fakes import FakeExecutor, FakeReviewer

        project = self.make_project("g3", checks={})
        scope = self.db.scope("g3")
        runner = Runner(
            settings=self.settings, project=project, scope=scope,
            executor=FakeExecutor([{}]), reviewer=FakeReviewer(),
            verifier=VerifyAdapter(timeout_seconds=60),
            git=GitAdapter(self.tmp / "wt"), notifier=ConsoleNotifier(),
            cost=CostGuard(self.db, self.settings),
        )
        task_id = scope.add_task("t", "s", ["a"])
        run_id = scope.start_run(task_id, "task")

        # Onmogelijke telling: meer cache dan invoer.
        kapot = Usage(model="executor-test", tokens_in=10, tokens_out=1, cached_in=999)
        runner._charge(kapot, phase="implement", role="uitvoerder",
                       task_id=task_id, run_id=run_id)  # mag niet werpen

        events = [r for r in scope.events(limit=20) if r["kind"] == "kosten-onbekend"]
        self.assertTrue(events, "de onboekbare aanroep is nergens vastgelegd")
        payload = json.loads(events[0]["payload"])
        self.assertEqual(payload["model"], "executor-test")
        self.assertEqual(payload["cached_in"], 999)
        self.assertIn("cachetokens", payload["detail"])

    def test_nooit_stilzwijgend_nul(self):
        """Een onmogelijke telling levert een fout op, geen bedrag van 0."""
        est = Estimate(model="m", tokens_in=10, tokens_out=0, cached_in=999)
        with self.assertRaises(InconsistentUsage):
            est.cost(ModelPrice(2.0, 12.0, 0.2))


class G4_ProviderConventiesGescheiden(unittest.TestCase):
    """OpenAI telt cache in input_tokens, de Claude-CLI niet."""

    def test_claude_telling_wordt_genormaliseerd(self):
        u = _usage_from_cli("claude-opus-5", {
            "input_tokens": 28, "cache_read_input_tokens": 586218,
            "cache_creation_input_tokens": 7828, "output_tokens": 412,
        }, {})
        self.assertEqual(u.tokens_in, 28 + 586218 + 7828)
        self.assertEqual(u.cached_in, 586218)

    def test_openai_telling_blijft_ongemoeid(self):
        """Daar is input_tokens al het totaal; er mag niets bij opgeteld worden."""
        from orchestrator.adapters.reviewer import _cached_tokens

        class Details:
            cached_tokens = 8000

        class Usage:
            input_tokens = 10000
            output_tokens = 100
            input_tokens_details = Details()

        u = Usage()
        self.assertEqual(_cached_tokens(u), 8000)
        est = Estimate(model="m", tokens_in=u.input_tokens,
                       tokens_out=u.output_tokens, cached_in=_cached_tokens(u))
        self.assertEqual(est.uncached_in, 2000)


class G9_CredentialProxyIsGeldig(unittest.TestCase):
    """Controleer of authenticatie wérkt, niet of een variabele bestaat."""

    def test_reviewer_bouwt_zonder_omgevingsvariabele(self):
        from orchestrator.adapters.reviewer import OpenAIReviewer

        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("OPENAI_API_KEY", None)
            client = OpenAIReviewer("gpt-5.6-terra").client
        self.assertIsNotNone(client, "de reviewer eist nog een omgevingsvariabele")

    def test_github_client_verstuurt_zonder_omgevingsvariabele(self):
        from orchestrator.notify.github import GitHubClient

        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ORCH_GITHUB_TOKEN", None)
            client = GitHubClient(repo="x/y")
        self.assertTrue(client.token, "zonder token wordt er niets verstuurd")

    def test_expliciete_sleutel_gaat_voor_op_de_placeholder(self):
        from orchestrator.notify.github import GitHubClient

        client = GitHubClient(token="nep-geheim-uit-de-test", repo="x/y")
        self.assertEqual(client.token, "nep-geheim-uit-de-test")


class G6_FeedbackOverleeftHerstart(Lus):
    """Feedback moet uit de database komen, niet uit het geheugen van een object."""

    def test_feedback_staat_in_de_database(self):
        from orchestrator.adapters import Finding, ReviewResult
        from orchestrator.models import Verdict

        revise = ReviewResult(
            verdict=Verdict.REVISE,
            findings=[Finding(severity="major", file="a.py", issue="te breed",
                              fix="versmal")],
            next_instruction="Versmal het.",
        )
        runner = self.build(steps=[{"write": {"a.py": "x = 1\n"}}], reviews=[revise])
        task_id = self.task(runner)
        runner.run_task(task_id)

        # Verse database-aansluiting: alsof het proces opnieuw is gestart.
        from orchestrator.db import Database

        verse = Database(self.settings.db_path)
        self.addCleanup(verse.close)
        taak = verse.scope("demo").task(task_id)
        opgeslagen = json.loads(taak["review_feedback"])
        self.assertEqual(opgeslagen["instructie"], "Versmal het.")
        self.assertEqual(opgeslagen["bevindingen"][0]["punt"], "te breed")


class G10_GeenBetaalde_Herhaling(Lus):
    """Dezelfde opdracht bij dezelfde toestand gaat niet nog eens naar een betaald model."""

    def test_identieke_opdracht_bij_ongewijzigde_toestand_wordt_geblokkeerd(self):
        """Drie rondes: pas als prompt EN toestand gelijk zijn, slaat de poort dicht.

        Ronde 1 heeft nog geen feedback, ronde 2 wel: die prompts verschillen dus
        terecht. Ronde 3 krijgt exact dezelfde feedback bij een onveranderde
        werkmap -- dan levert nog een betaalde aanroep hetzelfde antwoord op.
        """
        from orchestrator.adapters import Finding, ReviewResult
        from orchestrator.models import Verdict

        revise = ReviewResult(
            verdict=Verdict.REVISE,
            findings=[Finding(severity="major", file="a.py", issue="zelfde punt",
                              fix="zelfde herstel")],
            next_instruction="Zelfde instructie.",
        )
        # De uitvoerder verandert niets: de toestand blijft identiek.
        runner = self.build(
            checks={"tests": GROEN},
            steps=[{}, {}, {}],
            reviews=[revise, revise, revise],
        )
        task_id = self.task(runner)

        self.assertEqual(runner.run_task(task_id).status, TaskStatus.QUEUED)
        self.assertEqual(runner.run_task(task_id).status, TaskStatus.QUEUED)
        na_twee = len(self.executor.calls)
        self.assertEqual(na_twee, 2)

        derde = runner.run_task(task_id)

        self.assertEqual(derde.status, TaskStatus.BLOCKED)
        self.assertEqual(
            len(self.executor.calls), na_twee,
            "er is opnieuw betaald voor dezelfde opdracht bij dezelfde toestand",
        )
        events = [r for r in self.scope.events(limit=50)
                  if r["kind"] == "herhaalde-opdracht"]
        self.assertTrue(events, "de tegengehouden herhaling is niet vastgelegd")

    def test_gewijzigde_toestand_mag_wel_opnieuw(self):
        """Nieuwe informatie of een gewijzigde werkmap rechtvaardigt een nieuwe poging."""
        from orchestrator.adapters import ReviewResult
        from orchestrator.models import Verdict

        runner = self.build(
            checks={"tests": GROEN},
            steps=[{"write": {"a.py": "x = 1\n"}}, {"write": {"b.py": "y = 2\n"}}],
            reviews=[ReviewResult(verdict=Verdict.REVISE, next_instruction="doe meer"),
                     ReviewResult(verdict=Verdict.PASS)],
        )
        task_id = self.task(runner)
        self.assertEqual(runner.run_task(task_id).status, TaskStatus.QUEUED)
        self.assertEqual(runner.run_task(task_id).status, TaskStatus.PR_OPEN)
        self.assertEqual(len(self.executor.calls), 2,
                         "de tweede ronde is onterecht tegengehouden")


if __name__ == "__main__":
    unittest.main()


class AIEfficiency(TempCase):
    """De metriek, geijkt op de werkelijke cijfers van de B7-pilot."""

    # Zoals ze in de audittrail staan. Deze bedragen worden niet herrekend.
    B7_TOTAAL = 1.229464
    B7_VERSPILD = 0.841451

    def _project(self):
        self.make_project("eff", checks={})
        return self.db.scope("eff")

    def test_ijking_op_de_b7_cijfers(self):
        from orchestrator.efficiency import measure

        scope = self._project()
        task_id = scope.add_task("t", "s", ["a"])
        run_id = scope.start_run(task_id, "task")
        # de twee verspilde aanroepen uit B7
        for bedrag, reden in ((0.544913, "run afgebroken: InconsistentUsage"),
                              (0.296538, "verificatie onuitvoerbaar gelezen als kapot werk")):
            scope.record_call(phase="implement", role="uitvoerder", model="executor-test",
                              tokens_in=1, tokens_out=1, cached_in=0, cost_eur=bedrag,
                              task_id=task_id, run_id=run_id, day="2026-09-05")
            scope.conn.execute(
                "UPDATE calls SET wasted_reason = ? WHERE id ="
                " (SELECT MAX(id) FROM calls)", (reden,))
        # de nuttige rest
        for bedrag in (0.327644, 0.007550, 0.021722, 0.031098):
            scope.record_call(phase="review", role="beoordelaar", model="reviewer-test",
                              tokens_in=1, tokens_out=1, cached_in=0, cost_eur=bedrag,
                              task_id=task_id, run_id=run_id, day="2026-09-05")

        eff = measure(scope)
        # Vijf decimalen: de fixture gebruikt de afgeronde weergavebedragen, het
        # echte totaal komt uit volledige floats. Dat scheelt 1e-6, ver onder een cent.
        self.assertAlmostEqual(eff.total, self.B7_TOTAAL, places=5)
        self.assertAlmostEqual(eff.wasted, self.B7_VERSPILD, places=5)
        self.assertAlmostEqual(eff.useful, self.B7_TOTAAL - self.B7_VERSPILD, places=5)
        self.assertAlmostEqual(eff.wasted_pct, 68.4, places=1)
        self.assertEqual(eff.calls_wasted, 2)
        self.assertEqual(eff.calls_useful, 4)
        self.assertEqual(len(eff.reasons), 2, "de redenen zijn samengevallen")

    def test_ongemarkeerd_geldt_als_nuttig(self):
        """Te weinig verspilling melden is beter dan nuttig werk verdacht maken."""
        from orchestrator.efficiency import measure

        scope = self._project()
        task_id = scope.add_task("t", "s", ["a"])
        run_id = scope.start_run(task_id, "task")
        scope.record_call(phase="implement", role="uitvoerder", model="executor-test",
                          tokens_in=1, tokens_out=1, cached_in=0, cost_eur=0.5,
                          task_id=task_id, run_id=run_id, day="2026-09-05")
        eff = measure(scope)
        self.assertEqual(eff.wasted, 0.0)
        self.assertAlmostEqual(eff.useful, 0.5)

    def test_hergebruik_wordt_geteld_als_vermeden_aanroep(self):
        from orchestrator.efficiency import measure

        scope = self._project()
        task_id = scope.add_task("t", "s", ["a"])
        scope.log("hervatting", {"besluit": "bestaand werk hergebruikt", "ok": True},
                  task_id=task_id)
        scope.log("hervatting", {"besluit": "bestaand werk voldoet niet; opnieuw"
                                 " implementeren", "ok": False}, task_id=task_id)
        self.assertEqual(measure(scope).reused, 1)

    def test_markeren_verandert_de_bedragen_niet(self):
        from orchestrator.efficiency import measure

        scope = self._project()
        task_id = scope.add_task("t", "s", ["a"])
        run_id = scope.start_run(task_id, "task")
        scope.record_call(phase="implement", role="uitvoerder", model="executor-test",
                          tokens_in=1, tokens_out=1, cached_in=0, cost_eur=0.25,
                          task_id=task_id, run_id=run_id, day="2026-09-05")
        voor = measure(scope).total
        scope.mark_run_wasted(run_id, "run afgebroken")
        na = measure(scope)
        self.assertAlmostEqual(na.total, voor, msg="het totaal is veranderd door te markeren")
        self.assertAlmostEqual(na.wasted, 0.25)


class G7_WorktreeHergebruikSpaartDependencies(TempCase):
    """Een worktree wissen betekende de geinstalleerde afhankelijkheden wissen.

    Dat was de werkelijke oorzaak van D-10: de verificatie kon daarna niet
    draaien, gaf exitcode 127, en dat werd gelezen als kapot werk.
    """

    def test_niet_gevolgde_bestanden_overleven_hergebruik(self):
        from orchestrator.git import GitAdapter

        repo = self.make_repo("deps")
        adapter = GitAdapter(self.tmp / "wt")

        eerste = adapter.create_worktree(repo, "orch/7", "main")
        (eerste.path / "node_modules").mkdir()
        (eerste.path / "node_modules" / "pakket.js").write_text("x", encoding="utf-8")

        tweede = adapter.create_worktree(repo, "orch/7", "main")

        self.assertTrue(
            (tweede.path / "node_modules" / "pakket.js").exists(),
            "de afhankelijkheden zijn gewist bij hergebruik van de worktree",
        )

    def test_losse_wijzigingen_in_gevolgde_bestanden_verdwijnen_wel(self):
        """Rommel van een eerdere poging hoort niet mee te reizen.

        Het vastgelegde werk zit in de branch; wat los in de werkmap staat is
        restant en zou anders ongemerkt in de volgende diff belanden.
        """
        from orchestrator.git import GitAdapter

        repo = self.make_repo("rommel")
        adapter = GitAdapter(self.tmp / "wt2")

        eerste = adapter.create_worktree(repo, "orch/8", "main")
        (eerste.path / "app.py").write_text("# restant van poging 1\n", encoding="utf-8")

        tweede = adapter.create_worktree(repo, "orch/8", "main")

        self.assertNotIn("# restant", (tweede.path / "app.py").read_text(encoding="utf-8"))


class G11_KostenremWerktOpDeEchtePrompt(unittest.TestCase):
    """Een rem die een ander getal afremt dan er langskomt, remt niets."""

    def test_schatting_groeit_met_de_prompt(self):
        from orchestrator.runner import _schatting

        klein_in, klein_uit = _schatting("x" * 400)
        groot_in, groot_uit = _schatting("x" * 400_000)
        self.assertEqual(klein_in, 100)
        self.assertEqual(groot_in, 100_000)
        self.assertGreater(groot_uit, klein_uit)

    def test_lege_prompt_geeft_geen_nul(self):
        """Nul zou elke rem laten passeren."""
        from orchestrator.runner import _schatting

        invoer, uitvoer = _schatting("")
        self.assertGreaterEqual(invoer, 1)
        self.assertGreaterEqual(uitvoer, 1)


class G12_UitvoerderHervatGeenVreemdeSessie(unittest.TestCase):
    """De uitvoerder speelde de sessie van de orkestrator zelf opnieuw af.

    Dat liep op van $0,54 naar $1,91 per aanroep, met 1.477.278 invoertokens.
    De prompt is zelfdragend; gespreksgeschiedenis is niet nodig.
    """

    def test_geen_resume_in_het_commando(self):
        from orchestrator.adapters.claude import ClaudeExecutor

        cmd = ClaudeExecutor("claude-opus-5")._command("doe iets", "een-sessie-id")
        self.assertNotIn("--resume", cmd)
        self.assertNotIn("een-sessie-id", cmd)

    def test_de_prompt_zit_wel_in_het_commando(self):
        from orchestrator.adapters.claude import ClaudeExecutor

        cmd = ClaudeExecutor("claude-opus-5")._command("doe precies dit", None)
        self.assertIn("doe precies dit", cmd)


class G13_BudgetberichtInDeJuisteValuta(unittest.TestCase):
    def test_geen_hardgecodeerde_euro(self):
        from orchestrator.cost import BudgetExceeded

        fout = BudgetExceeded("taak 1", 2.0, 1.91, 0.06, "$")
        self.assertIn("$1.9100", str(fout))
        self.assertNotIn("€", str(fout))
