"""Herstel na crash of herstart, zonder handmatige tussenkomst."""

import unittest

from orchestrator.models import TaskStatus
from orchestrator.recovery import MAX_HERSTELPOGINGEN, recover

try:
    from tests.base import TempCase
except ImportError:  # pragma: no cover
    from base import TempCase


class Herstellen(TempCase):
    def setUp(self):
        super().setUp()
        self.make_project("h")
        self.scope = self.db.scope("h")

    def _taak(self, status: str) -> int:
        task_id = self.scope.add_task("t", "s", ["a"])
        self.scope.set_task(task_id, status=status)
        return task_id

    def test_verweesde_run_wordt_afgesloten(self):
        task_id = self._taak(TaskStatus.IMPLEMENTING.value)
        run_id = self.scope.start_run(task_id, "task")

        herstel = recover(self.scope)

        self.assertIn(run_id, herstel.verweesde_runs)
        rij = self.db.conn.execute("SELECT ended_at, outcome FROM runs WHERE id = ?",
                                   (run_id,)).fetchone()
        self.assertIsNotNone(rij["ended_at"])
        self.assertEqual(rij["outcome"], "verweesd")

    def test_geld_van_een_verweesde_run_blijft_zichtbaar(self):
        task_id = self._taak(TaskStatus.IMPLEMENTING.value)
        run_id = self.scope.start_run(task_id, "task")
        self.scope.record_call(phase="implement", role="uitvoerder", model="executor-test",
                               tokens_in=1, tokens_out=1, cached_in=0, cost_eur=0.4,
                               task_id=task_id, run_id=run_id, day="2026-09-05")
        recover(self.scope)
        rij = self.db.conn.execute(
            "SELECT wasted_reason FROM calls WHERE run_id = ?", (run_id,)).fetchone()
        self.assertIn("verweesd", rij["wasted_reason"])

    def test_onderbroken_taak_komt_terug_in_de_rij(self):
        for status in ("baseline", "answering", "implementing", "verifying",
                       "reviewing", "committing"):
            with self.subTest(status=status):
                task_id = self._taak(status)
                recover(self.scope)
                self.assertEqual(self.scope.task(task_id)["status"],
                                 TaskStatus.QUEUED.value)

    def test_gefaalde_taak_wordt_hervat(self):
        """Geen handmatige requeue meer nodig."""
        task_id = self._taak(TaskStatus.FAILED.value)
        recover(self.scope)
        self.assertEqual(self.scope.task(task_id)["status"], TaskStatus.QUEUED.value)

    def test_wachten_op_een_mens_is_geen_storing(self):
        for status in (TaskStatus.BLOCKED.value, TaskStatus.PARKED.value):
            with self.subTest(status=status):
                task_id = self._taak(status)
                recover(self.scope)
                self.assertEqual(
                    self.scope.task(task_id)["status"], status,
                    "een taak die op een antwoord wacht is onterecht hervat",
                )

    def test_afgeronde_taken_blijven_afgerond(self):
        for status in (TaskStatus.DONE.value, TaskStatus.PR_OPEN.value):
            with self.subTest(status=status):
                task_id = self._taak(status)
                recover(self.scope)
                self.assertEqual(self.scope.task(task_id)["status"], status)

    def test_niet_eindeloos_herstellen(self):
        """Een taak die telkens omvalt heeft een probleem dat herstarten niet oplost."""
        task_id = self._taak(TaskStatus.FAILED.value)
        for _ in range(MAX_HERSTELPOGINGEN):
            recover(self.scope)
            self.scope.set_task(task_id, status=TaskStatus.FAILED.value)

        herstel = recover(self.scope)

        self.assertIn(task_id, herstel.opgegeven_taken)
        self.assertEqual(self.scope.task(task_id)["status"], TaskStatus.FAILED.value)
        events = [r for r in self.scope.events(limit=50) if r["kind"] == "herstel-opgegeven"]
        self.assertTrue(events, "het opgeven is niet vastgelegd")

    def test_herstel_blijft_binnen_het_project(self):
        ander = self.make_project("ander")
        ander_scope = self.db.scope("ander")
        ander_taak = ander_scope.add_task("t", "s", ["a"])
        ander_scope.set_task(ander_taak, status=TaskStatus.IMPLEMENTING.value)

        self._taak(TaskStatus.IMPLEMENTING.value)
        recover(self.scope)

        self.assertEqual(
            ander_scope.task(ander_taak)["status"], TaskStatus.IMPLEMENTING.value,
            "herstel van het ene project raakte het andere",
        )

    def test_niets_te_doen_is_stil(self):
        self.assertFalse(recover(self.scope).iets_gedaan)


if __name__ == "__main__":
    unittest.main()


class BudgetstopIsGeenCrash(TempCase):
    """Een taak die op het budget strandt moet terugkomen als de grens omhoog gaat.

    Wat er werkelijk gebeurde op 2026-09-06: taak 2 liep op $2,1448 tegen een
    grens van $2,00. Het herstel bood haar drie keer opnieuw aan, ze viel drie
    keer op dezelfde muur, er kwamen drie issues "Budget bereikt", en daarna gold
    ze als definitief mislukt. Toen de eigenaar de grens verhoogde kon ze niet
    meer terugkomen.
    """

    def _scope(self):
        self.db.ensure_project("p")
        return self.db.scope("p")

    def _gestrand(self, scope, grens=2.0, dag="2026-09-06", niveau="taak 2"):
        from orchestrator.models import TaskStatus

        tid = scope.add_task("gestrande taak", acceptance=["werkt"])
        scope.set_task(tid, status=TaskStatus.FAILED.value)
        scope.log("budget", {"niveau": niveau, "grens": grens, "besteed": 2.1448,
                             "dag": dag, "detail": "budget bereikt"}, task_id=tid)
        return tid

    def test_hogere_grens_laat_de_taak_terugkomen(self):
        from orchestrator.models import TaskStatus
        from orchestrator.recovery import recover

        scope = self._scope()
        tid = self._gestrand(scope, grens=2.0)
        self.settings.budget_task_eur = 5.0

        uitkomst = recover(scope, self.settings, vandaag="2026-09-06")
        self.assertIn(tid, uitkomst.hervatte_taken)
        self.assertEqual(scope.task(tid)["status"], TaskStatus.QUEUED.value)

    def test_zonder_verandering_blijft_hij_staan(self):
        """Anders probeert hij elke ronde opnieuw en meldt hij elke ronde opnieuw."""
        from orchestrator.models import TaskStatus
        from orchestrator.recovery import recover

        scope = self._scope()
        tid = self._gestrand(scope, grens=2.0)
        self.settings.budget_task_eur = 2.0

        for _ in range(5):
            uitkomst = recover(scope, self.settings, vandaag="2026-09-06")
            self.assertNotIn(tid, uitkomst.hervatte_taken)
        self.assertEqual(scope.task(tid)["status"], TaskStatus.FAILED.value)

    def test_een_nieuwe_dag_geeft_het_dagbudget_terug(self):
        from orchestrator.recovery import recover

        scope = self._scope()
        tid = self._gestrand(scope, grens=15.0, niveau="project p vandaag")
        self.settings.budget_project_daily_eur = 15.0

        self.assertNotIn(tid, recover(scope, self.settings, vandaag="2026-09-06").hervatte_taken)
        self.assertIn(tid, recover(scope, self.settings, vandaag="2026-09-07").hervatte_taken)

    def test_een_budgetstop_verbruikt_geen_herstelpoging(self):
        """Drie budgetstops maakten de taak definitief verloren. Dat mag niet."""
        from orchestrator.recovery import recover

        scope = self._scope()
        tid = self._gestrand(scope, grens=2.0)
        for _ in range(6):
            recover(scope, self.settings, vandaag="2026-09-06")
        soorten = [e["kind"] for e in scope.events(limit=100)]
        self.assertNotIn("herstel-opgegeven", soorten)

    def test_een_echte_crash_wordt_nog_steeds_beperkt_hersteld(self):
        """De grens op herstelpogingen blijft gelden voor wat wél een crash is."""
        from orchestrator.models import TaskStatus
        from orchestrator.recovery import recover

        scope = self._scope()
        tid = scope.add_task("kapotte taak", acceptance=["werkt"])
        for _ in range(6):
            scope.set_task(tid, status=TaskStatus.IMPLEMENTING.value)
            recover(scope, self.settings, vandaag="2026-09-06")
        soorten = [e["kind"] for e in scope.events(limit=100)]
        self.assertIn("herstel-opgegeven", soorten)


class ElkeAanroepGeeftDeInstellingenMee(TempCase):
    """Zonder instellingen kan het herstel een budgetstop niet beoordelen.

    De budgetgrens staat in de instellingen. Wordt die niet meegegeven, dan
    blijft een op budget gestrande taak liggen zonder dat iemand ziet waarom --
    de functie doet dan gewoon niets, stilletjes.
    """

    def test_geen_enkele_aanroep_vergeet_de_instellingen(self):
        import inspect
        import re

        from orchestrator import cli

        # Op regelniveau, niet met een haakjes-regex: db.scope(slug) heeft zelf
        # haakjes, en een regex die daarop struikelt toetst iets anders dan hij
        # beweert.
        regels = [r.strip() for r in inspect.getsource(cli).splitlines()
                  if re.search(r"\brecover\(", r) and "def recover" not in r]
        self.assertTrue(regels, "geen enkele aanroep van recover() gevonden")
        for regel in regels:
            with self.subTest(aanroep=regel):
                self.assertIn("settings", regel,
                              "recover() zonder instellingen kan geen budgetstop hervatten")
