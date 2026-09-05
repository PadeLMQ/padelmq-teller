"""De datamap met je businessregels mag nooit binnen een git-repo liggen."""

import subprocess

from orchestrator.config import Settings
from tests.base import TempCase


class Datamap(TempCase):
    def test_datamap_buiten_git_is_in_orde(self):
        self.assertIsNone(self.settings.data_dir_inside_git())

    def test_datamap_binnen_een_repo_wordt_gesignaleerd(self):
        repo = self.tmp / "een-repo"
        (repo / "data").mkdir(parents=True)
        subprocess.run(["git", "init", "-q"], cwd=str(repo), check=True,
                       capture_output=True)
        settings = Settings(
            data_dir=repo / "data",
            db_path=repo / "data" / "db.sqlite3",
            projects_dir=repo / "data" / "projects",
        )
        self.assertEqual(settings.data_dir_inside_git(), repo.resolve())

    def test_ook_diep_genest_wordt_gevonden(self):
        repo = self.tmp / "repo2"
        diep = repo / "a" / "b" / "data"
        diep.mkdir(parents=True)
        subprocess.run(["git", "init", "-q"], cwd=str(repo), check=True,
                       capture_output=True)
        settings = Settings(data_dir=diep, db_path=diep / "d.db",
                            projects_dir=diep / "p")
        self.assertEqual(settings.data_dir_inside_git(), repo.resolve())
