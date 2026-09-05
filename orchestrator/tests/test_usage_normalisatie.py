"""Aanbieders tellen invoertokens verschillend. Usage kent één contract.

OpenAI: input_tokens is het totaal, cached_tokens is daar een deel van.
Claude-CLI: input_tokens sluit de cachetokens juist uit en zet cache_read en
cache_creation er los naast.

Wie die twee door elkaar haalt, krijgt meer cache dan invoer en boekt onzin.
Dat gebeurde echt in de eerste B7-run: 586218 cachetokens op 28 invoertokens.
"""

import unittest

from orchestrator.adapters.claude import _usage_from_cli
from orchestrator.config import ModelPrice
from orchestrator.cost import Estimate

try:
    from tests.base import TempCase
except ImportError:  # pragma: no cover
    from base import TempCase

TARIEF = ModelPrice(input_per_mtok=5.0, output_per_mtok=25.0, cached_input_per_mtok=0.5)


class ClaudeTelling(unittest.TestCase):
    # De werkelijke cijfers uit de mislukte run.
    ECHTE_USAGE = {
        "input_tokens": 28,
        "cache_read_input_tokens": 586218,
        "cache_creation_input_tokens": 7828,
        "output_tokens": 412,
    }

    def test_tokens_in_is_het_totaal(self):
        u = _usage_from_cli("claude-opus-5", self.ECHTE_USAGE, {})
        self.assertEqual(u.tokens_in, 28 + 586218 + 7828)

    def test_alleen_gelezen_cache_telt_als_cached(self):
        """Een cacheschrijfactie is geen goedkope leesactie."""
        u = _usage_from_cli("claude-opus-5", self.ECHTE_USAGE, {})
        self.assertEqual(u.cached_in, 586218)

    def test_de_echte_run_boekt_nu_zonder_fout(self):
        """Regressie: dit wierp InconsistentUsage en liet de run crashen."""
        u = _usage_from_cli("claude-opus-5", self.ECHTE_USAGE, {})
        est = Estimate(model=u.model, tokens_in=u.tokens_in,
                       tokens_out=u.tokens_out, cached_in=u.cached_in)
        self.assertEqual(est.uncached_in, 28 + 7828)
        self.assertGreater(est.cost(TARIEF), 0)

    def test_zonder_cache_blijft_de_telling_gelijk(self):
        u = _usage_from_cli("m", {"input_tokens": 100, "output_tokens": 20}, {})
        self.assertEqual((u.tokens_in, u.cached_in, u.tokens_out), (100, 0, 20))


class GerapporteerdeKost(unittest.TestCase):
    def test_kost_van_de_aanbieder_gaat_voor(self):
        """De CLI rekent zelf af; onze prijstabel is maar een benadering."""
        u = _usage_from_cli("claude-opus-5", ClaudeTelling.ECHTE_USAGE,
                            {"total_cost_usd": 0.0389604})
        self.assertAlmostEqual(u.cost_usd, 0.0389604)
        est = Estimate(model=u.model, tokens_in=u.tokens_in, tokens_out=u.tokens_out,
                       cached_in=u.cached_in, reported_cost=u.cost_usd)
        self.assertAlmostEqual(est.cost(TARIEF), 0.0389604)

    def test_zonder_gerapporteerde_kost_rekenen_we_zelf(self):
        u = _usage_from_cli("m", {"input_tokens": 1_000_000, "output_tokens": 0}, {})
        self.assertIsNone(u.cost_usd)
        est = Estimate(model="m", tokens_in=u.tokens_in, tokens_out=0,
                       reported_cost=u.cost_usd)
        self.assertAlmostEqual(est.cost(TARIEF), 5.0)

    def test_gerapporteerde_nul_is_geen_ontbrekende_waarde(self):
        """0.0 is een bedrag, geen 'onbekend'. Anders schat het systeem er alsnog op los."""
        u = _usage_from_cli("m", {"input_tokens": 1_000_000}, {"total_cost_usd": 0.0})
        self.assertEqual(u.cost_usd, 0.0)
        est = Estimate(model="m", tokens_in=u.tokens_in, tokens_out=0,
                       reported_cost=u.cost_usd)
        self.assertEqual(est.cost(TARIEF), 0.0)


if __name__ == "__main__":
    unittest.main()


class RunKosten(TempCase):
    """Een run die $0 meldt terwijl er aanroepen in zitten, verbergt kosten."""

    def test_end_run_telt_de_aanroepen_op(self):
        from orchestrator import projects as projects_mod

        projects_mod.add(self.settings, "p", str(self.make_repo("rk")))
        scope = self.db.scope("p")
        task_id = scope.add_task("t", "spec", ["a"])
        run_id = scope.start_run(task_id, "task")
        for bedrag in (0.25, 0.10):
            scope.record_call(phase="implement", role="uitvoerder", model="reviewer-test",
                              tokens_in=1, tokens_out=1, cached_in=0,
                              cost_eur=bedrag, task_id=task_id, run_id=run_id,
                              day="2026-09-05")
        scope.end_run(run_id, "done")
        rij = self.db.conn.execute(
            "SELECT cost_eur FROM runs WHERE id = ?", (run_id,)).fetchone()
        self.assertAlmostEqual(rij[0], 0.35)

    def test_expliciet_bedrag_gaat_voor(self):
        from orchestrator import projects as projects_mod

        projects_mod.add(self.settings, "q", str(self.make_repo("rk2")))
        scope = self.db.scope("q")
        run_id = scope.start_run(scope.add_task("t", "s", ["a"]), "task")
        scope.end_run(run_id, "done", cost_eur=1.5)
        rij = self.db.conn.execute(
            "SELECT cost_eur FROM runs WHERE id = ?", (run_id,)).fetchone()
        self.assertAlmostEqual(rij[0], 1.5)
