"""Het opstartrapport moet liegen onmogelijk maken.

De aanleiding: Railway zei "Active" en de log zweeg. Elke controle hieronder
test daarom niet of er iets gelogd wordt, maar of de uitkomst klopt met de
werkelijkheid - ook als die werkelijkheid slecht nieuws is.
"""

import os
import subprocess
import unittest

from tests.base import TempCase

from orchestrator.opstart import (MARKER, Controle, Rapport, controleer_claude,
                                  controleer_datamap, controleer_doctor,
                                  controleer_github, controleer_openai,
                                  format_rapport, hartslagregel)


class Datamap(TempCase):
    def test_eerste_start_meldt_dat_er_nog_geen_merkteken_is(self):
        """Bij de eerste start kunnen we persistentie nog niet bewijzen. Dat
        zeggen we dan ook, in plaats van 'OK' te suggereren."""
        c = controleer_datamap(self.tmp / "verse")
        self.assertTrue(c.ok)
        self.assertIn("nog geen merkteken", c.detail)

    def test_tweede_start_bewijst_dat_het_volume_bewaart(self):
        pad = self.tmp / "volume"
        controleer_datamap(pad)
        c = controleer_datamap(pad)
        self.assertTrue(c.ok)
        self.assertIn("blijft behouden", c.detail)
        self.assertTrue((pad / MARKER).exists())

    def test_onbeschrijfbare_map_is_fout(self):
        """Een leesbare maar onbeschrijfbare map is precies het geval waarin
        de dienst opkomt en pas bij de eerste taak omvalt."""
        if os.geteuid() == 0:
            self.skipTest("root mag overal schrijven; rechten zeggen hier niets")
        pad = self.tmp / "readonly"
        pad.mkdir()
        pad.chmod(0o500)
        self.addCleanup(pad.chmod, 0o700)
        c = controleer_datamap(pad)
        self.assertFalse(c.ok)
        self.assertIn("niet beschrijfbaar", c.detail)

    def test_datamap_die_een_bestand_blijkt_is_fout(self):
        """Een verkeerd gezet volume kan het pad als bestand achterlaten. Dat
        moet FOUT opleveren, niet een uitzondering die de start stilletjes velt."""
        pad = self.tmp / "geen-map"
        pad.write_text("ik ben een bestand")
        c = controleer_datamap(pad)
        self.assertFalse(c.ok)
        self.assertIn("kan niet worden aangemaakt", c.detail)


class GitHub(unittest.TestCase):
    def test_geslaagd_toont_de_login_niet_de_token(self):
        class Client:
            def whoami(self):
                return "PadeLMQ"

        c = controleer_github(Client, ["PadeLMQ/padelmq-teller"])
        self.assertTrue(c.ok)
        self.assertIn("PadeLMQ", c.detail)
        self.assertIn("padelmq-teller", c.detail)

    def test_fout_wordt_geredigeerd(self):
        """Een 401 van GitHub kan de aangeboden token in de foutmelding
        herhalen. Die mag niet in de log belanden.

        De nep-token wordt hier opgebouwd in plaats van uitgeschreven: de
        geheimenscanner van deze repository kijkt naar vorm, niet naar bedoeling,
        en die scanner willen we streng houden.
        """
        nep = "gh" + "p_" + "abcdefghijklmnopqrstuvwxyz0123"

        def kapot():
            raise RuntimeError(f"Bearer {nep} werd geweigerd")

        c = controleer_github(kapot)
        self.assertFalse(c.ok)
        self.assertNotIn(nep, c.detail)
        self.assertIn("geredigeerd", c.detail)


class Overige(unittest.TestCase):
    def test_openai_neemt_de_uitkomst_van_de_echte_authcontrole_over(self):
        self.assertFalse(controleer_openai(lambda: (False, "401")).ok)
        self.assertTrue(controleer_openai(lambda: (True, "OK")).ok)

    def test_claude_ontbreekt_in_path(self):
        c = controleer_claude(which=lambda naam: None)
        self.assertFalse(c.ok)

    def test_claude_staat_in_path_maar_valt_om(self):
        """'in PATH' is geen bewijs: een halve npm-installatie haalt die test."""
        def run(*a, **kw):
            return subprocess.CompletedProcess(a, 1, "", "cannot find module")

        c = controleer_claude(run=run, which=lambda naam: "/usr/bin/claude")
        self.assertFalse(c.ok)
        self.assertIn("exitcode 1", c.detail)

    def test_claude_werkt(self):
        def run(*a, **kw):
            return subprocess.CompletedProcess(a, 0, "2.0.1 (Claude Code)", "")

        c = controleer_claude(run=run, which=lambda naam: "/usr/bin/claude")
        self.assertTrue(c.ok)
        self.assertIn("2.0.1", c.detail)

    def test_doctor_die_faalt_is_fout_en_een_crash_ook(self):
        self.assertTrue(controleer_doctor(lambda: 0).ok)
        self.assertFalse(controleer_doctor(lambda: 1).ok)

        def knalt():
            raise ValueError("stuk")

        c = controleer_doctor(knalt)
        self.assertFalse(c.ok)
        self.assertIn("ValueError", c.detail)


class Opmaak(unittest.TestCase):
    def _rapport(self, *controles):
        r = Rapport()
        r.controles.extend(controles)
        return r

    def test_alles_goed_geeft_een_ondubbelzinnige_slotregel(self):
        r = self._rapport(Controle("datamap", True, "prima"))
        tekst = format_rapport(r, versie="1.0")
        self.assertIn("[OK  ] datamap", tekst)
        self.assertIn("alle noodzakelijke controles geslaagd", tekst)

    def test_falende_controle_noemt_zichzelf_in_de_slotregel(self):
        """Wie de log leest moet in één regel weten wat er stuk is."""
        r = self._rapport(Controle("datamap", True, "prima"),
                          Controle("github-auth", False, "401"))
        tekst = format_rapport(r, versie="1.0")
        self.assertIn("[FOUT] github-auth", tekst)
        self.assertIn("geblokkeerd door: github-auth", tekst)
        self.assertFalse(r.ok)

    def test_niet_fatale_controle_blokkeert_de_start_niet(self):
        r = self._rapport(Controle("email", False, "geen smtp", fataal=False))
        self.assertTrue(r.ok)
        self.assertIn("[FOUT] email", format_rapport(r, versie="1.0"))


class Hartslag(unittest.TestCase):
    class Ronde:
        hersteld = antwoorden = taken = fouten = 0
        stil = True

    def test_stille_ronde_geeft_toch_een_regel(self):
        """Zonder deze regel is 'niets te doen' niet te onderscheiden van 'dood'."""
        regel = hartslagregel(7, self.Ronde(), tijd="2026-09-05T10:00:00+00:00",
                              interval=120)
        self.assertIn("[HART] ronde 7", regel)
        self.assertIn("stil", regel)
        self.assertIn("volgende over 120s", regel)

    def test_ronde_met_werk_zegt_dat_ook(self):
        ronde = self.Ronde()
        ronde.taken = 2
        ronde.stil = False
        regel = hartslagregel(1, ronde, tijd="t", interval=60)
        self.assertIn("werk gedaan", regel)
        self.assertIn("taken=2", regel)


class Commando(TempCase):
    def test_startup_bestaat_als_subcommando(self):
        """Staat het niet in de parser, dan faalt start.sh pas op Railway."""
        from orchestrator.cli import build_parser

        args = build_parser().parse_args(["startup", "--zonder-doctor"])
        self.assertTrue(args.zonder_doctor)
        self.assertEqual(args.func.__name__, "cmd_startup")


if __name__ == "__main__":
    unittest.main()
