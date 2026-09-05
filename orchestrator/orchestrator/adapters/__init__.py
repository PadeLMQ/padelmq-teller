"""Adapters naar de modellen. De runner kent alleen de protocollen hieronder,
zodat tests met eenvoudige nepobjecten kunnen draaien.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from ..models import Question, Verdict


@dataclass
class Usage:
    model: str
    tokens_in: int = 0
    tokens_out: int = 0
    cached_in: int = 0


@dataclass
class Alternative:
    """Verplichte tegenspraak. 'geen' moet expliciet ingevuld worden."""

    proposal: str = ""
    why_better: str = ""
    evidence: str = ""
    cost_of_switching: str = ""
    recommendation: str = "geen"  # nu doen | later | verworpen omdat ... | geen

    @property
    def present(self) -> bool:
        return bool(self.proposal.strip()) and self.recommendation.strip().lower() != "geen"


@dataclass
class ExecutionResult:
    summary: str = ""
    session_id: str | None = None
    open_questions: list[Question] = field(default_factory=list)
    assumptions_made: list[str] = field(default_factory=list)
    alternative: Alternative = field(default_factory=Alternative)
    usage: Usage | None = None
    raw: dict = field(default_factory=dict)


@dataclass
class Finding:
    severity: str
    file: str
    issue: str
    fix: str = ""


@dataclass
class ReviewResult:
    verdict: Verdict = Verdict.ESCALATE
    findings: list[Finding] = field(default_factory=list)
    next_instruction: str = ""
    open_questions: list[Question] = field(default_factory=list)
    acceptance_met: list[str] = field(default_factory=list)
    acceptance_missing: list[str] = field(default_factory=list)
    alternative: Alternative = field(default_factory=Alternative)
    response_id: str | None = None
    usage: Usage | None = None


@dataclass
class AnswerResult:
    """Wat de beantwoorder teruggeeft, vóór de triage erover beslist."""

    questions: list[Question] = field(default_factory=list)
    response_id: str | None = None
    usage: Usage | None = None


class Executor(Protocol):
    def execute(self, *, prompt: str, cwd, session_id: str | None) -> ExecutionResult: ...


class Reviewer(Protocol):
    def answer(self, *, questions: list[Question], context: str,
               previous_response_id: str | None) -> AnswerResult: ...

    def review(self, *, diff: str, verification_summary: str, acceptance: list[str],
               context: str, previous_response_id: str | None) -> ReviewResult: ...
