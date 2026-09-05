"""Kerntypes. Bewust zonder externe afhankelijkheden."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime, timezone


def now() -> str:
    """UTC-tijdstempel in ISO-formaat. Overal dezelfde vorm, zodat sorteren werkt."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class TaskStatus(str, enum.Enum):
    QUEUED = "queued"
    BASELINE = "baseline"
    ANSWERING = "answering"
    PARKED = "parked"
    BLOCKED = "blocked"
    IMPLEMENTING = "implementing"
    VERIFYING = "verifying"
    REVIEWING = "reviewing"
    COMMITTING = "committing"
    PR_OPEN = "pr_open"
    DONE = "done"
    FAILED = "failed"

    @property
    def is_terminal(self) -> bool:
        return self in (TaskStatus.DONE, TaskStatus.FAILED)

    @property
    def waits_for_human(self) -> bool:
        return self in (TaskStatus.PARKED, TaskStatus.BLOCKED)


class Triage(str, enum.Enum):
    """De drie uitkomsten uit paragraaf 6 van het ontwerp."""

    AUTO = "auto"
    PARK = "park"
    BLOCK = "block"


class ItemStatus(str, enum.Enum):
    """Status van een item in de kennisbasis.

    Alleen CONFIRMED mag als bron dienen voor een automatisch antwoord.
    Dit is de mechanische invulling van "geimporteerde historie is niet
    automatisch de waarheid".
    """

    CONFIRMED = "bevestigd"
    TO_CONFIRM = "te bevestigen"
    CONFLICTING = "tegenstrijdig"
    MAYBE_STALE = "mogelijk verouderd"
    SUPERSEDED = "vervallen"

    @property
    def citable(self) -> bool:
        return self is ItemStatus.CONFIRMED


class VerificationStrength(str, enum.Enum):
    """Hoeveel hard bewijs een project levert. Zie paragraaf 8 van het ontwerp."""

    STRONG = "sterk"
    MEDIUM = "matig"
    WEAK = "zwak"

    @property
    def max_implement_iterations(self) -> int:
        return {"sterk": 5, "matig": 2, "zwak": 1}[self.value]

    @property
    def needs_pr_warning(self) -> bool:
        return self is not VerificationStrength.STRONG


class Verdict(str, enum.Enum):
    PASS = "pass"
    REVISE = "revise"
    ESCALATE = "escalate"


@dataclass(frozen=True)
class Citation:
    """Een bronverwijzing die de orkestrator zelf moet kunnen terugvinden.

    Drie schema's:
      kb:<item-id>          een item uit de kennisbasis van het project
      repo:<pad>:<regel>    een regel in de repository
      test:<naam>           een check uit de zojuist gedraaide verificatie
    """

    raw: str

    @property
    def scheme(self) -> str:
        return self.raw.split(":", 1)[0].strip().lower() if ":" in self.raw else ""

    @property
    def target(self) -> str:
        return self.raw.split(":", 1)[1].strip() if ":" in self.raw else ""


@dataclass
class Question:
    """Een openstaande vraag van de uitvoerder of de beantwoorder."""

    text: str
    why_blocking: str = ""
    options: list[str] = field(default_factory=list)
    proposed_answer: str | None = None
    proposed_default: str | None = None
    citations: list[Citation] = field(default_factory=list)
    category: str | None = None
    task_id: int | None = None

    def fingerprint(self) -> str:
        """Voor het ontdubbelen van gelijke vragen."""
        return " ".join(self.text.lower().split())


@dataclass
class TriageResult:
    outcome: Triage
    reason: str
    resolved_citations: list[str] = field(default_factory=list)
    answer: str | None = None


@dataclass
class CheckResult:
    name: str
    command: str
    exit_code: int
    output: str

    @property
    def ok(self) -> bool:
        return self.exit_code == 0


@dataclass
class VerificationResult:
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return bool(self.checks) and all(c.ok for c in self.checks)

    @property
    def failed(self) -> list[CheckResult]:
        return [c for c in self.checks if not c.ok]

    def signature(self) -> str:
        """Handtekening van het falen, voor de geen-vooruitgang-detector."""
        parts = []
        for check in self.failed:
            first_error = ""
            for line in check.output.splitlines():
                stripped = line.strip()
                if stripped:
                    first_error = stripped
                    break
            parts.append(f"{check.name}|{check.exit_code}|{first_error}")
        return "\n".join(sorted(parts))
