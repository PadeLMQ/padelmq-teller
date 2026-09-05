"""Het eindrapport moet precies de twaalf afgesproken punten bevatten.

De test draait een volledige lus met nepmodellen en leest daarna het rapport,
zodat bewezen is dat de lus vastlegt wat het rapport nodig heeft.
"""

import json

from orchestrator.adapters import Alternative, ReviewResult
from orchestrator.cost import CostGuard
from orchestrator.git import GitAdapter, run_git
from orchestrator.models import Citation, Question, TaskStatus, Verdict
from orchestrator.notify import ConsoleNotifier
from orchestrator.runner import Runner
from orchestrator.runreport import build_report, format_report
from orchestrator.verify import VerifyAdapter
from tests.base import TempCase
from tests.fakes import FakeExecutor, FakeReviewer

GROEN = "python3 -c \"import sys; sys.exit(0)\""


class FakeGitHub:
    def create_pull_request(self, repo, *, title, body, head, base):
        return {"html_url": f"https://github.com/{repo}/pull/3", "number": 3}


class Runrapport(TempCase):
    def bouw(self, *, steps, reviewer=None, github=None):
        repo = self.make_repo("pilot")
        origin = self.tmp / "origin.git"
        run_git(repo, "init", "--bare", "-q", str(origin))
        run_git(repo, "remote", "add", "origin", str(origin))
        run_git(repo, "push", "-q", "origin", "main")

        self.project = self.make_project("pilot", checks={"tests": GROEN}, repo=repo)
        self.project.github_repo = "PadeLMQ/pilot"
        self.scope = self.db.scope("pilot")
        self.settings.executor_model = "executor-test"
        self.settings.reviewer_model = "reviewer-test"

        # Een bevestigd kennisitem zodat een AUTO-antwoord een echte bron heeft.
        self.decision = self.project.knowledge.append_decision(
            "Taal van de code", "Commentaar en tests in het Nederlands.",
            source="intake", confirmed_by_human=True,
        )
        self.project.knowledge.load()

        return Runner(
            settings=self.settings, project=self.project, scope=self.scope,
            executor=FakeExecutor(steps),
            reviewer=reviewer or FakeReviewer(),
            verifier=VerifyAdapter(timeout_seconds=60),
            git=GitAdapter(self.tmp / "worktrees"),
            notifier=ConsoleNotifier(),
            cost=CostGuard(self.db, self.settings),
            github=github,
        )

    def test_rapport_bevat_alle_twaalf_punten(self):
        vraag = Question(
            text="In welke taal schrijven we het commentaar?",
            proposed_answer="Nederlands.",
            citations=[Citation("kb:D-001")],
        )
        reviewer = FakeReviewer(
            answers=[vraag],
            reviews=[ReviewResult(
                verdict=Verdict.PASS, acceptance_met=["format.ts heeft tests"],
                alternative=Alternative("Voeg ook een test voor dateShort toe",
                                        "meer dekking", "format.ts:9", "vijf minuten",
                                        "later"),
            )],
        )
        runner = self.bouw(
            steps=[
                {"questions": [Question(text="In welke taal schrijven we het commentaar?")]},
                {"write": {"format.test.ts": "// test\n"}},
            ],
            reviewer=reviewer,
            github=FakeGitHub(),
        )
        task_id = self.scope.add_task(
            "Voeg tests toe voor format.ts",
            spec="Alleen tests, geen gedragswijziging.",
            acceptance=["format.ts heeft tests", "npm run test slaagt"],
        )
        uitkomst = runner.run_task(task_id)
        self.assertEqual(uitkomst.status, TaskStatus.DONE)

        d = build_report(self.scope, self.project, task_id).data

        # 1 taak
        self.assertEqual(d["1_taak"]["titel"], "Voeg tests toe voor format.ts")
        self.assertEqual(len(d["1_taak"]["acceptatiecriteria"]), 2)

        # 2 wat Claude deed
        self.assertGreaterEqual(len(d["2_wat_claude_deed"]), 1)
        self.assertIsNotNone(d["2_wat_claude_deed"][0]["samenvatting"])

        # 3 harde verificatie met commando en exitcode
        check = d["3_harde_verificatie"][0]["checks"][0]
        self.assertEqual(check["naam"], "tests")
        self.assertEqual(check["exitcode"], 0)
        self.assertTrue(check["geslaagd"])

        # 4 exact welke context de reviewer had
        contexten = d["4_context_voor_de_reviewer"]
        self.assertTrue(any(c["fase"] == "beantwoorden" for c in contexten))
        self.assertTrue(any(c["fase"] == "beoordelen" for c in contexten))
        eerste = contexten[0]
        self.assertEqual(eerste["waarvan_bevestigd"], 1)
        self.assertEqual(len(eerste["context_sha256"]), 64)
        self.assertIn(self.decision, [i["id"] for i in eerste["kennisitems"]])

        # 5 en 6 triage met motivatie en bronnen
        triage = d["5_6_triage"][0]
        self.assertEqual(triage["uitkomst"], "auto")
        self.assertTrue(triage["motivatie"])
        self.assertTrue(triage["gebruikte_bronnen"])
        self.assertIn("kb:D-001", triage["aangeboden_bronnen"])

        # 7 ging Claude zelfstandig verder
        self.assertTrue(d["7_claude_ging_zelfstandig_verder"]["antwoord"])
        self.assertFalse(d["7_claude_ging_zelfstandig_verder"]["menselijk_antwoord_tussendoor"])

        # 8 aanroepen per rol
        self.assertEqual(
            set(d["8_aanroepen"]["per_rol"]), {"uitvoerder", "beantwoorder", "beoordelaar"}
        )

        # 9 tokens en kosten per model
        modellen = d["9_tokens_en_kosten"]["per_model"]
        self.assertIn("executor-test", modellen)
        self.assertIn("reviewer-test", modellen)
        self.assertGreater(modellen["executor-test"]["tokens_in"], 0)
        self.assertGreater(d["9_tokens_en_kosten"]["totaal_eur"], 0)

        # 10 looptijd
        self.assertIsNotNone(d["10_looptijd"]["seconden"])

        # 11 oplevering
        self.assertEqual(d["11_oplevering"]["branch"], f"orch/{task_id}")
        self.assertEqual(len(d["11_oplevering"]["commits"]), 1)
        self.assertIn("pull/3", str(d["11_oplevering"]["pull_request"]))

        # 12 vragen aan de mens: geen
        self.assertEqual(d["12_vragen_aan_de_mens"], [])

    def test_geparkeerde_vraag_komt_in_punt_twaalf(self):
        runner = self.bouw(steps=[{"questions": [Question(text="Welke knoptekst?")]}])
        task_id = self.scope.add_task("A", acceptance=["A"])
        self.scope.add_task("onafhankelijk werk", acceptance=["B"])
        runner.run_task(task_id)

        d = build_report(self.scope, self.project, task_id).data
        self.assertEqual(len(d["12_vragen_aan_de_mens"]), 1)
        self.assertEqual(d["12_vragen_aan_de_mens"][0]["uitkomst"], "park")
        self.assertFalse(d["7_claude_ging_zelfstandig_verder"]["antwoord"])
        self.assertIsNone(d["11_oplevering"]["branch"])

    def test_leesbare_uitvoer_bevat_de_kopjes(self):
        runner = self.bouw(steps=[{"write": {"a.txt": "x\n"}}], github=FakeGitHub())
        task_id = self.scope.add_task("A", acceptance=["A"])
        runner.run_task(task_id)
        tekst = format_report(build_report(self.scope, self.project, task_id))
        for kop in ["## 1. De taak", "## 2. Wat Claude deed", "## 3. Harde verificatie",
                    "## 4. Welke context de reviewer had", "## 5 en 6. Triage",
                    "## 7. Ging Claude zelfstandig verder?", "## 8. Aantal aanroepen",
                    "## 9. Tokens en kosten per model", "## 10. Looptijd",
                    "## 11. Oplevering", "## 12. Vragen die bij jou terechtkwamen"]:
            self.assertIn(kop, tekst, f"ontbreekt: {kop}")

    def test_rapport_is_ook_als_json_bruikbaar(self):
        runner = self.bouw(steps=[{"write": {"a.txt": "x\n"}}])
        task_id = self.scope.add_task("A", acceptance=["A"])
        runner.run_task(task_id)
        rapport = build_report(self.scope, self.project, task_id)
        opnieuw = json.loads(rapport.as_json())
        self.assertEqual(opnieuw["1_taak"]["id"], task_id)

    def test_onbekende_taak_wordt_geweigerd(self):
        self.bouw(steps=[{}])
        with self.assertRaises(ValueError):
            build_report(self.scope, self.project, 9999)
