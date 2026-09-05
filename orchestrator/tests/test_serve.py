"""De doorlopende lus. Geen echte klok, geen echte aanroepen."""

import unittest

from orchestrator.serve import Serve


class Lus(unittest.TestCase):
    def _serve(self, **kw):
        self.geslapen = []
        standaard = dict(
            recover_fn=lambda: 0, poll_fn=lambda: 0, work_fn=lambda: 0,
            sleep_fn=self.geslapen.append, interval=60,
        )
        standaard.update(kw)
        return Serve(**standaard)

    def test_volgorde_herstel_antwoorden_werk(self):
        """Eerst opruimen, dan antwoorden binnenhalen, dan pas werken.

        Andersom zou een taak opgepakt worden voordat het antwoord dat haar
        deblokkeert binnen is.
        """
        volgorde = []
        lus = self._serve(
            recover_fn=lambda: volgorde.append("herstel") or 0,
            poll_fn=lambda: volgorde.append("antwoorden") or 0,
            work_fn=lambda: volgorde.append("werk") or 0,
        )
        lus.ronde()
        self.assertEqual(volgorde, ["herstel", "antwoorden", "werk"])

    def test_een_fout_stopt_de_lus_niet(self):
        def stuk():
            raise RuntimeError("netwerk weg")

        gemeld = []
        lus = self._serve(poll_fn=stuk, work_fn=lambda: 1,
                          on_event=gemeld.append)
        r = lus.ronde()
        self.assertEqual(r.fouten, 1)
        self.assertEqual(r.taken, 1, "het werk is overgeslagen door een fout elders")
        self.assertTrue(any("netwerk weg" in m for m in gemeld),
                        "de fout is stilgehouden")

    def test_na_werk_meteen_door(self):
        """Staat er werk, dan wachten we niet: er staat waarschijnlijk meer."""
        lus = self._serve(work_fn=lambda: 1)
        lus.run(rondes=3)
        self.assertEqual(self.geslapen, [], "er is gewacht terwijl er werk was")

    def test_bij_stilte_wachten(self):
        lus = self._serve(interval=42)
        lus.run(rondes=3)
        self.assertEqual(self.geslapen, [42, 42])

    def test_laatste_ronde_wacht_niet(self):
        lus = self._serve(interval=5)
        lus.run(rondes=1)
        self.assertEqual(self.geslapen, [])

    def test_stille_ronde_herkennen(self):
        self.assertTrue(self._serve().ronde().stil)
        self.assertFalse(self._serve(work_fn=lambda: 1).ronde().stil)


if __name__ == "__main__":
    unittest.main()
