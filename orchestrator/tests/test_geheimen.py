"""Geen geheim mag ooit in git belanden."""

from orchestrator.secret_scan import format_hits, scan_text, scan_tree
from tests.base import TempCase


class Geheimen(TempCase):
    def test_bekende_sleutelvormen_worden_gevonden(self):
        gevallen = {  # nep-geheim: verzonnen waarden, alleen voor deze test
            "Shopify-token": "TOKEN = 'shpat_" + "abcdefghij1234567890'",
            "OpenAI-sleutel": 'key = "sk-' + 'abcdefghijklmnopqrstuvwxyz12"',
            "GitHub-token": "ghp_" + "abcdefghijklmnopqrstuvwxyz123456",
            "privesleutel": "-----BEGIN RSA PRIVATE" + " KEY-----",
        }
        for verwacht, regel in gevallen.items():
            hits = scan_text("x.py", regel)
            self.assertTrue(hits, f"niet gevonden: {verwacht}")

    def test_ingevulde_geheime_variabele_wordt_gevonden(self):
        hits = scan_text(".env", "SHOPIFY_ADMIN_TOKEN=werkelijkgeheimewaarde")
        self.assertEqual(len(hits), 1)

    def test_lege_en_placeholder_waarden_zijn_geen_alarm(self):
        for regel in ["SHOPIFY_ADMIN_TOKEN=", "OPENAI_API_KEY=<vul in>",
                      "SESSION_SECRET=${SECRET}", "# TOKEN=voorbeeld"]:
            self.assertEqual(scan_text(".env", regel), [], regel)

    def test_env_bestand_wordt_geweigerd_ongeacht_inhoud(self):
        root = self.tmp / "repo"
        root.mkdir()
        (root / ".env").write_text("LEEG=\n", encoding="utf-8")
        hits = scan_tree(root)
        self.assertEqual(len(hits), 1)
        self.assertIn("hoort niet in git", hits[0].kind)

    def test_voorbeeldbestand_mag_wel(self):
        root = self.tmp / "repo2"
        root.mkdir()
        (root / ".env.example").write_text("OPENAI_API_KEY=\n", encoding="utf-8")
        self.assertEqual(scan_tree(root), [])

    def test_chatgpt_export_wordt_geweigerd(self):
        root = self.tmp / "repo3"
        root.mkdir()
        (root / "conversations.json").write_text("[]", encoding="utf-8")
        self.assertEqual(len(scan_tree(root)), 1)

    def test_deze_repository_bevat_geen_geheimen(self):
        """Controleert de orkestrator-broncode zelf."""
        from pathlib import Path

        root = Path(__file__).resolve().parents[1]
        hits = scan_tree(root)
        self.assertEqual(hits, [], format_hits(hits))
