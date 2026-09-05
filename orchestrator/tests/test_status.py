"""Levensteken en status: bewijzen dat de dienst werkelijk draait."""

import unittest

from orchestrator.serve import Serve

try:
    from tests.base import TempCase
except ImportError:  # pragma: no cover
    from base import TempCase


class Levensteken(TempCase):
    def test_zonder_ronde_is_er_geen_levensteken(self):
        self.assertIsNone(self.db.laatste_heartbeat())

    def test_een_ronde_schrijft_een_levensteken(self):
        self.db.heartbeat(gestart_op="2026-09-05T10:00:00+00:00", rondes=1,
                          werk="1 taak", pid=42, host="vps")
        r = self.db.laatste_heartbeat()
        self.assertEqual(r["rondes"], 1)
        self.assertEqual(r["pid"], 42)
        self.assertEqual(r["host"], "vps")
        self.assertTrue(r["laatste_ronde"])

    def test_een_herstart_zet_de_starttijd_bij(self):
        """Anders liegt de status over hoe lang de dienst al draait."""
        self.db.heartbeat(gestart_op="2026-09-05T10:00:00+00:00", rondes=5, pid=1)
        self.db.heartbeat(gestart_op="2026-09-05T12:00:00+00:00", rondes=1, pid=2)
        r = self.db.laatste_heartbeat()
        self.assertEqual(r["gestart_op"], "2026-09-05T12:00:00+00:00")
        self.assertEqual(r["rondes"], 1, "de rondeteller is niet meegeherstart")
        self.assertEqual(r["pid"], 2)

    def test_het_laatste_werk_blijft_staan_bij_een_stille_ronde(self):
        """Anders lijkt een rustige dienst op een dienst die nooit iets deed."""
        self.db.heartbeat(gestart_op="x", rondes=1, werk="1 taak afgerond")
        self.db.heartbeat(gestart_op="x", rondes=2, werk=None)
        self.assertEqual(self.db.laatste_heartbeat()["laatste_werk"], "1 taak afgerond")

    def test_een_fout_verdwijnt_na_een_goede_ronde(self):
        self.db.heartbeat(gestart_op="x", rondes=1, fout="netwerk weg")
        self.assertEqual(self.db.laatste_heartbeat()["laatste_fout"], "netwerk weg")
        self.db.heartbeat(gestart_op="x", rondes=2, fout=None)
        self.assertIsNone(self.db.laatste_heartbeat()["laatste_fout"])


class KlopOokBijStilte(unittest.TestCase):
    def test_ook_een_stille_ronde_klopt(self):
        """Juist bij stilte moet er een teken zijn: anders lijkt rust op dood."""
        kloppen = []
        lus = Serve(recover_fn=lambda: 0, poll_fn=lambda: 0, work_fn=lambda: 0,
                    sleep_fn=lambda s: None, na_ronde=kloppen.append)
        lus.run(rondes=3)
        self.assertEqual(len(kloppen), 3)
        self.assertTrue(all(r.stil for r in kloppen))

    def test_een_kapot_levensteken_stopt_de_lus_niet(self):
        def stuk(ronde):
            raise RuntimeError("schijf vol")

        gemeld = []
        lus = Serve(recover_fn=lambda: 0, poll_fn=lambda: 0, work_fn=lambda: 1,
                    sleep_fn=lambda s: None, na_ronde=stuk, on_event=gemeld.append)
        r = lus.ronde()
        self.assertEqual(r.taken, 1, "het werk is verloren gegaan door het levensteken")
        self.assertTrue(any("levensteken" in m for m in gemeld))


if __name__ == "__main__":
    unittest.main()
