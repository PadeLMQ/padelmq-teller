"""Verboden en live paden mogen nooit als verificatie kunnen draaien.

Dit is de poort waar de hele pilotafspraak op rust: de orkestrator automatiseert
softwareontwikkeling, geen bedrijfsvoering.
"""

from pathlib import Path

from orchestrator import projects as projects_mod
from orchestrator.verify import UnsafeCheck, VerifyAdapter, assert_safe_checks
from tests.base import TempCase

# Precies de scripts uit padelmq-pro die geen bedrijfsactie zijn.
VEILIG = {
    "tests": "npm run test",
    "typecheck": "npm run typecheck",
    "lint": "npm run lint",
    "build": "npm run build",
}

# Precies de scripts uit padelmq-pro die dat wél zijn.
VERBODEN = {
    "sync": "npm run sync",
    "daily": "npm run daily",
    "scan-priority": "npm run scan:priority",
    "scan-stock": "npm run scan:stock",
    "scan-urgent": "npm run scan:urgent",
    "import-shopify": "npm run import:shopify",
    "import-oldapp": "npm run import:oldapp",
    "setup-shops": "npm run setup:shops",
    "discover": "npm run discover:new",
    "bestsellers": "npm run flag:bestsellers",
    "seed": "npm run seed",
}


class VeiligeChecks(TempCase):
    def test_de_toegestane_checks_komen_erdoor(self):
        assert_safe_checks(VEILIG)  # werpt niet

    def test_elk_verboden_script_wordt_geweigerd(self):
        for naam, commando in VERBODEN.items():
            with self.subTest(script=naam):
                with self.assertRaises(UnsafeCheck, msg=f"{commando} werd toegelaten"):
                    assert_safe_checks({naam: commando})

    def test_ook_een_live_vlag_wordt_geweigerd(self):
        for commando in ["npm run something -- --live", "node x.js --push",
                         "make deploy", "npm run publish"]:
            with self.subTest(commando=commando):
                with self.assertRaises(UnsafeCheck):
                    assert_safe_checks({"x": commando})

    def test_schrijfvlaggen_in_de_omgeving_worden_geweigerd(self):
        with self.assertRaises(UnsafeCheck):
            assert_safe_checks({"x": 'ENABLE_STOCK_WRITE=true npm run test'})
        with self.assertRaises(UnsafeCheck):
            assert_safe_checks({"x": 'STOCK_SYNC_UP_ENABLED="true" npm run test'})

    def test_rechtstreekse_shopify_aanroepen_worden_geweigerd(self):
        with self.assertRaises(UnsafeCheck):
            assert_safe_checks({"x": "curl https://winkel.myshopify.com/admin/api/2025-10/graphql.json"})

    def test_een_verboden_commando_tussen_veilige_wordt_ook_gevangen(self):
        with self.assertRaises(UnsafeCheck) as ctx:
            assert_safe_checks({**VEILIG, "stiekem": "npm run sync"})
        self.assertIn("stiekem", str(ctx.exception))

    def test_de_uitvoerder_weigert_zelf_ook(self):
        """De poort zit in de uitvoerder, niet alleen in de configuratie.

        Zelfs als project.yaml gewijzigd wordt, komt er niets doorheen.
        """
        adapter = VerifyAdapter(timeout_seconds=5)
        bewijs = self.tmp / "bewijs.txt"
        with self.assertRaises(UnsafeCheck):
            adapter.run(self.tmp, {"sync": f"npm run sync && touch {bewijs}"})
        self.assertFalse(bewijs.exists(), "er mag niets uitgevoerd zijn")

    def test_een_project_met_een_verboden_check_kan_niet_toegevoegd_worden(self):
        with self.assertRaises(UnsafeCheck):
            projects_mod.add(self.settings, "fout", "/tmp/repo",
                             checks={"tests": "npm run test", "sync": "npm run sync"})
        self.assertNotIn("fout", projects_mod.list_projects(self.settings))

    def test_het_pilotproject_kan_wel_toegevoegd_worden(self):
        project = projects_mod.add(self.settings, "padelmq-pro", "/tmp/pilot", checks=VEILIG)
        self.assertEqual(project.strength.value, "sterk")
        self.assertEqual(set(project.checks), set(VEILIG))

    def test_veilige_checks_draaien_gewoon(self):
        adapter = VerifyAdapter(timeout_seconds=30)
        uit = adapter.run(Path.cwd(), {"ok": "python3 -c \"import sys; sys.exit(0)\""})
        self.assertTrue(uit.ok)


class VragenRegistreren(TempCase):
    """question-add mag geen spookproject aanmaken."""

    def test_onbekend_project_wordt_geweigerd(self):
        from orchestrator.cli import main

        with self.env():
            with self.assertRaises(projects_mod.ProjectError):
                main(["question-add", "bestaatniet", "Een vraag?"])

    def test_bestaand_project_werkt(self):
        from orchestrator.cli import main

        with self.env():
            projects_mod.add(self.settings, "pilot", "/tmp/pilot", checks=VEILIG)
            self.assertEqual(main(["question-add", "pilot", "Een vraag?"]), 0)
            # De opdrachtregel bouwt zijn eigen instellingen uit de omgeving;
            # we lezen dus de database die híj gebruikt, niet die van de test.
            from orchestrator.config import Settings
            from orchestrator.db import Database

            cli_db = Database(Settings.from_env().db_path)
            self.addCleanup(cli_db.close)
            vragen = cli_db.scope("pilot").open_questions()
            self.assertEqual(len(vragen), 1)
            self.assertEqual(vragen[0]["outcome"], "park")

    def env(self):
        import contextlib
        import os

        @contextlib.contextmanager
        def _env():
            bewaard = os.environ.get("ORCH_DATA_DIR")
            os.environ["ORCH_DATA_DIR"] = str(self.settings.data_dir)
            try:
                yield
            finally:
                if bewaard is None:
                    os.environ.pop("ORCH_DATA_DIR", None)
                else:
                    os.environ["ORCH_DATA_DIR"] = bewaard

        return _env()
