"""Cachetokens mogen niet tegen het gewone invoertarief meegerekend worden.

De Responses-API rapporteert input_tokens als totaal en cached_tokens als een
onderdeel daarvan. Wie ze allebei vol aanrekent, betaalt de cache dubbel.
"""

import unittest

from orchestrator.adapters.reviewer import _cached_tokens
from orchestrator.config import ModelPrice
from orchestrator.cost import Estimate, InconsistentUsage

# tarieven zoals opgegeven door de provider, in USD per miljoen tokens
TARIEF = ModelPrice(input_per_mtok=2.00, output_per_mtok=12.00, cached_input_per_mtok=0.20)


class CachedInputKosten(unittest.TestCase):
    def test_cachedeel_gaat_tegen_cachetarief(self):
        # 10_000 invoer waarvan 8_000 uit de cache, 1_000 uitvoer
        est = Estimate(model="m", tokens_in=10_000, tokens_out=1_000, cached_in=8_000)
        verwacht = (2_000 / 1e6 * 2.00) + (8_000 / 1e6 * 0.20) + (1_000 / 1e6 * 12.00)
        self.assertAlmostEqual(est.cost(TARIEF), verwacht, places=10)

    def test_niet_dubbel_geteld(self):
        """De oude fout: alle invoer vol + cache er nog eens bovenop."""
        est = Estimate(model="m", tokens_in=10_000, tokens_out=0, cached_in=8_000)
        fout = (10_000 / 1e6 * 2.00) + (8_000 / 1e6 * 0.20)
        self.assertLess(est.cost(TARIEF), fout)

    def test_cache_is_goedkoper_dan_geen_cache(self):
        zonder = Estimate(model="m", tokens_in=10_000, tokens_out=0, cached_in=0)
        met = Estimate(model="m", tokens_in=10_000, tokens_out=0, cached_in=10_000)
        self.assertAlmostEqual(zonder.cost(TARIEF), 10_000 / 1e6 * 2.00, places=10)
        self.assertAlmostEqual(met.cost(TARIEF), 10_000 / 1e6 * 0.20, places=10)
        self.assertLess(met.cost(TARIEF), zonder.cost(TARIEF))

    def test_zonder_cache_ongewijzigd(self):
        """Een aanroep zonder cachehits kost precies wat hij altijd kostte."""
        est = Estimate(model="m", tokens_in=1_234, tokens_out=567)
        verwacht = (1_234 / 1e6 * 2.00) + (567 / 1e6 * 12.00)
        self.assertAlmostEqual(est.cost(TARIEF), verwacht, places=10)

    def test_tegenstrijdige_telling_stopt(self):
        """Meer cache dan invoer spreekt het datamodel tegen: stoppen, niet gokken."""
        est = Estimate(model="m", tokens_in=100, tokens_out=0, cached_in=101)
        with self.assertRaises(InconsistentUsage):
            est.cost(TARIEF)


class CachedTokensUitlezen(unittest.TestCase):
    class _Details:
        def __init__(self, cached):
            self.cached_tokens = cached

    class _Usage:
        def __init__(self, details):
            self.input_tokens = 10_000
            self.output_tokens = 100
            if details is not None:
                self.input_tokens_details = details

    def test_leest_cached_tokens(self):
        usage = self._Usage(self._Details(8_000))
        self.assertEqual(_cached_tokens(usage), 8_000)

    def test_ontbrekend_subobject_is_nul(self):
        self.assertEqual(_cached_tokens(self._Usage(None)), 0)

    def test_geen_usage_is_nul(self):
        self.assertEqual(_cached_tokens(None), 0)

    def test_none_waarde_is_nul(self):
        self.assertEqual(_cached_tokens(self._Usage(self._Details(None))), 0)


if __name__ == "__main__":
    unittest.main()


class CachetariefUitOmgeving(unittest.TestCase):
    """ORCH_REVIEWER_PRICE_CACHED_IN moet echt doorwerken in de prijstabel."""

    def _laad(self, **extra):
        import os
        from unittest import mock
        from orchestrator.config import Settings

        omgeving = {
            "ORCH_REVIEWER_MODEL": "gpt-5.6-terra",
            "ORCH_REVIEWER_PRICE_IN": "2.00",
            "ORCH_REVIEWER_PRICE_OUT": "12.00",
        }
        omgeving.update(extra)
        with mock.patch.dict(os.environ, omgeving, clear=False):
            for weg in ("ORCH_REVIEWER_PRICE_CACHED_IN",):
                if weg not in omgeving:
                    os.environ.pop(weg, None)
            return Settings.from_env().prices["gpt-5.6-terra"]

    def test_cachetarief_wordt_gelezen(self):
        prijs = self._laad(ORCH_REVIEWER_PRICE_CACHED_IN="0.20")
        self.assertEqual(prijs.cached_input_per_mtok, 0.20)

    def test_zonder_cachetarief_valt_terug_op_invoertarief(self):
        """Niet op 0.00: te weinig boeken verbergt kosten."""
        prijs = self._laad()
        self.assertEqual(prijs.cached_input_per_mtok, 2.00)
