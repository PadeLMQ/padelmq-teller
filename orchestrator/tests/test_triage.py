"""De kern van 'nooit gokken': wanneer mag een antwoord automatisch gebruikt worden."""

from orchestrator.knowledge import KnowledgeStore
from orchestrator.models import Citation, Question, Triage
from orchestrator.triage import TriageContext, TriageEngine
from tests.base import TempCase


class Triageregels(TempCase):
    def setUp(self):
        super().setUp()
        self.repo = self.make_repo()
        self.store = KnowledgeStore(self.tmp / "kennis")
        self.store.scaffold("demo")
        self.confirmed = self.store.append_decision(
            "Munteenheid", "Alle bedragen in euro.",
            source="intake", confirmed_by_human=True,
        )
        self.unconfirmed = self.store.append_decision(
            "Knoptekst", "Gebruik 'Bewaren'.", source="model", confirmed_by_human=False
        )
        self.store.load()

    def engine(self, independent: bool = True, verification=None) -> TriageEngine:
        return TriageEngine(
            TriageContext(
                knowledge=self.store,
                repo_root=self.repo,
                verification=verification,
                has_independent_work=independent,
            )
        )

    # -- AUTO -------------------------------------------------------------
    def test_auto_met_bevestigde_bron(self):
        question = Question(
            text="Welke munteenheid gebruiken we in de weergave?",
            proposed_answer="Euro.",
            citations=[Citation(f"kb:{self.confirmed}")],
        )
        result = self.engine().decide(question)
        self.assertEqual(result.outcome, Triage.AUTO)
        self.assertEqual(result.answer, "Euro.")

    def test_auto_met_bestandsverwijzing(self):
        question = Question(
            text="Hoe heet de bestaande functie in de module?",
            proposed_answer="total()",
            citations=[Citation("repo:app.py:1")],
        )
        self.assertEqual(self.engine().decide(question).outcome, Triage.AUTO)

    # -- PARK -------------------------------------------------------------
    def test_niet_bevestigde_bron_gaat_naar_park(self):
        question = Question(
            text="Welke tekst komt op de knop?",
            proposed_answer="Bewaren",
            citations=[Citation(f"kb:{self.unconfirmed}")],
        )
        result = self.engine().decide(question)
        self.assertEqual(result.outcome, Triage.PARK)
        self.assertIn("te bevestigen", result.reason)

    def test_antwoord_zonder_bron_gaat_naar_park(self):
        question = Question(text="Welke tekst komt op de knop?", proposed_answer="Bewaren")
        result = self.engine().decide(question)
        self.assertEqual(result.outcome, Triage.PARK)
        self.assertIn("zonder bronverwijzing", result.reason)

    def test_verzonnen_bron_gaat_naar_park(self):
        question = Question(
            text="Welke tekst komt op de knop?",
            proposed_answer="Bewaren",
            citations=[Citation("kb:D-999")],
        )
        self.assertEqual(self.engine().decide(question).outcome, Triage.PARK)

    def test_bestand_buiten_de_projectmap_telt_niet(self):
        question = Question(
            text="Wat staat er in het systeembestand?",
            proposed_answer="iets",
            citations=[Citation("repo:../../etc/passwd:1")],
        )
        self.assertEqual(self.engine().decide(question).outcome, Triage.PARK)

    def test_een_kloppende_en_een_kapotte_bron_gaat_naar_park(self):
        """Twijfel tussen AUTO en PARK gaat naar PARK."""
        question = Question(
            text="Welke munteenheid?",
            proposed_answer="Euro.",
            citations=[Citation(f"kb:{self.confirmed}"), Citation("kb:D-999")],
        )
        self.assertEqual(self.engine().decide(question).outcome, Triage.PARK)

    # -- verboden categorieen ---------------------------------------------
    def test_btw_wordt_nooit_automatisch_beantwoord(self):
        question = Question(
            text="Tonen we de btw inclusief of exclusief?",
            proposed_answer="Inclusief.",
            citations=[Citation(f"kb:{self.confirmed}")],
            category="btw",
        )
        result = self.engine().decide(question)
        self.assertEqual(result.outcome, Triage.PARK)
        self.assertIn("nooit automatisch", result.reason)

    def test_verboden_categorie_ook_zonder_label(self):
        question = Question(
            text="Welke prijs rekenen we voor verzending?",
            proposed_answer="4,95",
            citations=[Citation(f"kb:{self.confirmed}")],
        )
        self.assertNotEqual(self.engine().decide(question).outcome, Triage.AUTO)

    def test_verbodenlijst_van_het_project_telt_mee(self):
        (self.tmp / "kennis" / "verboden.md").write_text(
            "## V-001 · Retourtermijn\nstatus: bevestigd\nbron: intake\n\n"
            "Nooit zelf een retourtermijn bepalen.\n",
            encoding="utf-8",
        )
        self.store.load()
        question = Question(
            text="Welke retourtermijn hanteren we? Bepalen we die zelf?",
            proposed_answer="14 dagen",
            citations=[Citation(f"kb:{self.confirmed}")],
        )
        self.assertNotEqual(self.engine().decide(question).outcome, Triage.AUTO)

    # -- BLOCK ------------------------------------------------------------
    def test_zonder_ander_werk_wordt_het_block(self):
        question = Question(text="Welke tekst komt op de knop?", proposed_answer="Bewaren")
        result = self.engine(independent=False).decide(question)
        self.assertEqual(result.outcome, Triage.BLOCK)
        self.assertIn("geen onafhankelijk werk", result.reason)

    def test_met_ander_werk_wordt_het_park(self):
        question = Question(text="Welke tekst komt op de knop?", proposed_answer="Bewaren")
        self.assertEqual(self.engine(independent=True).decide(question).outcome, Triage.PARK)

    def test_leeg_antwoord_is_geen_auto(self):
        question = Question(
            text="Welke munteenheid?", proposed_answer="",
            citations=[Citation(f"kb:{self.confirmed}")],
        )
        self.assertEqual(self.engine().decide(question).outcome, Triage.PARK)
