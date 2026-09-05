"""Projectregister. Een project toevoegen is één commando.

Niets in de kern kent een vaste projectlijst; dat is beslissing B6.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .config import Settings
from .knowledge import KnowledgeStore
from .models import VerificationStrength
from .verify import infer_strength


class ProjectError(RuntimeError):
    pass


@dataclass
class Project:
    slug: str
    repo: str
    root: Path
    default_branch: str = "main"
    checks: dict[str, str] = field(default_factory=dict)
    strength: VerificationStrength = VerificationStrength.WEAK
    budget_daily_eur: float | None = None
    budget_task_eur: float | None = None
    reviewer_enabled: bool = True
    redact_patterns: list[str] = field(default_factory=lambda: [r"\.env", r"secret", r"token"])
    auto_merge: bool = False          # ontworpen, staat uit, niet geimplementeerd in V1
    branch_prefix: str = "orch/"
    github_repo: str = ""             # "eigenaar/repo" voor issues en PR's
    notify: list[str] = field(default_factory=lambda: ["email", "github"])

    @property
    def knowledge(self) -> KnowledgeStore:
        return KnowledgeStore(self.root / "kennis")

    @property
    def repo_root(self) -> Path:
        return Path(self.repo).expanduser()

    def to_yaml(self) -> str:
        return yaml.safe_dump(
            {
                "slug": self.slug,
                "repo": str(self.repo),
                "default_branch": self.default_branch,
                "github_repo": self.github_repo,
                "checks": self.checks,
                "verificatiesterkte": self.strength.value,
                "budget_daily_eur": self.budget_daily_eur,
                "budget_task_eur": self.budget_task_eur,
                "reviewer_enabled": self.reviewer_enabled,
                "redact_patterns": self.redact_patterns,
                "auto_merge": self.auto_merge,
                "branch_prefix": self.branch_prefix,
                "notify": self.notify,
            },
            sort_keys=False,
            allow_unicode=True,
        )


def project_dir(settings: Settings, slug: str) -> Path:
    return settings.projects_dir / slug


def load(settings: Settings, slug: str) -> Project:
    root = project_dir(settings, slug)
    config_path = root / "project.yaml"
    if not config_path.is_file():
        raise ProjectError(
            f"project {slug!r} bestaat niet; voeg het toe met"
            f" 'orchestrator project add {slug} --repo <pad>'"
        )
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    checks = dict(raw.get("checks") or {})
    strength_raw = str(raw.get("verificatiesterkte") or "").strip().lower()
    try:
        strength = VerificationStrength(strength_raw)
    except ValueError:
        strength = infer_strength(checks)
    return Project(
        slug=raw.get("slug", slug),
        repo=raw.get("repo", ""),
        root=root,
        default_branch=raw.get("default_branch", "main"),
        github_repo=raw.get("github_repo", "") or "",
        checks=checks,
        strength=strength,
        budget_daily_eur=raw.get("budget_daily_eur"),
        budget_task_eur=raw.get("budget_task_eur"),
        reviewer_enabled=bool(raw.get("reviewer_enabled", True)),
        redact_patterns=list(raw.get("redact_patterns") or []),
        auto_merge=bool(raw.get("auto_merge", False)),
        branch_prefix=raw.get("branch_prefix", "orch/"),
        notify=list(raw.get("notify") or ["email", "github"]),
    )


def list_projects(settings: Settings) -> list[str]:
    if not settings.projects_dir.exists():
        return []
    return sorted(
        p.name for p in settings.projects_dir.iterdir()
        if (p / "project.yaml").is_file()
    )


def add(
    settings: Settings,
    slug: str,
    repo: str,
    *,
    checks: dict[str, str] | None = None,
    github_repo: str = "",
    default_branch: str = "main",
) -> Project:
    settings.ensure_dirs()
    root = project_dir(settings, slug)
    if (root / "project.yaml").exists():
        raise ProjectError(f"project {slug!r} bestaat al")
    checks = checks or {}
    project = Project(
        slug=slug,
        repo=repo,
        root=root,
        default_branch=default_branch,
        github_repo=github_repo,
        checks=checks,
        strength=infer_strength(checks),
    )
    root.mkdir(parents=True, exist_ok=True)
    (root / "state").mkdir(exist_ok=True)
    project.knowledge.scaffold(slug)
    (root / "project.yaml").write_text(project.to_yaml(), encoding="utf-8")
    return project
