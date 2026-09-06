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


class PoortOpGewoneTaal(TempCase):
    """De verboden-poort ging op willekeur af.

    Drie echte vragen op issue #2 van padelmq-ai-product-engine werden
    geweigerd met "raakt een regel uit verboden.md". De woorden waarop dat
    gebeurde waren 'echte', 'komen', 'claude', 'database' en 'krijgen'. De
    enige vraag die werkelijk over Shopify ging kwam er ongemoeid doorheen.

    Een poort die zo werkt is geen poort: hij weigert onschuldige vragen en
    laat de gevaarlijke door.
    """

    def _motor(self, verboden_tekst: str):
        from orchestrator.knowledge import KnowledgeStore
        from orchestrator.triage import TriageContext, TriageEngine

        kennis = self.tmp / "kennis"
        KnowledgeStore(kennis).scaffold("p")
        (kennis / "verboden.md").write_text(
            "# p — verboden\n\n## VB-1 · Geen live acties\n"
            "status: bevestigd\ndatum: 2026-09-06\nbron: eigenaar\n\n"
            + verboden_tekst + "\n", encoding="utf-8")
        return TriageEngine(TriageContext(knowledge=KnowledgeStore(kennis),
                                          repo_root=self.tmp))

    def _vraag(self, tekst: str):
        from orchestrator.models import Question
        return Question(text=tekst)

    LANG = ("Zonder uitdrukkelijke toestemming van de eigenaar mag er niets echte "
            "gebeuren: geen live write, geen deploy naar productie. Wat er niet in "
            "staat mag niet komen. De documentatie in CLAUDE.md en de database "
            "blijven ongemoeid; niemand mag rechten krijgen die er niet zijn.")

    def test_gewone_taal_leidt_niet_meer_tot_een_weigering(self):
        motor = self._motor(self.LANG)
        for vraag in [
            "Moeten README.md:13 en DATABASE.md:303 dezelfde Node-verduidelijking "
            "krijgen als CLAUDE.md?",
            "Wat is de echte ondergrens voor de Node-versie, en moet die in "
            "package.json 'engines' komen?",
            "Zullen we de tekst in de footer aanpassen?",
        ]:
            with self.subTest(vraag=vraag[:40]):
                self.assertIsNone(motor.is_forbidden(self._vraag(vraag)),
                                  "geweigerd op gewone taal")

    def test_de_echt_gevaarlijke_vragen_worden_wel_gepakt(self):
        """Eén treffer is genoeg: dit zijn geen woorden die per ongeluk in een
        vraag over documentatie belanden."""
        motor = self._motor(self.LANG)
        for vraag in [
            "Moet CLAUDE.md gecorrigeerd worden waar het zegt dat er geen "
            "Shopify-integratie is?",
            "Mogen we het product publiceren naar de webshop?",
            "Moeten we de voorraad van dit racket bijwerken?",
            "Zullen we dit deployen naar productie?",
            "Mag deze branch gemerged worden?",
        ]:
            with self.subTest(vraag=vraag[:40]):
                self.assertIsNotNone(motor.is_forbidden(self._vraag(vraag)),
                                     "kwam er ongemoeid doorheen")

    def test_een_echte_overlap_blijft_weigeren_en_noemt_het_bewijs(self):
        """De regel zelf blijft werken; alleen gewone woorden tellen niet mee.
        En de melding moet zeggen waarop hij afging, anders is een onterechte
        weigering niet van een terechte te onderscheiden."""
        motor = self._motor("Nooit een fabrikantprijs of een leveranciersmarge "
                            "automatisch overnemen.")
        reden = motor.is_forbidden(
            self._vraag("Mag de fabrikantprijs uit de leveranciersmarge afgeleid worden?"))
        self.assertIsNotNone(reden)
        self.assertIn("op de woorden", reden)
