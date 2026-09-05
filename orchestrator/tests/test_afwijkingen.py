"""Afwijken van het draaiboek mag, stilzwijgend afwijken niet."""

import json
import unittest

from orchestrator import projects as projects_mod
from orchestrator.deviations import (
    Deviation,
    DeviationOutcome,
    OnvolledigeAfwijking,
    classify,
    format_deviation,
    record,
)

try:  # werkt zowel via 'discover -s tests' als via 'unittest tests.<naam>'
    from tests.base import TempCase
except ImportError:  # pragma: no cover - hangt af van de aanroepvorm
    from base import TempCase


def _afwijking(**overschrijf) -> Deviation:
    velden = {
        "voorgeschreven": "verify-reviewer --model, drie woorden en een booleaans schema",
        "uitgevoerd": "het echte answer()-pad met een volledige vraag",
        "reden": "valideert ook het schema en de bronplicht, niet alleen de verbinding",
        "risico": "geen; strengere controle langs dezelfde weg",
        "kosten": "436 tokens meer, ongeveer 0,003 USD",
    }
    velden.update(overschrijf)
    return Deviation(**velden)


class Verantwoording(unittest.TestCase):
    def test_alle_vijf_velden_verplicht(self):
        for veld in ("voorgeschreven", "uitgevoerd", "reden", "risico", "kosten"):
            with self.subTest(veld=veld):
                with self.assertRaises(OnvolledigeAfwijking):
                    _afwijking(**{veld: ""})

    def test_spaties_tellen_niet_als_verantwoording(self):
        with self.assertRaises(OnvolledigeAfwijking):
            _afwijking(reden="   ")

    def test_de_melding_noemt_het_ontbrekende_veld(self):
        with self.assertRaises(OnvolledigeAfwijking) as ctx:
            _afwijking(risico="", kosten="")
        self.assertIn("risico", str(ctx.exception))
        self.assertIn("kosten", str(ctx.exception))


class Indeling(unittest.TestCase):
    def test_zuiver_technische_afwijking_gaat_door(self):
        uitkomst, _ = classify(_afwijking())
        self.assertIs(uitkomst, DeviationOutcome.TECHNISCH)

    def test_productie_blokkeert(self):
        uitkomst, reden = classify(_afwijking(reden="sneller naar productie"))
        self.assertIs(uitkomst, DeviationOutcome.BLOKKEREND)
        self.assertIn("productie", reden)

    def test_geld_blokkeert(self):
        self.assertIs(
            classify(_afwijking(uitgevoerd="prijs handmatig aangepast"))[0],
            DeviationOutcome.BLOKKEREND,
        )

    def test_onomkeerbaar_blokkeert(self):
        self.assertIs(
            classify(_afwijking(risico="onomkeerbaar"))[0], DeviationOutcome.BLOKKEREND
        )

    def test_veiligheidsgrens_blokkeert(self):
        self.assertIs(
            classify(_afwijking(uitgevoerd="controle op de sleutel overgeslagen"))[0],
            DeviationOutcome.BLOKKEREND,
        )

    def test_verboden_categorie_blokkeert_ook_zonder_trefwoord(self):
        uitkomst, reden = classify(_afwijking(), category="btw")
        self.assertIs(uitkomst, DeviationOutcome.BLOKKEREND)
        self.assertIn("btw", reden)

    def test_json_schema_blokkeert_niet(self):
        """Regressie: 'schema' als losse term blokkeerde elke gewone afwijking.

        Een poort die bij iedere technische afwijking dichtslaat, wordt genegeerd
        en beschermt dan niets meer. Alleen een databaseschema telt.
        """
        self.assertIs(
            classify(_afwijking(uitgevoerd="een JSON-schema van een veld gebruikt"))[0],
            DeviationOutcome.TECHNISCH,
        )

    def test_databaseschema_blokkeert_wel(self):
        for tekst in ("databaseschema gewijzigd", "tabel-schema aangepast",
                      "schemawijziging doorgevoerd"):
            with self.subTest(tekst=tekst):
                self.assertIs(
                    classify(_afwijking(uitgevoerd=tekst))[0],
                    DeviationOutcome.BLOKKEREND,
                )

    def test_elk_veld_telt_mee_niet_alleen_de_stap(self):
        """Een onschuldige stap met een riskante reden blijft riskant."""
        self.assertIs(
            classify(_afwijking(kosten="verwaarloosbaar, ook na de deploy"))[0],
            DeviationOutcome.BLOKKEREND,
        )


class Audittrail(TempCase):
    def setUp(self):
        super().setUp()
        projects_mod.add(self.settings, "pilot", str(self.make_repo()))
        self.scope = self.db.scope("pilot")

    def _laatste(self):
        rijen = [r for r in self.scope.events(limit=10) if r["kind"] == "afwijking"]
        self.assertTrue(rijen, "afwijking staat niet in de audittrail")
        return rijen[0]

    def test_technische_afwijking_wordt_geregistreerd(self):
        uitkomst, _ = record(self.scope, _afwijking())
        self.assertIs(uitkomst, DeviationOutcome.TECHNISCH)
        payload = json.loads(self._laatste()["payload"])
        for veld in ("voorgeschreven", "uitgevoerd", "reden", "risico", "kosten"):
            self.assertTrue(payload.get(veld), f"{veld} ontbreekt in de audittrail")
        self.assertEqual(payload["uitkomst"], "technisch")

    def test_blokkerende_afwijking_wordt_ook_geregistreerd(self):
        """Juist bij een blokkade moet er iets naar te wijzen zijn."""
        uitkomst, _ = record(self.scope, _afwijking(reden="nodig voor de deploy"))
        self.assertIs(uitkomst, DeviationOutcome.BLOKKEREND)
        self.assertEqual(json.loads(self._laatste()["payload"])["uitkomst"], "blokkerend")

    def test_afwijking_blijft_binnen_het_project(self):
        projects_mod.add(self.settings, "ander", str(self.make_repo("r2")))
        record(self.scope, _afwijking())
        ander = self.db.scope("ander")
        self.assertEqual(
            [r for r in ander.events(limit=10) if r["kind"] == "afwijking"], []
        )

    def test_leesbare_weergave_noemt_alle_velden(self):
        record(self.scope, _afwijking())
        tekst = format_deviation(self._laatste())
        for etiket in ("voorgeschreven", "uitgevoerd", "reden",
                       "risico-impact", "kostenimpact"):
            self.assertIn(etiket, tekst)


if __name__ == "__main__":
    unittest.main()
