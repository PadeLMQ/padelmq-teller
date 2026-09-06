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
        self.settings.budget_task_eur = 2.0  # expliciet, niet de standaard
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


class Budgetgrenzen(TempCase):
    """De remmen staan hoger, maar ze staan er nog.

    Verhoogd op verzoek van de eigenaar op 2026-09-06, nadat een taak stukliep
    op $2,1448 tegen een grens van $2,00. Deze test legt de afgesproken hoogtes
    vast, en vooral de verhouding: de rongrens moet ONDER de taakgrens liggen,
    anders is er geen rem per ronde meer, en de taakgrens moet onder het
    dagbudget liggen, anders kan één taak de dag opmaken.
    """

    def test_afgesproken_hoogtes(self):
        from orchestrator.config import Settings

        s = Settings.from_env()
        self.assertEqual(s.budget_task_eur, 5.0)
        self.assertEqual(s.budget_project_daily_eur, 15.0)
        self.assertEqual(s.budget_global_daily_eur, 15.0)

    def test_de_remmen_staan_niet_uit(self):
        from orchestrator.config import Settings

        s = Settings.from_env()
        for naam in ("budget_run_eur", "budget_task_eur",
                     "budget_project_daily_eur", "budget_global_daily_eur"):
            self.assertGreater(getattr(s, naam), 0, f"{naam} staat uit")

    def test_de_verhouding_klopt(self):
        from orchestrator.config import Settings

        s = Settings.from_env()
        # Met tegenzin <=: de schatting vóór een aanroep bleek er tot achtvoudig
        # naast te zitten ($4,2903 verbruikt voor de poort aansloeg), en een
        # rongrens onder de taakgrens weigert dan de tweede aanroep van elke taak.
        self.assertLessEqual(s.budget_run_eur, s.budget_task_eur,
                             "een run mag nooit meer mogen dan de taak waar hij bij hoort")
        self.assertLessEqual(s.budget_task_eur, s.budget_project_daily_eur,
                             "één taak mag het dagbudget van een project niet kunnen opmaken")
        self.assertLessEqual(s.budget_project_daily_eur, s.budget_global_daily_eur,
                             "een project mag niet meer mogen dan het geheel")
