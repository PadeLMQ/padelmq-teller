"""De inspectie leest de werkelijke verificatie, en overdrijft niet."""

import json

from orchestrator.inspect import format_report, inspect
from orchestrator.models import VerificationStrength
from tests.base import TempCase


class Inspectie(TempCase):
    def npm_project(self, scripts: dict) -> object:
        root = self.tmp / "app"
        (root / "src" / "lib").mkdir(parents=True)
        (root / "tests").mkdir()
        (root / "package.json").write_text(
            json.dumps({"name": "app", "scripts": scripts}), encoding="utf-8"
        )
        return root

    def test_npm_scripts_worden_herkend(self):
        root = self.npm_project({"test": "vitest run", "typecheck": "tsc --noEmit",
                                 "lint": "next lint", "build": "next build"})
        result = inspect(root)
        self.assertEqual(result.checks["tests"], "npm run test")
        self.assertEqual(result.checks["typecheck"], "npm run typecheck")
        self.assertEqual(result.strength, VerificationStrength.STRONG)

    def test_zonder_tests_is_de_sterkte_zwak(self):
        root = self.npm_project({"build": "next build"})
        result = inspect(root)
        self.assertEqual(result.strength, VerificationStrength.MEDIUM)
        result2 = inspect(self.tmp / "leeg")
        self.assertEqual(result2.strength, VerificationStrength.WEAK)

    def test_modules_zonder_toegewijde_test_worden_gemeld(self):
        root = self.npm_project({"test": "vitest run"})
        for name in ("repricing.ts", "brain.ts", "priceSync.ts"):
            (root / "src" / "lib" / name).write_text("export const x = 1\n", encoding="utf-8")
        (root / "tests" / "priceSync.test.ts").write_text("test\n", encoding="utf-8")
        result = inspect(root)
        self.assertIn("repricing", result.untested)
        self.assertIn("brain", result.untested)
        self.assertNotIn("priceSync", result.untested)

    def test_rapport_zegt_dat_dekking_indirect_kan_zijn(self):
        root = self.npm_project({"test": "vitest run"})
        (root / "src" / "lib" / "repricing.ts").write_text("x\n", encoding="utf-8")
        report = format_report(inspect(root))
        self.assertIn("indirect gedekt", report)
        self.assertIn("Modules zonder toegewijd testbestand", report)

    def test_zwakke_sterkte_krijgt_een_waarschuwing_in_het_rapport(self):
        report = format_report(inspect(self.npm_project({"build": "next build"})))
        self.assertIn("bouwt de lus niet zelfstandig door", report)
