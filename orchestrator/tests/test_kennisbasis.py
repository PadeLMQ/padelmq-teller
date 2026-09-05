"""Alleen een bevestigd item mag als bron dienen; alleen de mens bevestigt."""

from orchestrator.knowledge import KnowledgeError, KnowledgeStore
from orchestrator.models import ItemStatus
from tests.base import TempCase


class Kennisbasis(TempCase):
    def setUp(self):
        super().setUp()
        self.store = KnowledgeStore(self.tmp / "kennis")
        self.store.scaffold("demo")

    def test_menselijk_antwoord_levert_bevestigd_item(self):
        item_id = self.store.append_decision(
            "Btw op de teller", "Bedragen zijn inclusief btw.",
            source="antwoord op issue #12", confirmed_by_human=True,
        )
        item = self.store.get(item_id)
        self.assertEqual(item.status, ItemStatus.CONFIRMED)
        self.assertTrue(item.citable)

    def test_model_kan_niets_tot_waarheid_verheffen(self):
        item_id = self.store.append_decision(
            "Marge", "30 procent.", source="reviewer", confirmed_by_human=False
        )
        self.assertEqual(self.store.get(item_id).status, ItemStatus.TO_CONFIRM)
        self.assertFalse(self.store.get(item_id).citable)

    def test_bevestigde_beslissing_vereist_bron(self):
        with self.assertRaises(KnowledgeError):
            self.store.append_decision("X", "Y", source="  ", confirmed_by_human=True)

    def test_ids_lopen_op(self):
        first = self.store.append_decision("a", "b", source="s", confirmed_by_human=True)
        second = self.store.append_decision("c", "d", source="s", confirmed_by_human=True)
        self.assertEqual((first, second), ("D-001", "D-002"))

    def test_statussen_uit_het_bestand_worden_gelezen(self):
        (self.tmp / "kennis" / "businessregels.md").write_text(
            "# regels\n\n"
            "## R-001 · Verzendkosten\nstatus: tegenstrijdig\n\nOfwel 4,95 ofwel gratis.\n\n"
            "## R-002 · Munt\nstatus: bevestigd\nbron: intake\n\nAlles in euro.\n",
            encoding="utf-8",
        )
        self.store.load()
        self.assertEqual(self.store.get("R-001").status, ItemStatus.CONFLICTING)
        self.assertFalse(self.store.get("R-001").citable)
        self.assertTrue(self.store.get("R-002").citable)

    def test_onbekende_status_wordt_niet_vertrouwd(self):
        (self.tmp / "kennis" / "open.md").write_text(
            "## X-1 · iets\nstatus: misschien\n\ntekst\n", encoding="utf-8"
        )
        self.store.load()
        self.assertEqual(self.store.get("X-1").status, ItemStatus.TO_CONFIRM)
