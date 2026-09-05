"""Twee projecten naast elkaar, zonder dat ze elkaar raken.

Isolatie is niet iets wat je erbij bouwt maar iets wat overal moet gelden:
kennis, taken, vragen, kosten, handtekeningen en herstel. Deze tests toetsen ze
allemaal, want één lek is genoeg om businessregels van het ene project in het
andere te laten landen.
"""

import unittest

from orchestrator.models import TaskStatus
from orchestrator.recovery import recover

try:
    from tests.base import TempCase
except ImportError:  # pragma: no cover
    from base import TempCase


class TweeProjecten(TempCase):
    def setUp(self):
        super().setUp()
        self.alpha = self.make_project("alpha")
        self.beta = self.make_project("beta")
        self.a = self.db.scope("alpha")
        self.b = self.db.scope("beta")

    def test_kennis_blijft_gescheiden(self):
        self.alpha.knowledge.append_decision(
            "Btw-weergave", "Inclusief btw.", source="mens", confirmed_by_human=True)
        self.assertEqual(self.beta.knowledge.load(), {},
                         "kennis van alpha is zichtbaar in beta")
        self.assertEqual(len(self.alpha.knowledge.load()), 1)

    def test_taken_blijven_gescheiden(self):
        self.a.add_task("taak van alpha", "s", ["a"])
        self.assertEqual(self.b.tasks(), [])
        self.assertIsNone(self.b.next_queued())

    def test_vragen_blijven_gescheiden(self):
        vraag = self.a.add_question("Iets?", "block", "vp-1")
        self.assertEqual(self.b.open_questions(), [])
        self.assertIsNone(self.b.question(vraag),
                          "een vraag van alpha is opvraagbaar via beta")

    def test_kosten_blijven_gescheiden(self):
        taak = self.a.add_task("t", "s", ["a"])
        run = self.a.start_run(taak, "task")
        self.a.record_call(phase="implement", role="uitvoerder", model="executor-test",
                           tokens_in=1, tokens_out=1, cached_in=0, cost_eur=0.5,
                           task_id=taak, run_id=run, day="2026-09-05")
        self.assertEqual(self.b.spend_today("2026-09-05"), 0.0)
        self.assertEqual(self.a.spend_today("2026-09-05"), 0.5)

    def test_handtekeningen_blijven_gescheiden(self):
        """Anders zou werk in het ene project een taak in het andere blokkeren."""
        taak_a = self.a.add_task("t", "s", ["a"])
        taak_b = self.b.add_task("t", "s", ["a"])
        self.a.remember_signature(taak_a, "impl:zelfde")
        self.assertFalse(self.b.signature_seen(taak_b, "impl:zelfde"))
        self.assertTrue(self.a.signature_seen(taak_a, "impl:zelfde"))

    def test_herstel_raakt_alleen_het_eigen_project(self):
        taak_a = self.a.add_task("t", "s", ["a"])
        taak_b = self.b.add_task("t", "s", ["a"])
        for scope, taak in ((self.a, taak_a), (self.b, taak_b)):
            scope.set_task(taak, status=TaskStatus.IMPLEMENTING.value)
            scope.start_run(taak, "task")

        recover(self.a)

        self.assertEqual(self.a.task(taak_a)["status"], TaskStatus.QUEUED.value)
        self.assertEqual(self.b.task(taak_b)["status"], TaskStatus.IMPLEMENTING.value,
                         "herstel van alpha heeft beta aangeraakt")

    def test_events_blijven_gescheiden(self):
        taak = self.a.add_task("t", "s", ["a"])
        self.a.log("iets", {"x": 1}, task_id=taak)
        self.assertEqual(self.b.events(limit=10), [])

    def test_gelijke_taaknummers_verwarren_niets(self):
        """Beide projecten beginnen bij hun eigen nummering."""
        a1 = self.a.add_task("alpha eerst", "s", ["a"])
        b1 = self.b.add_task("beta eerst", "s", ["a"])
        self.assertEqual(self.a.task(a1)["title"], "alpha eerst")
        self.assertEqual(self.b.task(b1)["title"], "beta eerst")
        if a1 == b1:
            self.assertNotEqual(self.a.task(a1)["title"], self.b.task(b1)["title"])


if __name__ == "__main__":
    unittest.main()
