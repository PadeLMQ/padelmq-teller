"""Deterministische controles: verzonnen waarden, geen vooruitgang, redactie."""

import unittest

from orchestrator.adapters import Finding, ReviewResult
from orchestrator.adapters.claude import assumptions_without_source
from orchestrator.adapters.reviewer import validate_verdict
from orchestrator.guards import NoProgressDetector, detect_invented_values
from orchestrator.models import CheckResult, Verdict, VerificationResult
from orchestrator.redact import redact_diff, redact_text
from orchestrator.verify import infer_strength
from orchestrator.models import VerificationStrength

DIFF = """diff --git a/app.py b/app.py
--- a/app.py
+++ b/app.py
@@ -1,2 +1,6 @@
 def total(x):
+    btw = 0.21
+    verzendkosten = 4.95
+    items = [1, 2, 3]
     return x
"""


class VerzonnenWaarden(unittest.TestCase):
    def test_onbekende_waarde_wordt_gemeld(self):
        findings = detect_invented_values(DIFF, known_text="btw is 0.21 volgens D-003")
        self.assertEqual([f.value for f in findings], ["4.95"])

    def test_bekende_waarde_wordt_niet_gemeld(self):
        findings = detect_invented_values(
            DIFF, known_text="btw is 0.21 en verzendkosten zijn 4.95"
        )
        self.assertEqual(findings, [])

    def test_gewone_getallen_geven_geen_vals_alarm(self):
        diff = "+++ b/a.py\n@@ -1 +1,2 @@\n+    for i in range(3):\n+        items = [1, 2]\n"
        self.assertEqual(detect_invented_values(diff, ""), [])

    def test_percentage_wordt_gevangen(self):
        diff = "+++ b/a.py\n@@ -1 +1,2 @@\n+    korting = 15%\n"
        self.assertEqual([f.reason for f in detect_invented_values(diff, "")], ["percentage"])


class GeenVooruitgang(unittest.TestCase):
    def test_tweede_keer_dezelfde_handtekening_stopt(self):
        detector = NoProgressDetector()
        self.assertFalse(detector.stuck("a"))
        self.assertTrue(detector.stuck("a"))

    def test_handtekening_uit_de_verificatie(self):
        result = VerificationResult([
            CheckResult("tests", "pytest", 1, "FAILED test_x\nmeer regels"),
            CheckResult("lint", "ruff", 0, ""),
        ])
        self.assertIn("tests|1|FAILED test_x", result.signature())
        self.assertFalse(result.ok)


class Aannames(unittest.TestCase):
    def test_aanname_zonder_bron_wordt_gemeld(self):
        self.assertEqual(
            assumptions_without_source(["Euro || kb:D-002", "Marge 30% || "]),
            ["Marge 30%"],
        )


class Redactie(unittest.TestCase):
    def test_sleutels_worden_geredigeerd(self):
        text = 'SHOP_CLIENT_SECRET = "abc123geheimwaarde"\nshpat_ABCdef123456'
        out = redact_text(text)
        self.assertNotIn("abc123geheimwaarde", out)
        self.assertNotIn("shpat_ABCdef123456", out)

    def test_env_bestand_gaat_niet_mee(self):
        diff = (
            "diff --git a/.env b/.env\n--- a/.env\n+++ b/.env\n@@\n+TOKEN=zeergeheim123\n"
            "diff --git a/app.py b/app.py\n--- a/app.py\n+++ b/app.py\n@@\n+print('hoi')\n"
        )
        out = redact_diff(diff)
        self.assertNotIn("zeergeheim123", out)
        self.assertIn("print('hoi')", out)


class Beoordelaar(unittest.TestCase):
    def test_pass_met_openstaande_criteria_wordt_verworpen(self):
        review = validate_verdict(
            ReviewResult(verdict=Verdict.PASS, acceptance_missing=["criterium-3"]), []
        )
        self.assertEqual(review.verdict, Verdict.REVISE)

    def test_pass_met_blocker_wordt_verworpen(self):
        review = validate_verdict(
            ReviewResult(verdict=Verdict.PASS,
                         findings=[Finding("blocker", "a.py", "lek")]), []
        )
        self.assertEqual(review.verdict, Verdict.REVISE)

    def test_geldige_pass_blijft_staan(self):
        review = validate_verdict(ReviewResult(verdict=Verdict.PASS), [])
        self.assertEqual(review.verdict, Verdict.PASS)


class Verificatiesterkte(unittest.TestCase):
    def test_zonder_checks_is_zwak(self):
        self.assertEqual(infer_strength({}), VerificationStrength.WEAK)

    def test_alleen_lint_is_zwak(self):
        self.assertEqual(infer_strength({"lint": "ruff check"}), VerificationStrength.WEAK)

    def test_tests_alleen_is_matig(self):
        self.assertEqual(
            infer_strength({"tests": "pytest -q"}), VerificationStrength.MEDIUM
        )

    def test_tests_en_build_is_sterk(self):
        self.assertEqual(
            infer_strength({"tests": "pytest -q", "types": "mypy ."}),
            VerificationStrength.STRONG,
        )

    def test_iteratielimiet_schaalt_mee(self):
        self.assertEqual(VerificationStrength.WEAK.max_implement_iterations, 1)
        self.assertEqual(VerificationStrength.STRONG.max_implement_iterations, 5)
