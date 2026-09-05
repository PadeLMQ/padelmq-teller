"""Samenvatting en digest: het spoor moet terug te lezen zijn.

De audittrail blijft de waarheid. Deze tests bewaken dat de leeswijzer erboven
klopt en niets invult wat er niet staat.
"""

import json
import unittest

from orchestrator.report import daily_digest
from orchestrator.samenvatting import bouw, format_samenvatting

try:
    from tests.base import TempCase
except ImportError:  # pragma: no cover
    from base import TempCase


class SamenvattingPerTaak(TempCase):
    def setUp(self):
        super().setUp()
        self.project = self.make_project("tp")
        self.scope = self.db.scope("tp")
        self.task_id = self.scope.add_task(
            "Doe iets nuttigs", "de opdracht zoals gegeven", ["het werkt", "tests groen"])

    def _vul(self):
        s = self.scope
        t = self.task_id
        s.log("opdracht-aangenomen", {"issue": 42, "criteria": 2}, task_id=t)
        s.log("uitvoering", {"samenvatting": "bestand X aangepast"}, task_id=t)
        s.log("beoordeling", {"verdict": "revise", "bevindingen": [{"punt": "te breed"}],
                              "criteria_open": ["nog niet af"],
                              "instructie": "versmal het"}, task_id=t)
        s.log("uitvoering", {"samenvatting": "versmald zoals gevraagd"}, task_id=t)
        s.log("verificatie", {"ok": True, "checks": [
            {"naam": "tests", "commando": "npm run test", "exitcode": 0, "geslaagd": True}]},
            task_id=t)
        s.log("beoordeling", {"verdict": "pass", "bevindingen": [],
                              "criteria_open": []}, task_id=t)
        s.log("commit", {"sha": "abc1234", "branch": "orch/1"}, task_id=t)
        s.log("pr-geopend", {"url": "https://github.com/x/y/pull/9", "number": 9}, task_id=t)
        run = s.start_run(t, "task")
        s.record_call(phase="implement", role="uitvoerder", model="executor-test",
                      tokens_in=1, tokens_out=1, cached_in=0, cost_eur=0.30,
                      task_id=t, run_id=run, day="2026-09-05")
        s.record_call(phase="review", role="beoordelaar", model="reviewer-test",
                      tokens_in=1, tokens_out=1, cached_in=0, cost_eur=0.02,
                      task_id=t, run_id=run, day="2026-09-05")

    def test_alles_wat_gevraagd_is_staat_erin(self):
        self._vul()
        tekst = format_samenvatting(bouw(self.scope, self.task_id))
        for verwacht in ("de opdracht zoals gegeven",   # wat gevraagd werd
                         "bestand X aangepast",          # wat uitgevoerd werd
                         "te breed",                     # wat de beoordelaar afkeurde
                         "versmald zoals gevraagd",      # wat daarna gecorrigeerd is
                         "exit 0",                       # testresultaat
                         "abc1234",                      # commit
                         "pull/9",                       # PR
                         "0.320000"):                    # totale AI-kosten
            self.assertIn(verwacht, tekst, f"{verwacht!r} ontbreekt in de samenvatting")

    def test_de_weg_terug_naar_het_spoor_staat_erin(self):
        self._vul()
        tekst = format_samenvatting(bouw(self.scope, self.task_id))
        self.assertIn("orchestrator inspect tp", tekst)
        self.assertIn("audittrail", tekst.lower())

    def test_beslissingen_van_de_mens_komen_erin(self):
        vraag = self.scope.add_question("Btw inclusief?", "block", "vp", task_id=self.task_id)
        self.scope.set_question(vraag, issue_number=7, status="answered",
                                answer=json.dumps({"interpretation": "inclusief",
                                                   "decision": "D-001"}))
        tekst = format_samenvatting(bouw(self.scope, self.task_id))
        self.assertIn("Btw inclusief?", tekst)
        self.assertIn("inclusief", tekst)
        self.assertIn("D-001", tekst)
        self.assertIn("issue #7", tekst)

    def test_ontbrekende_stappen_worden_gemeld_niet_ingevuld(self):
        """Een samenvatting die gaten opvult, ondermijnt waarvoor ze bedoeld is."""
        tekst = format_samenvatting(bouw(self.scope, self.task_id))
        self.assertIn("geen beoordeling gedraaid", tekst)
        self.assertIn("geen checks gedraaid", tekst)
        self.assertIn("geen pull request", tekst)

    def test_onbekende_taak_geeft_niets(self):
        self.assertIsNone(bouw(self.scope, 9999))


class Digest(TempCase):
    def test_digest_toont_alles_wat_gevraagd_is(self):
        self.make_project("dp")
        scope = self.db.scope("dp")
        klaar = scope.add_task("Afgerond werk", "s", ["a"])
        scope.set_task(klaar, status="done")
        scope.log("pr-geopend", {"url": "https://github.com/x/y/pull/3"}, task_id=klaar)
        lopend = scope.add_task("Onderhanden werk", "s", ["a"])
        scope.set_task(lopend, status="implementing")
        vraag = scope.add_question("Open beslissing?", "block", "vb")
        scope.set_question(vraag, issue_number=11)
        run = scope.start_run(klaar, "task")
        scope.record_call(phase="implement", role="uitvoerder", model="executor-test",
                          tokens_in=1, tokens_out=1, cached_in=0, cost_eur=0.5,
                          task_id=klaar, run_id=run, day="2026-09-05")

        tekst = daily_digest(self.db, ["dp"], day="2026-09-05", symbol="$")

        self.assertIn("Afgerond werk", tekst)
        self.assertIn("pull/3", tekst)
        self.assertIn("Onderhanden werk", tekst)
        self.assertIn("Open beslissing?", tekst)
        self.assertIn("issue #11", tekst)
        self.assertIn("$0.5000", tekst)
        self.assertIn("orchestrator summary dp", tekst,
                      "de weg naar de details ontbreekt")

    def test_geen_euro_bij_dollars(self):
        self.make_project("dv")
        self.assertNotIn("€", daily_digest(self.db, ["dv"], day="2026-09-05", symbol="$"))

    def test_projecten_blijven_gescheiden(self):
        self.make_project("een")
        self.make_project("twee")
        self.db.scope("een").add_task("Taak van een", "s", ["a"])
        tekst = daily_digest(self.db, ["twee"], day="2026-09-05", symbol="$")
        self.assertNotIn("Taak van een", tekst)


if __name__ == "__main__":
    unittest.main()
