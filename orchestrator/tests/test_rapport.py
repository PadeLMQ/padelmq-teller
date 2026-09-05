"""PR-omschrijving en dagrapport bevatten wat het ontwerp voorschrijft."""

from orchestrator.adapters import Alternative, Finding, ReviewResult
from orchestrator.models import (
    CheckResult, Citation, Question, VerificationResult, Verdict, VerificationStrength,
)
from orchestrator.report import daily_digest, pr_body
from tests.base import TempCase


class Rapporten(TempCase):
    def test_pr_omschrijving_bevat_alle_verplichte_onderdelen(self):
        project = self.make_project("demo", checks={"tests": "pytest"})
        scope = self.db.scope("demo")
        task_id = scope.add_task("Voeg X toe", spec="omdat Y", acceptance=["A", "B"])
        verification = VerificationResult([CheckResult("tests", "pytest", 0, "")])
        review = ReviewResult(
            verdict=Verdict.PASS,
            findings=[Finding("minor", "app.py", "kan eenvoudiger")],
            acceptance_met=["A", "B"],
            alternative=Alternative("Gebruik de bestaande helper", "minder code",
                                    "app.py:12", "een half uur", "later"),
        )
        body = pr_body(
            project=project, task=scope.task(task_id), acceptance=["A", "B"],
            verification=verification, review=review,
            auto_answers=[Question(text="Munteenheid?", proposed_answer="euro",
                                   citations=[Citation("kb:D-001")])],
            parked=["Welke knoptekst?"],
        )
        for verplicht in [
            "Wat er gewijzigd is", "Acceptatiecriteria", "Verificatie",
            "automatisch beantwoord", "kb:D-001", "Resterende risico",
            "Geparkeerde vragen", "beter alternatief", "nooit automatisch gemerged",
        ]:
            self.assertIn(verplicht, body, f"ontbreekt in de PR-omschrijving: {verplicht}")

    def test_zwakke_verificatie_geeft_een_waarschuwing_in_de_pr(self):
        project = self.make_project("zwak", checks={})
        scope = self.db.scope("zwak")
        task_id = scope.add_task("Iets", acceptance=["A"])
        body = pr_body(
            project=project, task=scope.task(task_id), acceptance=["A"],
            verification=VerificationResult([]), review=None, auto_answers=[], parked=[],
        )
        self.assertEqual(project.strength, VerificationStrength.WEAK)
        self.assertIn("beperkt hard bewijs", body)

    def test_geheimen_komen_niet_in_de_pr(self):
        project = self.make_project("demo")
        scope = self.db.scope("demo")
        task_id = scope.add_task("X", spec='token = "geheimwaarde12345"', acceptance=["A"])
        body = pr_body(
            project=project, task=scope.task(task_id), acceptance=["A"],
            verification=VerificationResult([]), review=None, auto_answers=[], parked=[],
        )
        self.assertNotIn("geheimwaarde12345", body)

    def test_dagrapport_groepeert_per_project(self):
        self.make_project("alpha")
        self.make_project("beta")
        alpha = self.db.scope("alpha")
        alpha.add_question("Welke knoptekst?", "park", "knoptekst")
        beta = self.db.scope("beta")
        beta.add_question("Btw incl?", "block", "btw incl")
        beta.record_call(phase="p", role="r", model="m", tokens_in=0, tokens_out=0,
                         cached_in=0, cost_eur=1.25, day="2026-09-05")

        text = daily_digest(self.db, ["alpha", "beta"], day="2026-09-05")
        self.assertIn("## alpha", text)
        self.assertIn("## beta", text)
        self.assertIn("Welke knoptekst?", text)
        self.assertIn("Btw incl?", text)
        self.assertIn("€1.25", text)
        self.assertIn("Totale kosten vandaag: €1.25", text)
