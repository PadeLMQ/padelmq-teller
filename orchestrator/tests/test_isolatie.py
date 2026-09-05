"""Projecten mogen elkaars gegevens nooit zien."""

from tests.base import TempCase


class Isolatie(TempCase):
    def test_taken_blijven_bij_hun_project(self):
        alpha = self.db.scope("alpha")
        beta = self.db.scope("beta")
        a = alpha.add_task("taak van alpha")
        b = beta.add_task("taak van beta")

        self.assertEqual([r["title"] for r in alpha.tasks()], ["taak van alpha"])
        self.assertEqual([r["title"] for r in beta.tasks()], ["taak van beta"])
        self.assertIsNone(alpha.task(b), "alpha mag de taak van beta niet kunnen opvragen")
        self.assertIsNone(beta.task(a), "beta mag de taak van alpha niet kunnen opvragen")

    def test_vragen_en_kosten_blijven_gescheiden(self):
        alpha = self.db.scope("alpha")
        beta = self.db.scope("beta")
        alpha.add_question("mag dit?", "park", "mag dit?")
        alpha.record_call(phase="p", role="r", model="m", tokens_in=1000,
                          tokens_out=100, cached_in=0, cost_eur=1.0, day="2026-09-05")

        self.assertEqual(len(beta.open_questions()), 0)
        self.assertEqual(beta.spend_today("2026-09-05"), 0.0)
        self.assertEqual(alpha.spend_today("2026-09-05"), 1.0)

    def test_set_task_weigert_onbekende_velden(self):
        scope = self.db.scope("alpha")
        task_id = scope.add_task("x")
        with self.assertRaises(ValueError):
            scope.set_task(task_id, project_id=99)

    def test_gelijke_vraag_wordt_ontdubbeld(self):
        scope = self.db.scope("alpha")
        first = scope.add_question("Btw incl of excl?", "park", "btw incl of excl?")
        second = scope.add_question("Btw incl of excl?", "park", "btw incl of excl?")
        self.assertEqual(first, second)
        self.assertEqual(len(scope.open_questions()), 1)
