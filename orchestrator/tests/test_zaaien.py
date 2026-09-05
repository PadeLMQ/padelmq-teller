"""Kennis meegeven aan een vers volume — en daarna nooit meer.

De aanleiding: het Railway-volume kreeg een lege kennisbasis, terwijl alles wat
de eigenaar had bevestigd (welke checks hard zijn, wat nooit automatisch mag)
alleen op de schijf van één sessie stond. Een orkestrator zonder die kennis
stelt vragen die al beantwoord zijn, of kent de verboden niet.

Wat hier vastligt is vooral wat er NIET mag gebeuren: overschrijven.
"""

import unittest
from pathlib import Path

from tests.base import TempCase

from orchestrator.knowledge import KnowledgeStore
from orchestrator.zaaien import MERKTEKEN, ZaaiGeweigerd, zaai

ITEM = """# p — verboden

_Wat hier nooit automatisch mag gebeuren._

## VB-1 · Geen live bedrijfsacties
status: bevestigd
datum: 2026-09-05
bron: beslissing van de eigenaar

Nooit automatisch: een merge naar main, een deploy, een Shopify live write.
"""


class Zaaien(TempCase):
    def setUp(self) -> None:
        super().setUp()
        self.kennis = self.tmp / "project" / "kennis"
        self.bron = self.tmp / "repo" / ".orchestrator" / "kennis"
        self.bron.mkdir(parents=True)

    def _scaffold(self) -> None:
        KnowledgeStore(self.kennis).scaffold("p")

    def test_lege_kennisbasis_wordt_gevuld(self):
        self._scaffold()
        (self.bron / "verboden.md").write_text(ITEM)
        uitkomst = zaai(self.kennis, self.bron)
        self.assertEqual(uitkomst.geschreven, ["verboden.md"])
        items = KnowledgeStore(self.kennis).load()
        self.assertIn("VB-1", items)
        self.assertTrue(items["VB-1"].citable)

    def test_zaaien_gebeurt_maar_een_keer(self):
        """Zonder deze grens zou elke deploy de kennis terugzetten naar het
        zaaigoed, en zou werk van weken stil verdwijnen."""
        self._scaffold()
        (self.bron / "verboden.md").write_text(ITEM)
        zaai(self.kennis, self.bron)
        (self.kennis / "verboden.md").write_text(ITEM.replace("VB-1", "VB-9"))

        tweede = zaai(self.kennis, self.bron)
        self.assertIn("eerder al gezaaid", tweede.reden)
        self.assertIn("VB-9", (self.kennis / "verboden.md").read_text())
        self.assertNotIn("VB-1", (self.kennis / "verboden.md").read_text())

    def test_bestand_met_bestaande_kennis_wordt_nooit_overschreven(self):
        """Ook bij de allereerste zaaibeurt: wat er staat, blijft staan."""
        self._scaffold()
        (self.kennis / "verboden.md").write_text(ITEM.replace("VB-1", "EIGEN-1"))
        (self.bron / "verboden.md").write_text(ITEM)
        (self.bron / "doel.md").write_text("# p — doel\n\n## D-1 · Doel\nstatus: bevestigd\n\nx\n")

        uitkomst = zaai(self.kennis, self.bron)
        self.assertEqual(uitkomst.overgeslagen, ["verboden.md"])
        self.assertEqual(uitkomst.geschreven, ["doel.md"])
        self.assertIn("EIGEN-1", (self.kennis / "verboden.md").read_text())

    def test_vers_sjabloon_telt_niet_als_bestaande_kennis(self):
        """Een sjabloon heeft nul items; dat is leeg, geen inhoud om te sparen."""
        self._scaffold()
        (self.bron / "verboden.md").write_text(ITEM)
        self.assertEqual(zaai(self.kennis, self.bron).overgeslagen, [])

    def test_zonder_zaaigoed_gebeurt_er_niets(self):
        self._scaffold()
        uitkomst = zaai(self.kennis, self.tmp / "bestaat-niet")
        self.assertIn("geen zaaigoed", uitkomst.reden)
        self.assertFalse((self.kennis / MERKTEKEN).exists(),
                         "zonder zaaigoed hoort er geen merkteken te komen; "
                         "anders kan er later nooit meer gezaaid worden")

    def test_geheim_in_het_zaaigoed_weigert_alles(self):
        """Een repository is te bewerken door iedereen met schrijfrechten. Bij
        twijfel wordt er niets geschreven, niet gedeeltelijk."""
        self._scaffold()
        (self.bron / "verboden.md").write_text(ITEM)
        nep = "gh" + "p_" + "abcdefghijklmnopqrstuvwxyz0123"
        (self.bron / "doel.md").write_text(f"# p — doel\n\ntoken: {nep}\n")

        with self.assertRaises(ZaaiGeweigerd):
            zaai(self.kennis, self.bron)
        self.assertFalse((self.kennis / MERKTEKEN).exists())
        self.assertEqual(KnowledgeStore(self.kennis).load(), {},
                         "er mag niets geschreven zijn, ook niet het goede bestand")

    def test_alleen_bekende_kennisbestanden_worden_overgenomen(self):
        """Zaaigoed mag geen willekeurige bestanden op het volume zetten."""
        self._scaffold()
        (self.bron / "verboden.md").write_text(ITEM)
        (self.bron / "geheim-plan.md").write_text("# iets anders\n")
        zaai(self.kennis, self.bron)
        self.assertFalse((self.kennis / "geheim-plan.md").exists())

    def test_start_script_zaait_na_de_kloon_en_voor_de_controle(self):
        """Volgorde: het zaaigoed komt uit de kloon, dus die moet er eerst zijn."""
        wortel = Path(__file__).resolve().parents[2]
        script = (wortel / "deploy" / "railway" / "start.sh").read_text()
        self.assertLess(script.index("project bootstrap"), script.index("project seed"))
        self.assertLess(script.index("project seed"), script.index("cli startup"))


if __name__ == "__main__":
    unittest.main()
