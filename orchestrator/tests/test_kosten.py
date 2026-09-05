"""Kostenbewaking: vier niveaus, en de rem zit voor de aanroep."""

from orchestrator.cost import BudgetExceeded, CostGuard, Estimate
from tests.base import TempCase


class Kosten(TempCase):
    def setUp(self):
        super().setUp()
        self.warnings = []
        self.guard = CostGuard(
            self.db, self.settings,
            on_warning=lambda level, pct, spent, limit: self.warnings.append((level, pct)),
        )
        self.scope = self.db.scope("demo")

    def estimate(self, tokens_in=1_000_000, tokens_out=0):
        return Estimate("executor-test", tokens_in, tokens_out)

    def test_prijs_wordt_correct_gerekend(self):
        # 1M invoer à €5 plus 1M uitvoer à €25
        self.assertAlmostEqual(
            self.guard.estimate_cost(Estimate("executor-test", 1_000_000, 1_000_000)), 30.0
        )

    def test_onbekend_model_wordt_niet_geraden(self):
        with self.assertRaises(KeyError):
            self.guard.estimate_cost(Estimate("onbekend-model", 100, 100))

    def test_taakbudget_remt_voor_de_aanroep(self):
        self.settings.budget_task_eur = 2.0
        with self.assertRaises(BudgetExceeded) as ctx:
            self.guard.check(self.scope, self.estimate(1_000_000), task_id=1)
        self.assertIn("taak 1", str(ctx.exception))

    def test_dagbudget_van_het_project(self):
        self.settings.budget_task_eur = 100.0
        self.settings.budget_project_daily_eur = 3.0
        self.guard.record(self.scope, self.estimate(400_000), phase="p", role="r",
                          day="2026-09-05")  # €2
        with self.assertRaises(BudgetExceeded):
            self.guard.check(self.scope, self.estimate(400_000), day="2026-09-05")

    def test_globaal_dagbudget_telt_projecten_op(self):
        self.settings.budget_task_eur = 100.0
        self.settings.budget_project_daily_eur = 100.0
        self.settings.budget_global_daily_eur = 3.0
        self.guard.record(self.db.scope("alpha"), self.estimate(400_000),
                          phase="p", role="r", day="2026-09-05")
        with self.assertRaises(BudgetExceeded) as ctx:
            self.guard.check(self.db.scope("beta"), self.estimate(400_000), day="2026-09-05")
        self.assertIn("globaal", str(ctx.exception))

    def test_een_dure_run_kan_niet_over_de_limiet_schieten(self):
        """De rem zit voor de aanroep, dus er wordt niets geregistreerd."""
        self.settings.budget_global_daily_eur = 1.0
        with self.assertRaises(BudgetExceeded):
            self.guard.check(self.scope, self.estimate(1_000_000), day="2026-09-05")
        self.assertEqual(self.guard.global_spend_today("2026-09-05"), 0.0)

    def test_waarschuwingen_op_50_80_100(self):
        self.settings.budget_task_eur = 100.0
        self.settings.budget_project_daily_eur = 100.0
        self.settings.budget_global_daily_eur = 12.0
        for _ in range(4):  # vier aanroepen van EUR 3 vullen het budget precies
            self.guard.check(self.scope, self.estimate(600_000), day="2026-09-05")
            self.guard.record(self.scope, self.estimate(600_000), phase="p", role="r",
                              day="2026-09-05")
        stappen = sorted({pct for level, pct in self.warnings if level == "globaal vandaag"})
        self.assertEqual(stappen, [0.5, 0.8, 1.0])

    def test_aanroep_die_het_budget_zou_overschrijden_gaat_niet_door(self):
        """Waarschuwen is niet genoeg: de aanroep wordt geweigerd, niet afgekapt."""
        self.settings.budget_task_eur = 100.0
        self.settings.budget_project_daily_eur = 100.0
        self.settings.budget_global_daily_eur = 10.0
        for _ in range(3):  # tot EUR 9
            self.guard.check(self.scope, self.estimate(600_000), day="2026-09-05")
            self.guard.record(self.scope, self.estimate(600_000), phase="p", role="r",
                              day="2026-09-05")
        with self.assertRaises(BudgetExceeded):
            self.guard.check(self.scope, self.estimate(600_000), day="2026-09-05")
        self.assertAlmostEqual(self.guard.global_spend_today("2026-09-05"), 9.0)

    def test_rapport_splitst_per_project_model_en_rol(self):
        self.guard.record(self.db.scope("alpha"), Estimate("executor-test", 100_000, 0),
                          phase="implement", role="uitvoerder", day="2026-09-05")
        self.guard.record(self.db.scope("beta"), Estimate("reviewer-test", 100_000, 0),
                          phase="review", role="beoordelaar", day="2026-09-05")
        rapport = self.guard.report("2026-09-05")
        self.assertEqual(len(rapport), 2)
        self.assertEqual({r["project"] for r in rapport}, {"alpha", "beta"})
        self.assertEqual({r["role"] for r in rapport}, {"uitvoerder", "beoordelaar"})
