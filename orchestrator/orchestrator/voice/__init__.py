"""Gesproken menselijke tussenkomst.

Spraak is geen aparte werkstroom maar een kanaal op dezelfde antwoordmachine
(``answer_session.py``). Deze module levert precies twee handelingen voor het
transport — welke vraag staat open, en hier is mijn antwoord — plus de
protocollen voor spraakherkenning, spraaksynthese en het lezen van een open
antwoord.

Het transport zelf (Siri-shortcut, telefoon-app, Telegram) zit hier bewust
niet in. Het praat met deze twee handelingen en verder met niets.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from ..answer_session import Act, AnswerFlow, Interpreter, Step
from ..answers import record_human_decision
from ..db import ProjectScope
from ..projects import Project
from ..redact import redact_text

CHANNEL = "voice"


@dataclass
class Transcript:
    text: str
    confidence: float | None = None


class SpeechToText(Protocol):
    def transcribe(self, audio: bytes, *, hint: str = "") -> Transcript: ...


class TextToSpeech(Protocol):
    def synthesize(self, text: str) -> bytes: ...


@dataclass
class VoicePrompt:
    """Wat er voorgelezen moet worden."""

    session_id: int
    project: str
    task_id: int | None
    question_id: int
    text: str
    options: list[str] = field(default_factory=list)


@dataclass
class VoiceReply:
    """Wat er na jouw antwoord moet gebeuren."""

    speak: str
    finished: bool
    applied: bool = False
    decision_id: str | None = None
    resumed_tasks: int = 0
    clarity: str = ""
    reason: str = ""


class VoiceQueue:
    """De twee handelingen die een spraaktransport nodig heeft."""

    def __init__(self, scope: ProjectScope, project: Project,
                 interpreter: Interpreter | None = None):
        self.scope = scope
        self.project = project
        self.flow = AnswerFlow(scope, CHANNEL, interpreter=interpreter)

    # -- 1. wat staat er open ---------------------------------------------
    def next_question(self) -> VoicePrompt | None:
        """De oudste openstaande blokkade van dit project, klaar om voor te lezen."""
        import json

        blockades = self.scope.pending_questions("block")
        for row in blockades:
            session = self.scope.open_answer_session(int(row["id"]))
            if session is not None and session["state"] in (
                "resolved", "returned_to_block"
            ):
                continue
            options = json.loads(row["options"] or "[]")
            # Geheimen worden nooit hardop voorgelezen.
            gesproken = redact_text(row["text"], self.project.redact_patterns)
            if options:
                gesproken += " De opties zijn: " + ", ".join(
                    redact_text(o, self.project.redact_patterns) for o in options
                ) + "."
            session_id = self.flow.open(int(row["id"]), gesproken, row["task_id"])
            return VoicePrompt(
                session_id=session_id,
                project=self.scope.slug,
                task_id=row["task_id"],
                question_id=int(row["id"]),
                text=gesproken,
                options=options,
            )
        return None

    # -- 2. hier is mijn antwoord ------------------------------------------
    def submit(self, session_id: int, transcript: str,
               confidence: float | None = None) -> VoiceReply:
        step: Step = self.flow.submit(session_id, transcript, confidence)

        if step.act is Act.APPLY:
            session = self.scope.answer_session(session_id)
            question_id = int(session["question_id"])
            wachtend = len(self.scope.tasks_waiting_on(question_id))
            decision_id = record_human_decision(
                scope=self.scope,
                project=self.project,
                question_id=question_id,
                answer=step.text,
                source=f"gesproken antwoord, sessie #{session_id}",
            )
            self.scope.set_answer_session(session_id, decision_id=decision_id)
            return VoiceReply(
                speak=(
                    f"Vastgelegd. "
                    + (f"Ik hervat {wachtend} taak." if wachtend == 1
                       else f"Ik hervat {wachtend} taken." if wachtend else
                       "Er stond geen taak op te wachten.")
                ),
                finished=True, applied=True, decision_id=decision_id,
                resumed_tasks=wachtend,
                clarity=step.clarity.value if step.clarity else "",
                reason=step.reason,
            )

        return VoiceReply(
            speak=step.text,
            finished=step.act is Act.KEEP_BLOCKED,
            clarity=step.clarity.value if step.clarity else "",
            reason=step.reason,
        )

    # -- audit --------------------------------------------------------------
    def audit(self, session_id: int) -> list[dict]:
        return self.flow.audit(session_id)
