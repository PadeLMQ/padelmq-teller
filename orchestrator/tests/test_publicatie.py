"""Pushen en een PR openen — en nooit mergen."""

from orchestrator.cost import CostGuard
from orchestrator.git import GitAdapter, run_git
from orchestrator.models import TaskStatus
from orchestrator.notify import ConsoleNotifier
from orchestrator.runner import Runner
from orchestrator.verify import VerifyAdapter
from tests.base import TempCase
from tests.fakes import FakeExecutor, FakeReviewer

GROEN = "python3 -c \"import sys; sys.exit(0)\""


class FakeGitHub:
    def __init__(self, fail: bool = False):
        self.fail = fail
        self.calls = []

    def create_pull_request(self, repo, *, title, body, head, base):
        if self.fail:
            raise RuntimeError("422 validation failed")
        self.calls.append({"repo": repo, "title": title, "body": body,
                           "head": head, "base": base})
        return {"html_url": f"https://github.com/{repo}/pull/7", "number": 7}


class Publicatie(TempCase):
    def build(self, *, github=None):
        # Een kale repo als 'origin', zodat pushen echt werkt.
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
        self.github = github
        self.notifier = ConsoleNotifier()
        return Runner(
            settings=self.settings, project=self.project, scope=self.scope,
            executor=FakeExecutor([{"write": {"app.py": "def total(x):\n    return x + 1\n"}}]),
            reviewer=FakeReviewer(), verifier=VerifyAdapter(timeout_seconds=60),
            git=GitAdapter(self.tmp / "worktrees"), notifier=self.notifier,
            cost=CostGuard(self.db, self.settings), github=github,
        )

    def test_branch_wordt_gepusht_en_pr_geopend(self):
        github = FakeGitHub()
        runner = self.build(github=github)
        task_id = self.scope.add_task("Verhoog het totaal met één",
                                      acceptance=["total(1) geeft 2"])
        outcome = runner.run_task(task_id)

        self.assertEqual(outcome.status, TaskStatus.DONE)
        self.assertIn("pull/7", outcome.detail)
        self.assertEqual(len(github.calls), 1)
        call = github.calls[0]
        self.assertEqual(call["head"], f"orch/{task_id}")
        self.assertEqual(call["base"], "main")
        self.assertIn("Acceptatiecriteria", call["body"])
        self.assertIn("nooit automatisch gemerged", call["body"])

        # de branch staat echt op origin, main is niet aangeraakt
        remote = run_git(self.project.repo_root, "ls-remote", "--heads", "origin")
        self.assertIn(f"orch/{task_id}", remote)
        self.assertEqual(
            len(run_git(self.project.repo_root, "log", "--oneline", "main").strip().splitlines()),
            1,
        )

    def test_er_wordt_nooit_gemerged(self):
        github = FakeGitHub()
        runner = self.build(github=github)
        task_id = self.scope.add_task("X", acceptance=["A"])
        runner.run_task(task_id)
        self.assertFalse(hasattr(github, "merge_pull_request"),
                         "de orkestrator heeft geen mergepad")
        main_before = run_git(self.project.repo_root, "rev-parse", "main").strip()
        orch = run_git(self.project.repo_root, "rev-parse", f"orch/{task_id}").strip()
        self.assertNotEqual(main_before, orch)

    def test_mislukte_pr_is_geen_mislukte_taak(self):
        runner = self.build(github=FakeGitHub(fail=True))
        task_id = self.scope.add_task("X", acceptance=["A"])
        outcome = runner.run_task(task_id)
        self.assertEqual(outcome.status, TaskStatus.PR_OPEN)
        self.assertIn("PR openen mislukte", outcome.detail)
        remote = run_git(self.project.repo_root, "ls-remote", "--heads", "origin")
        self.assertIn(f"orch/{task_id}", remote, "de branch hoort er wel te staan")

    def test_zonder_github_blijft_het_bij_een_gepushte_branch(self):
        runner = self.build(github=None)
        task_id = self.scope.add_task("X", acceptance=["A"])
        outcome = runner.run_task(task_id)
        self.assertEqual(outcome.status, TaskStatus.PR_OPEN)
        self.assertIn("geen github_repo", outcome.detail)
