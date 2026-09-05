"""Wanneer mag de bevestigingsronde overgeslagen worden?

Alleen als het antwoord zonder enige interpretatie precies één aangeboden optie
aanwijst. Alles daarbuiten wordt bevestigd. Er komt geen model aan te pas: dit
is een string die past of niet past.
"""

import json
import unittest

from orchestrator.answer_session import Act, AnswerFlow, exacte_optiekeuze

try:
    from tests.base import TempCase
except ImportError:  # pragma: no cover
    from base import TempCase

OPTIES = [
    "Strict (next/core-web-vitals)",
    "Base (next)",
]


class WelEenExacteKeuze(unittest.TestCase):
    def test_optienummer(self):
        self.assertEqual(exacte_optiekeuze("1", OPTIES), OPTIES[0])
        self.assertEqual(exacte_optiekeuze("2", OPTIES), OPTIES[1])

    def test_nummer_met_woord_ervoor(self):
        for tekst in ("optie 2", "keuze 2", "nummer 2"):
            with self.subTest(tekst=tekst):
                self.assertEqual(exacte_optiekeuze(tekst, OPTIES), OPTIES[1])

    def test_leestekens_en_hoofdletters_doen_er_niet_toe(self):
        for tekst in ("2.", " 2 ", "OPTIE 2"):
            with self.subTest(tekst=tekst):
                self.assertEqual(exacte_optiekeuze(tekst, OPTIES), OPTIES[1])

    def test_letterlijke_optietekst(self):
        self.assertEqual(exacte_optiekeuze("Base (next)", OPTIES), OPTIES[1])
        self.assertEqual(exacte_optiekeuze("base next", OPTIES), OPTIES[1])


class GeenExacteKeuze(unittest.TestCase):
    """Bij twijfel: bevestigen. Elk van deze gevallen moet None geven."""

    def test_meer_dan_een_optie(self):
        self.assertIsNone(exacte_optiekeuze("1 en 2", OPTIES))
        self.assertIsNone(exacte_optiekeuze("beide", OPTIES))

    def test_ontkenning(self):
        self.assertIsNone(exacte_optiekeuze("niet 1", OPTIES))
        self.assertIsNone(exacte_optiekeuze("geen van beide", OPTIES))

    def test_nummer_buiten_bereik(self):
        self.assertIsNone(exacte_optiekeuze("3", OPTIES))
        self.assertIsNone(exacte_optiekeuze("0", OPTIES))

    def test_extra_voorwaarde_maakt_het_geen_keuze_meer(self):
        self.assertIsNone(
            exacte_optiekeuze("Base (next), maar alleen in CI", OPTIES))
        self.assertIsNone(exacte_optiekeuze("2 mits we later upgraden", OPTIES))

    def test_samenvatting_is_geen_exacte_tekst(self):
        """'strict' is niet hetzelfde als 'Strict (next/core-web-vitals)'."""
        self.assertIsNone(exacte_optiekeuze("strict", OPTIES))

    def test_vrije_tekst(self):
        self.assertIsNone(
            exacte_optiekeuze("doe maar wat jullie het beste lijkt", OPTIES))

    def test_leeg_antwoord(self):
        self.assertIsNone(exacte_optiekeuze("", OPTIES))
        self.assertIsNone(exacte_optiekeuze("   ", OPTIES))

    def test_zonder_opties_nooit(self):
        self.assertIsNone(exacte_optiekeuze("1", []))

    def test_dubbele_opties_zijn_niet_eenduidig(self):
        self.assertIsNone(exacte_optiekeuze("zelfde", ["Zelfde", "zelfde"]))


class DoorDeFlow(TempCase):
    """De regel moet ook echt in de sessiemachine landen."""

    def setUp(self):
        super().setUp()
        self.project = self.make_project("keuze")
        self.scope = self.db.scope("keuze")
        self.task_id = self.scope.add_task("t", "s", ["a"])
        self.question_id = self.scope.add_question(
            "Welke preset?", "block", "preset", options=OPTIES, task_id=self.task_id)
        self.flow = AnswerFlow(self.scope, channel="test")
        self.session = self.flow.open(self.question_id, "Welke preset?", self.task_id)

    def test_exacte_keuze_wordt_meteen_toegepast(self):
        stap = self.flow.submit(self.session, "2")
        self.assertIs(stap.act, Act.APPLY)
        self.assertEqual(stap.text, OPTIES[1])
        self.assertEqual(
            self.scope.answer_session(self.session)["state"], "resolved",
            "de sessie wacht nog op een bevestiging",
        )

    def test_vrije_tekst_wordt_wel_bevestigd(self):
        stap = self.flow.submit(self.session, "doe de strenge variant denk ik")
        self.assertIsNot(stap.act, Act.APPLY,
                         "vrije tekst is zonder bevestiging vastgelegd")

    def test_extra_voorwaarde_wordt_wel_bevestigd(self):
        stap = self.flow.submit(self.session, "2 maar alleen als de build groen blijft")
        self.assertIsNot(stap.act, Act.APPLY)

    def test_de_reden_staat_in_de_audittrail(self):
        self.flow.submit(self.session, "1")
        beurten = self.scope.turns(self.session)
        laatste = beurten[-1]
        self.assertIn("exacte optiekeuze", (laatste["note"] or ""))


if __name__ == "__main__":
    unittest.main()


class SpraakHoudtDeBevestiging(TempCase):
    """Bij een transcriptie zegt 'exact' alleen dat de transcriptie exact is.

    Niet dat er exact dat gezegd is. Een verkeerd verstaan antwoord dat toevallig
    op een optie past, mag geen beslissing worden.
    """

    def setUp(self):
        super().setUp()
        self.project = self.make_project("spraakkeuze")
        self.scope = self.db.scope("spraakkeuze")
        task_id = self.scope.add_task("t", "s", ["a"])
        self.question_id = self.scope.add_question(
            "Welke preset?", "block", "preset-spraak", options=OPTIES, task_id=task_id)

    def _flow(self, transcribed: bool):
        flow = AnswerFlow(self.scope, channel="test", transcribed=transcribed)
        return flow, flow.open(self.question_id, "Welke preset?")

    def test_getypt_gaat_meteen_door(self):
        flow, sessie = self._flow(transcribed=False)
        self.assertIs(flow.submit(sessie, "2").act, Act.APPLY)

    def test_verstaan_wordt_altijd_bevestigd(self):
        flow, sessie = self._flow(transcribed=True)
        stap = flow.submit(sessie, "2", confidence=0.99)
        self.assertIsNot(stap.act, Act.APPLY,
                         "een verstaan antwoord is zonder bevestiging vastgelegd")

    def test_ook_zonder_confidence_blijft_spraak_spraak(self):
        """De correctieronde binnen hetzelfde gesprek geeft geen confidence mee."""
        flow, sessie = self._flow(transcribed=True)
        self.assertIsNot(flow.submit(sessie, "2").act, Act.APPLY)
