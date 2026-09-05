"""Het spraakeindpunt: gemachtigd, begrensd, en altijd bij het juiste project."""

import json
import threading
import urllib.error
import urllib.request

from orchestrator.models import TaskStatus
from orchestrator.voice.api import RateLimiter, maak_server
from orchestrator.voice.service import VoiceService
from tests.base import TempCase

TOKEN = "een-voldoende-lang-testtoken-1234"  # nep-geheim: alleen voor deze test


class VoiceApi(TempCase):
    def setUp(self):
        super().setUp()
        self.project = self.make_project("pilot")
        self.scope = self.db.scope("pilot")
        self.task_id = self.scope.add_task("Wachtende taak", acceptance=["A"])
        self.question_id = self.scope.add_question(
            "Tonen we de btw inclusief of exclusief?", "block", "btw incl of excl",
            options=["inclusief btw", "exclusief btw"], task_id=self.task_id,
        )
        self.scope.set_task(self.task_id, status=TaskStatus.BLOCKED.value,
                            blocked_by_question=self.question_id)

        service = VoiceService(self.settings, self.db)
        self.server = maak_server(service, host="127.0.0.1", port=0, token=TOKEN)
        self.poort = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    # -- hulpjes ---------------------------------------------------------
    def haal(self, pad, token=TOKEN):
        verzoek = urllib.request.Request(f"http://127.0.0.1:{self.poort}{pad}")
        if token is not None:
            verzoek.add_header("X-Orch-Token", token)
        with urllib.request.urlopen(verzoek, timeout=5) as antwoord:
            return antwoord.status, json.loads(antwoord.read())

    def stuur(self, pad, payload, token=TOKEN):
        verzoek = urllib.request.Request(
            f"http://127.0.0.1:{self.poort}{pad}",
            data=json.dumps(payload).encode(), method="POST",
        )
        verzoek.add_header("Content-Type", "application/json")
        if token is not None:
            verzoek.add_header("X-Orch-Token", token)
        with urllib.request.urlopen(verzoek, timeout=5) as antwoord:
            return antwoord.status, json.loads(antwoord.read())

    # -- machtiging -------------------------------------------------------
    def test_zonder_token_geen_toegang(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.haal("/voice/next", token=None)
        self.assertEqual(ctx.exception.code, 401)

    def test_met_verkeerd_token_geen_toegang(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.haal("/voice/next", token="fout-token-dat-lang-genoeg-is-x")
        self.assertEqual(ctx.exception.code, 401)

    def test_de_foutmelding_verraadt_niets(self):
        try:
            self.haal("/voice/next", token=None)
        except urllib.error.HTTPError as fout:
            body = json.loads(fout.read())
            self.assertEqual(body, {"fout": "niet gemachtigd"})

    def test_health_heeft_geen_token_nodig(self):
        status, body = self.haal("/health", token=None)
        self.assertEqual((status, body), (200, {"status": "ok"}))

    def test_dienst_start_niet_zonder_deugdelijk_token(self):
        service = VoiceService(self.settings, self.db)
        for slecht in ["", "kort"]:
            with self.assertRaises(RuntimeError):
                maak_server(service, host="127.0.0.1", port=0, token=slecht)

    # -- de twee handelingen ---------------------------------------------
    def test_volgende_vraag_wordt_aangeboden(self):
        status, body = self.haal("/voice/next")
        self.assertEqual(status, 200)
        self.assertEqual(body["project"], "pilot")
        self.assertEqual(body["taak"], self.task_id)
        self.assertIn("btw", body["spreek"].lower())
        self.assertEqual(body["opties"], ["inclusief btw", "exclusief btw"])

    def test_niets_open_geeft_een_leeg_antwoord(self):
        self.scope.set_question(self.question_id, status="answered")
        status, body = self.haal("/voice/next")
        self.assertEqual(status, 200)
        self.assertIsNone(body["vraag"])
        self.assertIn("niets open", body["spreek"])

    def test_volledig_gesprek_over_http(self):
        _, vraag = self.haal("/voice/next")
        _, stap1 = self.stuur("/voice/answer", {
            "sessie": vraag["sessie"], "transcript": "doe maar inclusief btw", "zekerheid": 0.95,
        })
        self.assertFalse(stap1["vastgelegd"])
        self.assertIn("Klopt dat?", stap1["spreek"])

        _, stap2 = self.stuur("/voice/answer", {"sessie": vraag["sessie"], "transcript": "ja"})
        self.assertTrue(stap2["vastgelegd"])
        self.assertEqual(stap2["project"], "pilot")
        self.assertEqual(stap2["hervatte_taken"], 1)
        self.assertEqual(self.scope.task(self.task_id)["status"], TaskStatus.QUEUED.value)

    def test_slecht_verstaan_legt_niets_vast(self):
        _, vraag = self.haal("/voice/next")
        _, stap = self.stuur("/voice/answer", {
            "sessie": vraag["sessie"], "transcript": "inclusief btw", "zekerheid": 0.2,
        })
        self.assertFalse(stap["vastgelegd"])
        self.assertIn("verstond je niet", stap["spreek"])
        self.assertEqual(self.scope.task(self.task_id)["status"], TaskStatus.BLOCKED.value)

    def test_onbekende_sessie_wordt_geweigerd(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.stuur("/voice/answer", {"sessie": 9999, "transcript": "ja"})
        self.assertEqual(ctx.exception.code, 404)

    def test_ontbrekend_sessieveld_wordt_geweigerd(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.stuur("/voice/answer", {"transcript": "ja"})
        self.assertEqual(ctx.exception.code, 400)

    def test_onbruikbare_zekerheid_wordt_geweigerd(self):
        _, vraag = self.haal("/voice/next")
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.stuur("/voice/answer", {
                "sessie": vraag["sessie"], "transcript": "ja", "zekerheid": "veel",
            })
        self.assertEqual(ctx.exception.code, 400)

    def test_onbekend_pad_geeft_404(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.haal("/geheim")
        self.assertEqual(ctx.exception.code, 404)

    def test_onbekend_project_geeft_een_nette_fout(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.haal("/voice/next?project=bestaatniet")
        self.assertEqual(ctx.exception.code, 400)

    # -- meerdere projecten -----------------------------------------------
    def test_een_antwoord_komt_altijd_bij_het_juiste_project(self):
        tweede = self.make_project("tweede")
        scope2 = self.db.scope("tweede")
        taak2 = scope2.add_task("Andere taak", acceptance=["B"])
        vraag2 = scope2.add_question("Andere vraag?", "block", "andere vraag",
                                     options=["ja", "nee"], task_id=taak2)
        scope2.set_task(taak2, status=TaskStatus.BLOCKED.value, blocked_by_question=vraag2)

        _, a = self.haal("/voice/next?project=tweede")
        self.assertEqual(a["project"], "tweede")
        _, stap1 = self.stuur("/voice/answer", {"sessie": a["sessie"], "transcript": "ja"})
        _, stap2 = self.stuur("/voice/answer", {"sessie": a["sessie"], "transcript": "ja"})
        self.assertEqual(stap2["project"], "tweede")
        # het eerste project is niet aangeraakt
        self.assertEqual(self.scope.task(self.task_id)["status"], TaskStatus.BLOCKED.value)
        self.assertEqual(self.project.knowledge.load(), {})


class Snelheidsbegrenzing(TempCase):
    def test_boven_de_limiet_wordt_geweigerd(self):
        limiter = RateLimiter(per_minuut=3)
        self.assertTrue(all(limiter.toegestaan("1.2.3.4") for _ in range(3)))
        self.assertFalse(limiter.toegestaan("1.2.3.4"))

    def test_andere_afzender_heeft_een_eigen_emmer(self):
        limiter = RateLimiter(per_minuut=1)
        self.assertTrue(limiter.toegestaan("1.1.1.1"))
        self.assertFalse(limiter.toegestaan("1.1.1.1"))
        self.assertTrue(limiter.toegestaan("2.2.2.2"))
