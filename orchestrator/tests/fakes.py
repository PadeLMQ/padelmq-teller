"""Nepobjecten voor de lus-tests. De runner kent alleen de protocollen."""

from __future__ import annotations

from pathlib import Path

from orchestrator.adapters import (
    Alternative, AnswerResult, ExecutionResult, ReviewResult, Usage,
)
from orchestrator.models import Question, Verdict


class FakeExecutor:
    """Voert een lijst met stappen uit; elke stap mag het werkblad wijzigen."""

    def __init__(self, steps: list[dict]):
        self.steps = list(steps)
        self.calls: list[str] = []

    def execute(self, *, prompt: str, cwd: Path, session_id: str | None = None):
        self.calls.append(prompt)
        step = self.steps.pop(0) if self.steps else {}
        for name, content in (step.get("write") or {}).items():
            target = Path(cwd) / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        for name in step.get("delete") or []:
            target = Path(cwd) / name
            if target.exists():
                target.unlink()
        return ExecutionResult(
            summary=step.get("summary", "gedaan"),
            session_id="sessie-1",
            open_questions=step.get("questions", []),
            assumptions_made=step.get("assumptions", []),
            alternative=step.get("alternative", Alternative()),
            usage=Usage("executor-test", 1000, 500),
        )


class FakeReviewer:
    def __init__(self, answers: list[Question] | None = None,
                 reviews: list[ReviewResult] | None = None):
        self.answers = answers or []
        self.reviews = list(reviews or [])
        self.answer_calls = 0
        self.review_calls = 0
        self.last_diff = ""
        self.last_context = ""

    def answer(self, *, questions, context, previous_response_id=None):
        self.answer_calls += 1
        self.last_context = context
        return AnswerResult(
            questions=self.answers or questions,
            response_id="resp-1",
            usage=Usage("reviewer-test", 800, 200),
        )

    def review(self, *, diff, verification_summary, acceptance, context,
               previous_response_id=None):
        self.review_calls += 1
        self.last_diff = diff
        result = self.reviews.pop(0) if self.reviews else ReviewResult(verdict=Verdict.PASS)
        result.usage = Usage("reviewer-test", 1200, 400)
        result.response_id = "resp-2"
        return result
