"""Git: worktree per run, branch orch/<taak-id>, commit, push, PR.

Nooit rechtstreeks naar main. Committen gebeurt uitsluitend na groene
verificatie; dat wordt in de runner afgedwongen.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


class GitError(RuntimeError):
    pass


def run_git(repo: Path, *args: str, check: bool = True) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=str(repo), capture_output=True, text=True, timeout=300
    )
    if check and proc.returncode != 0:
        raise GitError(f"git {' '.join(args)} faalde: {proc.stderr.strip()}")
    return proc.stdout


@dataclass
class Worktree:
    path: Path
    branch: str
    repo: Path

    def diff(self, base: str) -> str:
        return run_git(self.path, "diff", f"{base}...HEAD")

    def full_diff(self, base: str) -> str:
        """Alles wat deze branch verandert ten opzichte van base.

        Dus vastgelegd EN nog niet vastgelegd werk. De beoordelaar moet het
        geheel zien: bij een hervatte taak staat alles al in een commit en zou
        een diff van alleen de werkmap leeg zijn. Een beoordelaar die niets
        ziet, keurt alles goed.
        """
        run_git(self.path, "add", "-A", "-N")
        return run_git(self.path, "diff", base)

    def uncommitted_diff(self) -> str:
        """Diff inclusief nieuwe bestanden.

        'git diff' toont alleen gevolgde bestanden; met 'add -N' worden nieuwe
        bestanden als leeg toegevoegd zodat ze wel in de diff verschijnen. Zonder
        dit zou een verzonnen waarde in een nieuw bestand aan de controle
        ontsnappen.
        """
        run_git(self.path, "add", "-A", "-N", check=False)
        return run_git(self.path, "diff")

    def has_changes(self) -> bool:
        return bool(run_git(self.path, "status", "--porcelain").strip())


class GitAdapter:
    def __init__(self, workdir: Path):
        self.workdir = Path(workdir)
        self.workdir.mkdir(parents=True, exist_ok=True)

    def create_worktree(self, repo: Path, branch: str, base: str) -> Worktree:
        repo = Path(repo)
        if not (repo / ".git").exists():
            raise GitError(f"{repo} is geen git-repository")
        target = self.workdir / branch.replace("/", "_")
        if target.exists():
            run_git(repo, "worktree", "remove", "--force", str(target), check=False)
        run_git(repo, "fetch", "--all", "--quiet", check=False)
        # Een eerdere poging kan gestrand zijn en de branch achtergelaten hebben.
        # Dan hangen we de worktree aan die bestaande branch in plaats van hem
        # opnieuw aan te maken; -b zou hier alleen maar falen. De branch wordt
        # nooit automatisch weggegooid: daar kan al vastgelegd werk in zitten en
        # dat weggooien is niet terug te draaien.
        if self._branch_exists(repo, branch):
            run_git(repo, "worktree", "add", str(target), branch)
        else:
            run_git(repo, "worktree", "add", "-b", branch, str(target), base)
        return Worktree(path=target, branch=branch, repo=repo)

    @staticmethod
    def _branch_exists(repo: Path, branch: str) -> bool:
        out = run_git(repo, "branch", "--list", branch, check=False)
        return bool(out.strip())

    def remove_worktree(self, worktree: Worktree) -> None:
        run_git(worktree.repo, "worktree", "remove", "--force", str(worktree.path), check=False)

    def commit(self, worktree: Worktree, message: str, author: str,
               base: str | None = None) -> str:
        run_git(worktree.path, "add", "-A")
        if not run_git(worktree.path, "status", "--porcelain").strip():
            # Bij een hervatte taak staat het werk al in een commit. Dan is er
            # niets te committen omdat het al gebeurd is, en dat is geen fout:
            # we geven de bestaande kop terug. Alleen als er ook ten opzichte
            # van base niets staat, is er werkelijk niets gedaan.
            if base is not None:
                aantal = run_git(worktree.path, "rev-list", "--count",
                                 f"{base}..HEAD", check=False).strip()
                if aantal.isdigit() and int(aantal) > 0:
                    return run_git(worktree.path, "rev-parse", "HEAD").strip()
            raise GitError("niets te committen")
        name, _, email = author.partition("<")
        run_git(
            worktree.path,
            "-c", f"user.name={name.strip() or 'orchestrator'}",
            "-c", f"user.email={email.rstrip('>').strip() or 'bot@localhost'}",
            "commit", "-m", message,
        )
        return run_git(worktree.path, "rev-parse", "HEAD").strip()

    def push(self, worktree: Worktree) -> None:
        run_git(worktree.path, "push", "-u", "origin", worktree.branch)

    @staticmethod
    def guard_branch(branch: str, protected: str) -> None:
        """Laatste vangnet: nooit committen op de hoofdbranch."""
        if branch.strip() == protected.strip():
            raise GitError(
                f"weigering: er wordt niet rechtstreeks op {protected!r} gewerkt"
            )
