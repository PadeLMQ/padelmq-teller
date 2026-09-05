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
