"""Gesproken antwoorden: nooit aanvullen, nooit raden, altijd naspeurbaar."""

from orchestrator.answer_session import (
    Act, AnswerFlow, Clarity, Interpretation, assess, match_options,
)
from orchestrator.models import ItemStatus, TaskStatus
from orchestrator.voice import VoiceQueue
from tests.base import TempCase


class VageLezer:
    """Leest een open antwoord als meerduidig."""

    def interpret(self, *, question, options, transcript):
        return Interpretation(text=transcript, unambiguous=False,
                              alternatives=["lezing A", "lezing B"])


class OnvolledigeLezer:
    def interpret(self, *, question, options, transcript):
        return Interpretation(text=transcript, missing=["het bedrag"])


class HeldereLezer:
    def interpret(self, *, question, options, transcript):
        return Interpretation(text=f"gelezen: {transcript}")


class Poort(TempCase):
    """De ondubbelzinnigheidspoort, los van kanaal en opslag."""

    def test_leeg_antwoord_leidt_tot_doorvragen(self):
        uit = assess(question="v", options=[], transcript="   ")
        self.assertEqual(uit.clarity, Clarity.EMPTY)
        self.assertIn("niets verstaan", uit.clarification)

    def test_slechte_transcriptie_leidt_tot_doorvragen(self):
        uit = assess(question="v", options=[], transcript="iets", confidence=0.4)
        self.assertEqual(uit.clarity, Clarity.LOW_CONFIDENCE)
        self.assertIn("0.40", uit.reason)

    def test_goede_transcriptie_mag_door(self):
        uit = assess(question="v", options=[], transcript="inclusief btw",
                     confidence=0.95)
        self.assertEqual(uit.clarity, Clarity.CLEAR)

    def test_een_optie_noemen_is_eenduidig(self):
        uit = assess(question="Btw?", options=["inclusief btw", "exclusief btw"],
                     transcript="doe maar inclusief btw")
        self.assertEqual(uit.clarity, Clarity.CLEAR)
        self.assertEqual(uit.interpretation, "inclusief btw")

    def test_twee_opties_noemen_is_niet_eenduidig(self):
        uit = assess(question="Btw?", options=["inclusief btw", "exclusief btw"],
                     transcript="inclusief of eigenlijk exclusief, kies maar")
        self.assertEqual(uit.clarity, Clarity.MULTIPLE)
        self.assertIn("Welke", uit.clarification)

    def test_geen_enkele_optie_noemen_is_niet_eenduidig(self):
        uit = assess(question="Btw?", options=["inclusief btw", "exclusief btw"],
                     transcript="doe maar wat jij denkt")
        self.assertEqual(uit.clarity, Clarity.MULTIPLE)
        self.assertIn("opties zijn", uit.clarification)

    def test_meerduidige_lezing_leidt_tot_doorvragen(self):
        uit = assess(question="v", options=[], transcript="het hangt ervan af",
                     interpreter=VageLezer())
        self.assertEqual(uit.clarity, Clarity.MULTIPLE)

    def test_onvolledig_antwoord_wordt_niet_aangevuld(self):
        uit = assess(question="v", options=[], transcript="verhoog het maar",
                     interpreter=OnvolledigeLezer())
        self.assertEqual(uit.clarity, Clarity.INCOMPLETE)
        self.assertIn("het bedrag", uit.clarification)
        self.assertIsNone(uit.interpretation)

    def test_weet_ik_niet_wordt_niet_als_antwoord_gelezen(self):
        uit = assess(question="v", options=["a", "b"], transcript="geen idee, later")
        self.assertEqual(uit.clarity, Clarity.DEFERRED)

    def test_optiekoppeling_negeert_woorden_die_in_alle_opties_staan(self):
        # "btw" staat in beide opties en mag dus niet doorslaggevend zijn.
        self.assertEqual(match_options("gewoon btw", ["inclusief btw", "exclusief btw"]), [])
        self.assertEqual(match_options("exclusief graag", ["inclusief btw", "exclusief btw"]),
                         ["exclusief btw"])


class Spraakgesprek(TempCase):
    def opzet(self, opties=None, lezer=None):
        self.project = self.make_project("pilot")
        self.scope = self.db.scope("pilot")
        self.task_id = self.scope.add_task("Wachtende taak", acceptance=["A"])
        self.question_id = self.scope.add_question(
            "Tonen we de btw inclusief of exclusief?", "block", "btw incl of excl",
            options=opties or [], task_id=self.task_id,
        )
        self.scope.set_task(self.task_id, status=TaskStatus.BLOCKED.value,
                            blocked_by_question=self.question_id)
        return VoiceQueue(self.scope, self.project, interpreter=lezer)

    def test_vraag_wordt_aangeboden_om_voor_te_lezen(self):
        queue = self.opzet(opties=["inclusief btw", "exclusief btw"])
        prompt = queue.next_question()
        self.assertIsNotNone(prompt)
        self.assertIn("btw", prompt.text.lower())
        self.assertIn("opties zijn", prompt.text.lower())
        self.assertEqual(prompt.task_id, self.task_id)

    def test_geheimen_worden_nooit_voorgelezen(self):
        self.project = self.make_project("pilot")
        self.scope = self.db.scope("pilot")
        qid = self.scope.add_question(
            "Klopt dit token: SHOPIFY_ADMIN_TOKEN=zeergeheimewaarde123?",
            "block", "token", task_id=None,
        )
        queue = VoiceQueue(self.scope, self.project)
        prompt = queue.next_question()
        self.assertNotIn("zeergeheimewaarde123", prompt.text)

    def test_volledig_gesprek_vraag_antwoord_bevestiging(self):
        queue = self.opzet(opties=["inclusief btw", "exclusief btw"])
        prompt = queue.next_question()

        stap1 = queue.submit(prompt.session_id, "doe maar inclusief btw", confidence=0.95)
        self.assertFalse(stap1.finished)
        self.assertIn("Klopt dat?", stap1.speak)
        # nog niets vastgelegd voor de bevestiging
        self.assertEqual(self.project.knowledge.load(), {})
        self.assertEqual(self.scope.task(self.task_id)["status"], TaskStatus.BLOCKED.value)

        stap2 = queue.submit(prompt.session_id, "ja", confidence=0.99)
        self.assertTrue(stap2.applied)
        self.assertEqual(stap2.resumed_tasks, 1)
        item = self.project.knowledge.get(stap2.decision_id)
        self.assertEqual(item.status, ItemStatus.CONFIRMED)
        self.assertIn("inclusief btw", item.body)
        self.assertEqual(self.scope.task(self.task_id)["status"], TaskStatus.QUEUED.value)

    def test_een_verduidelijking_daarna_alsnog_klaar(self):
        queue = self.opzet(opties=["inclusief btw", "exclusief btw"])
        prompt = queue.next_question()

        vaag = queue.submit(prompt.session_id, "doe maar wat", confidence=0.95)
        self.assertFalse(vaag.finished)
        self.assertIn("opties zijn", vaag.speak)

        goed = queue.submit(prompt.session_id, "inclusief btw", confidence=0.95)
        self.assertIn("Klopt dat?", goed.speak)
        klaar = queue.submit(prompt.session_id, "ja")
        self.assertTrue(klaar.applied)

    def test_na_een_verduidelijking_blijft_het_geblokkeerd_in_plaats_van_geraden(self):
        queue = self.opzet(opties=["inclusief btw", "exclusief btw"])
        prompt = queue.next_question()
        queue.submit(prompt.session_id, "doe maar wat", confidence=0.95)
        tweede = queue.submit(prompt.session_id, "nog steeds onduidelijk", confidence=0.95)
        self.assertTrue(tweede.finished)
        self.assertFalse(tweede.applied)
        self.assertIn("geblokkeerd", tweede.speak)
        self.assertEqual(self.project.knowledge.load(), {})
        self.assertEqual(self.scope.task(self.task_id)["status"], TaskStatus.BLOCKED.value)

    def test_slecht_verstaan_leidt_niet_tot_een_beslissing(self):
        queue = self.opzet(opties=["inclusief btw", "exclusief btw"])
        prompt = queue.next_question()
        uit = queue.submit(prompt.session_id, "inclusief btw", confidence=0.3)
        self.assertFalse(uit.applied)
        self.assertIn("verstond je niet", uit.speak)

    def test_weet_ik_niet_houdt_de_blokkade_zonder_door_te_vragen(self):
        queue = self.opzet(opties=["inclusief btw", "exclusief btw"])
        prompt = queue.next_question()
        uit = queue.submit(prompt.session_id, "geen idee, later", confidence=0.95)
        self.assertTrue(uit.finished)
        self.assertFalse(uit.applied)
        self.assertEqual(self.scope.task(self.task_id)["status"], TaskStatus.BLOCKED.value)

    def test_correctie_tijdens_de_bevestiging_wordt_opnieuw_beoordeeld(self):
        queue = self.opzet(opties=["inclusief btw", "exclusief btw"])
        prompt = queue.next_question()
        queue.submit(prompt.session_id, "inclusief btw", confidence=0.95)
        correctie = queue.submit(prompt.session_id, "nee, exclusief btw", confidence=0.95)
        self.assertIn("exclusief btw", correctie.speak)
        klaar = queue.submit(prompt.session_id, "ja")
        self.assertTrue(klaar.applied)
        self.assertIn("exclusief btw", self.project.knowledge.get(klaar.decision_id).body)

    def test_open_vraag_zonder_opties_wordt_letterlijk_bevestigd(self):
        queue = self.opzet(opties=[], lezer=HeldereLezer())
        prompt = queue.next_question()
        stap = queue.submit(prompt.session_id, "inclusief, altijd", confidence=0.9)
        self.assertIn("gelezen: inclusief, altijd", stap.speak)

    def test_audit_spoor_bevat_het_hele_gesprek(self):
        queue = self.opzet(opties=["inclusief btw", "exclusief btw"])
        prompt = queue.next_question()
        queue.submit(prompt.session_id, "doe maar wat", confidence=0.95)
        queue.submit(prompt.session_id, "inclusief btw", confidence=0.95)
        queue.submit(prompt.session_id, "ja")

        spoor = queue.audit(prompt.session_id)
        richtingen = [t["direction"] for t in spoor]
        self.assertEqual(richtingen[0], "gevraagd")
        self.assertIn("verduidelijking", richtingen)
        self.assertIn("bevestiging", richtingen)
        self.assertEqual(richtingen[-1], "afgesloten")
        # de transcriptiezekerheid hoort erbij
        self.assertTrue(any(t["confidence"] == 0.95 for t in spoor))
        # en het project en de taak staan vast
        self.assertTrue(all(t["session_id"] == prompt.session_id for t in spoor))

    def test_alleen_blokkades_worden_voorgelezen_geen_geparkeerde_vragen(self):
        queue = self.opzet()
        self.scope.add_question("Knoptekst?", "park", "knoptekst")
        prompt = queue.next_question()
        self.assertEqual(prompt.question_id, self.question_id)
