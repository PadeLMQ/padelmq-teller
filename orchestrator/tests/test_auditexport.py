"""De audittrail moet ook buiten de database bestaan.

Aanleiding: de volledige pilot -- vijf taken, elf beslissingen van de eigenaar,
27 betaalde aanroepen -- stond in één sqlite-bestand op één machine. Een
sqlite-bestand is geen archief: het is onleesbaar zonder de orkestrator en het
verdwijnt met de machine.

Wat hier vastligt is vooral dat de export niets weglaat en niets verzint.
"""

import unittest

from tests.base import TempCase

from orchestrator.auditexport import bouw


class Export(TempCase):
    def setUp(self) -> None:
        super().setUp()
        self.db.ensure_project("pilot")
        self.scope = self.db.scope("pilot")

    def test_lege_audittrail_zegt_dat_er_niets_is(self):
        """Niets is een geldige uitkomst; hem opvullen zou liegen zijn."""
        tekst = bouw(self.scope, "pilot")
        self.assertIn("Geen taken vastgelegd", tekst)
        self.assertIn("Geen vragen vastgelegd", tekst)
        self.assertIn("Geen afwijkingen vastgelegd", tekst)

    def test_taken_komen_erin(self):
        self.scope.add_task("Een taak", spec="doe iets nuttigs")
        tekst = bouw(self.scope, "pilot")
        self.assertIn("Een taak", tekst)
        self.assertIn("doe iets nuttigs", tekst)

    def test_beantwoorde_vraag_komt_met_antwoord_mee(self):
        """Een beantwoorde vraag is juist het waardevolste: het is de
        beslissing van de eigenaar, en die mag nooit verloren gaan."""
        qid = self.scope.add_question("Mag lint hard zijn?", "block", "vv-1",
                                      why_blocking="niet zelf te verzinnen")
        self.scope.set_question(qid, status="answered", answer="Ja, vanaf D-005",
                                issue_number=19)
        tekst = bouw(self.scope, "pilot")
        self.assertIn("Mag lint hard zijn?", tekst)
        self.assertIn("Ja, vanaf D-005", tekst)
        self.assertIn("GitHub-issue #19", tekst)
        self.assertIn("niet zelf te verzinnen", tekst)

    def test_onbeantwoorde_vraag_wordt_niet_ingevuld(self):
        self.scope.add_question("Open vraag?", "block", "vv-2")
        tekst = bouw(self.scope, "pilot")
        self.assertIn("geen antwoord vastgelegd", tekst)

    def test_kosten_worden_opgeteld_en_per_aanroep_getoond(self):
        self.scope.record_call(phase="implement", role="uitvoerder", model="m",
                               tokens_in=100, tokens_out=10, cached_in=40,
                               cost_eur=0.25)
        self.scope.record_call(phase="review", role="beoordelaar", model="r",
                               tokens_in=50, tokens_out=5, cached_in=0,
                               cost_eur=0.125)
        tekst = bouw(self.scope, "pilot")
        self.assertIn("2 betaalde aanroep(en), samen **$0.375000**", tekst)
        self.assertIn("150 invoertokens, waarvan 40 uit cache", tekst)
        self.assertIn("uitvoerder", tekst)

    def test_verspilde_aanroep_blijft_zichtbaar(self):
        """Verspilling verbergen zou de duurste les uit de pilot wegpoetsen."""
        self.scope.record_call(phase="implement", role="uitvoerder", model="m",
                               tokens_in=1, tokens_out=1, cached_in=0, cost_eur=1.9)
        self.scope.conn.execute(
            "UPDATE calls SET wasted_reason = ? WHERE project_id = ?",
            ("achterhaald na de budgetstop", self.scope.project_id))
        self.assertIn("achterhaald na de budgetstop", bouw(self.scope, "pilot"))

    def test_afwijkingen_krijgen_een_eigen_sectie(self):
        self.scope.log("budget-uitzondering", {"reden": "eenmalige meting"})
        self.scope.log("beoordeling", {"iets": "gewoons"})
        tekst = bouw(self.scope, "pilot")
        afwijkingen = tekst[tekst.index("## Afwijkingen"):tekst.index("## Volledig")]
        self.assertIn("eenmalige meting", afwijkingen)
        self.assertNotIn("gewoons", afwijkingen,
                         "een gewone gebeurtenis is geen afwijking")

    def test_alle_gebeurtenissen_blijven_in_het_logboek(self):
        for n in range(120):
            self.scope.log("iets", {"n": n})
        tekst = bouw(self.scope, "pilot")
        self.assertIn("120 gebeurtenissen", tekst,
                      "de export mag niet stilletjes bij 50 ophouden")


if __name__ == "__main__":
    unittest.main()
