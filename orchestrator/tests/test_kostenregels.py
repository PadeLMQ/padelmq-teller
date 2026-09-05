"""De kostenregels: zo veel mogelijk veilige autonomie per betaalde aanroep.

Elke test hier bewaakt een regel die geld kost als hij breekt — maar geen
enkele mag veiligheid inruilen voor besparing.
"""

from orchestrator.adapters import Alternative, AnswerResult, ReviewResult, Usage
from orchestrator.cost import CostGuard
from orchestrator.git import GitAdapter
from orchestrator.knowledge import KnowledgeStore
from orchestrator.models import Citation, Question, TaskStatus, Verdict
from orchestrator.notify import ConsoleNotifier
from orchestrator.reviewcache import ReviewCache
from orchestrator.runner import Runner
from orchestrator.verify import VerifyAdapter
from tests.base import TempCase
from tests.fakes import FakeExecutor, FakeReviewer

GROEN = "python3 -c \"import sys; sys.exit(0)\""
# Groen in de repo zoals hij is; rood zodra 'stuk.txt' bestaat. Zo kan de
# uitvoerder de verificatie eerst breken en daarna zelf herstellen.
ROOD_BIJ_BESTAND = (
    "python3 -c \"import pathlib,sys; sys.exit(1 if pathlib.Path('stuk.txt').exists() else 0)\""
)


class TellendeReviewer(FakeReviewer):
    """Telt hoe vaak er werkelijk betaald wordt."""

    def __init__(self, **kw):
        super().__init__(**kw)
        self.answer_batches: list[int] = []

    def answer(self, *, questions, context, previous_response_id=None):
        self.answer_calls += 1
        self.answer_batches.append(len(questions))
        self.last_context = context
        return AnswerResult(questions=self.answers or questions, response_id="r",
                            usage=Usage("reviewer-test", 100, 50))


class MinderCalls(TempCase):
    def bouw(self, *, checks, steps, reviewer):
        self.project = self.make_project("pilot", checks=checks)
        self.scope = self.db.scope("pilot")
        self.settings.executor_model = "executor-test"
        self.settings.reviewer_model = "reviewer-test"
        self.reviewer = reviewer
        return Runner(
            settings=self.settings, project=self.project, scope=self.scope,
            executor=FakeExecutor(steps), reviewer=reviewer,
            verifier=VerifyAdapter(timeout_seconds=60),
            git=GitAdapter(self.tmp / "worktrees"), notifier=ConsoleNotifier(),
            cost=CostGuard(self.db, self.settings),
        )

    def test_rode_verificatie_kost_geen_enkele_reviewer_call(self):
        """Claude herstelt zelf; GPT wordt pas geraadpleegd als het groen is."""
        reviewer = TellendeReviewer()
        runner = self.bouw(
            checks={"tests": ROOD_BIJ_BESTAND},
            steps=[{"write": {"a.txt": "1\n", "stuk.txt": "kapot\n"}},
                   {"delete": ["stuk.txt"]}],
            reviewer=reviewer,
        )
        uitkomst = runner.run_task(self.scope.add_task("A", acceptance=["A"]))
        self.assertEqual(uitkomst.status, TaskStatus.PR_OPEN)
        self.assertEqual(reviewer.answer_calls, 0, "een rode test mag niets kosten")
        self.assertEqual(reviewer.review_calls, 1, "pas op groen één eindreview")

    def test_drie_vragen_gaan_in_een_enkele_call(self):
        vragen = [Question(text=f"Vraag {i}?") for i in range(3)]
        reviewer = TellendeReviewer()
        runner = self.bouw(checks={"tests": GROEN}, steps=[{"questions": vragen}],
                           reviewer=reviewer)
        task_id = self.scope.add_task("A", acceptance=["A"])
        self.scope.add_task("ander werk", acceptance=["B"])
        runner.run_task(task_id)
        self.assertEqual(reviewer.answer_batches, [3], "drie vragen, één betaalde call")

    def test_de_hele_batch_wordt_vastgelegd_en_niet_weggegooid(self):
        """Anders komen de al betaalde vragen een ronde later opnieuw langs."""
        vragen = [Question(text=f"Vraag {i}?") for i in range(3)]
        runner = self.bouw(checks={"tests": GROEN}, steps=[{"questions": vragen}],
                           reviewer=TellendeReviewer())
        task_id = self.scope.add_task("A", acceptance=["A"])
        self.scope.add_task("ander werk", acceptance=["B"])
        runner.run_task(task_id)
        self.assertEqual(len(self.scope.pending_questions()), 3)

    def test_een_blokkade_in_de_batch_bepaalt_de_status(self):
        vragen = [Question(text="Knoptekst?"), Question(text="Welke btw-behandeling?")]
        runner = self.bouw(checks={"tests": GROEN}, steps=[{"questions": vragen}],
                           reviewer=TellendeReviewer())
        task_id = self.scope.add_task("A", acceptance=["A"])
        self.scope.add_task("ander werk", acceptance=["B"])
        uitkomst = runner.run_task(task_id)
        # btw is een verboden categorie; met ander werk beschikbaar is dat PARK,
        # dus de zwaarste uitkomst hier is PARK en beide vragen staan vast.
        self.assertEqual(uitkomst.status, TaskStatus.PARKED)
        self.assertEqual(len(self.scope.pending_questions()), 2)


class MinimaleContext(TempCase):
    def test_alleen_bevestigde_items_gaan_volledig_mee(self):
        store = KnowledgeStore(self.tmp / "kennis")
        store.scaffold("demo")
        store.append_decision("Munteenheid", "Alles in euro, altijd.",
                              source="intake", confirmed_by_human=True)
        store.append_decision("Knoptekst", "Waarschijnlijk Bewaren, nog niet zeker.",
                              source="model", confirmed_by_human=False)
        store.load()
        context = store.as_prompt_context()

        self.assertIn("Alles in euro, altijd.", context)
        self.assertNotIn("Waarschijnlijk Bewaren", context,
                         "de body van een niet-bevestigd item hoeft niet betaald te worden")
        self.assertIn("Knoptekst", context, "het bestaan ervan moet wel bekend zijn")
        self.assertIn("NOOIT als bron", context)


class Hergebruik(TempCase):
    def opzet(self):
        self.project = self.make_project("pilot")
        self.scope = self.db.scope("pilot")
        self.inner = TellendeReviewer(
            reviews=[ReviewResult(verdict=Verdict.PASS,
                                  alternative=Alternative(recommendation="geen"))] * 5
        )
        self.cache = ReviewCache(self.inner, self.scope, "reviewer-test")

    def test_dezelfde_vraag_met_dezelfde_context_wordt_eenmaal_betaald(self):
        self.opzet()
        vragen = [Question(text="Welke munteenheid?")]
        eerste = self.cache.answer(questions=vragen, context="kennis A")
        tweede = self.cache.answer(questions=vragen, context="kennis A")
        self.assertEqual(self.inner.answer_calls, 1)
        self.assertEqual(self.cache.treffers, 1)
        self.assertEqual([q.text for q in tweede.questions], [q.text for q in eerste.questions])

    def test_gewijzigde_kennis_wordt_opnieuw_gevraagd(self):
        self.opzet()
        vragen = [Question(text="Welke munteenheid?")]
        self.cache.answer(questions=vragen, context="kennis A")
        self.cache.answer(questions=vragen, context="kennis A, plus beslissing D-002")
        self.assertEqual(self.inner.answer_calls, 2, "veranderde context = opnieuw vragen")

    def test_een_andere_vraag_wordt_opnieuw_gevraagd(self):
        self.opzet()
        self.cache.answer(questions=[Question(text="Vraag een?")], context="kennis A")
        self.cache.answer(questions=[Question(text="Vraag twee?")], context="kennis A")
        self.assertEqual(self.inner.answer_calls, 2)

    def test_dezelfde_diff_wordt_niet_tweemaal_beoordeeld(self):
        self.opzet()
        args = dict(diff="--- a\n+++ b\n+x", verification_summary="tests: geslaagd",
                    acceptance=["A"], context="kennis A")
        self.cache.review(**args)
        uit = self.cache.review(**args)
        self.assertEqual(self.inner.review_calls, 1)
        self.assertEqual(uit.verdict, Verdict.PASS)

    def test_een_gewijzigde_diff_wordt_wel_opnieuw_beoordeeld(self):
        self.opzet()
        basis = dict(verification_summary="tests: geslaagd", acceptance=["A"],
                     context="kennis A")
        self.cache.review(diff="--- a\n+++ b\n+x", **basis)
        self.cache.review(diff="--- a\n+++ b\n+y", **basis)
        self.assertEqual(self.inner.review_calls, 2)

    def test_gewijzigde_acceptatiecriteria_worden_opnieuw_beoordeeld(self):
        self.opzet()
        basis = dict(diff="--- a\n+++ b\n+x", verification_summary="tests: geslaagd",
                     context="kennis A")
        self.cache.review(acceptance=["A"], **basis)
        self.cache.review(acceptance=["A", "B"], **basis)
        self.assertEqual(self.inner.review_calls, 2)

    def test_een_andere_verificatie_uitslag_wordt_opnieuw_beoordeeld(self):
        self.opzet()
        basis = dict(diff="--- a\n+++ b\n+x", acceptance=["A"], context="kennis A")
        self.cache.review(verification_summary="tests: geslaagd", **basis)
        self.cache.review(verification_summary="tests: GEFAALD", **basis)
        self.assertEqual(self.inner.review_calls, 2)

    def test_de_cache_van_een_project_lekt_niet_naar_een_ander(self):
        self.opzet()
        tweede = self.make_project("tweede")
        cache2 = ReviewCache(self.inner, self.db.scope("tweede"), "reviewer-test")
        vragen = [Question(text="Welke munteenheid?")]
        self.cache.answer(questions=vragen, context="kennis A")
        cache2.answer(questions=vragen, context="kennis A")
        self.assertEqual(self.inner.answer_calls, 2, "projecten delen nooit een cache")

    def test_een_treffer_boekt_geen_kosten(self):
        self.opzet()
        vragen = [Question(text="Welke munteenheid?")]
        self.cache.answer(questions=vragen, context="kennis A")
        tweede = self.cache.answer(questions=vragen, context="kennis A")
        self.assertIsNone(tweede.usage, "er is niets betaald, dus er valt niets te boeken")


class Maandkosten(TempCase):
    def test_kosten_per_maand_zijn_op_te_vragen(self):
        scope = self.db.scope("pilot")
        for dag, bedrag in [("2026-09-01", 1.0), ("2026-09-30", 2.0), ("2026-10-01", 5.0)]:
            scope.record_call(phase="p", role="r", model="m", tokens_in=0, tokens_out=0,
                              cached_in=0, cost_eur=bedrag, day=dag)
        self.assertEqual(scope.spend_month("2026-09"), 3.0)
        self.assertEqual(scope.spend_month("2026-10"), 5.0)

    def test_maandkosten_blijven_per_project_gescheiden(self):
        self.db.scope("a").record_call(phase="p", role="r", model="m", tokens_in=0,
                                       tokens_out=0, cached_in=0, cost_eur=4.0,
                                       day="2026-09-05")
        self.assertEqual(self.db.scope("b").spend_month("2026-09"), 0.0)


class VeiligheidGaatVoorBesparing(TempCase):
    def test_zonder_bevestigde_bron_geen_auto_ook_al_kost_dat_een_ronde(self):
        from orchestrator.triage import TriageContext, TriageEngine

        store = KnowledgeStore(self.tmp / "kennis")
        store.scaffold("demo")
        niet_bevestigd = store.append_decision("Knoptekst", "Bewaren.", source="model",
                                               confirmed_by_human=False)
        store.load()
        engine = TriageEngine(TriageContext(
            knowledge=store, repo_root=self.tmp, has_independent_work=True))
        besluit = engine.decide(Question(
            text="Welke knoptekst?", proposed_answer="Bewaren",
            citations=[Citation(f"kb:{niet_bevestigd}")],
        ))
        self.assertNotEqual(besluit.outcome.value, "auto")


class KostenVerdeling(TempCase):
    """De verdeling Claude / GPT moet op rol gaan, niet op modelnaam."""

    def test_verdeling_klopt_ook_bij_modelnamen_zonder_merk(self):
        from orchestrator.runreport import build_report, format_report

        self.make_project("pilot")
        scope = self.db.scope("pilot")
        task_id = scope.add_task("A", acceptance=["A"])
        scope.record_call(phase="implement", role="uitvoerder", model="executor-test",
                          tokens_in=1000, tokens_out=500, cached_in=0, cost_eur=0.02,
                          task_id=task_id)
        scope.record_call(phase="review", role="beoordelaar", model="reviewer-test",
                          tokens_in=800, tokens_out=200, cached_in=0, cost_eur=0.005,
                          task_id=task_id)

        from orchestrator import projects as projects_mod
        project = projects_mod.load(self.settings, "pilot")
        d = build_report(scope, project, task_id).data["9b_kosten_per_aanbieder"]
        self.assertAlmostEqual(d["Claude"]["kosten_eur"], 0.02)
        self.assertAlmostEqual(d["GPT"]["kosten_eur"], 0.005)

        tekst = format_report(build_report(scope, project, task_id))
        self.assertIn("Claude", tekst)
        self.assertIn("GPT", tekst)
