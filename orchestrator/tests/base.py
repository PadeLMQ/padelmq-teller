import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from orchestrator.config import ModelPrice, Settings  # noqa: E402
from orchestrator.db import Database  # noqa: E402
from orchestrator import projects as projects_mod  # noqa: E402


class TempCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.settings = Settings(
            data_dir=self.tmp / "data",
            db_path=self.tmp / "data" / "db.sqlite3",
            projects_dir=self.tmp / "data" / "projects",
        )
        self.settings.prices["reviewer-test"] = ModelPrice(2.0, 12.0)
        self.settings.prices["executor-test"] = ModelPrice(5.0, 25.0)
        self.settings.ensure_dirs()
        self.db = Database(self.settings.db_path)
        self.addCleanup(self.db.close)

    def make_repo(self, name: str = "repo") -> Path:
        repo = self.tmp / name
        repo.mkdir()
        (repo / "app.py").write_text("def total(x):\n    return x\n", encoding="utf-8")
        self._git(repo, "init", "-q", "-b", "main")
        self._git(repo, "add", "-A")
        self._git(repo, "-c", "user.name=t", "-c", "user.email=t@t",
                  "commit", "-q", "-m", "init")
        return repo

    @staticmethod
    def _git(repo: Path, *args: str) -> None:
        proc = subprocess.run(["git", *args], cwd=str(repo), capture_output=True, text=True)
        if proc.returncode != 0:
            raise AssertionError(f"git {' '.join(args)}: {proc.stderr}")

    def make_project(self, slug: str = "demo", checks: dict | None = None, repo: Path | None = None):
        repo = repo or self.make_repo(slug + "-repo")
        project = projects_mod.add(
            self.settings, slug, str(repo), checks=checks if checks is not None else {}
        )
        self.db.ensure_project(slug)
        return project
