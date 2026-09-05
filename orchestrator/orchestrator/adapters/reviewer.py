"""Reviewer: de OpenAI Responses API, in twee rollen.

- ``answer``  beantwoordt openstaande vragen uit de kennisbasis, met verplichte
  bronvermelding. De triage beslist daarna of het antwoord gebruikt mag worden;
  deze adapter beslist dat nooit zelf.
- ``review``  beoordeelt een diff die de harde verificatie al gehaald heeft.

Gespreksgeheugen per project loopt via ``previous_response_id``: elk project
heeft zijn eigen keten, er bestaat geen gedeelde keten.

TE VERIFIEREN VOOR DE EERSTE ECHTE RUN: de exacte parameternamen van de
Responses API in de geinstalleerde openai-versie. ``orchestrator doctor``
doet daarvoor een minimale echte aanroep. Er wordt hier bewust niets stil
opgevangen: gaat het mis, dan hoor je het meteen.
"""

from __future__ import annotations

import json
from typing import Any

from ..models import Citation, Question, Verdict
from . import Alternative, AnswerResult, Finding, ReviewResult, Usage

ANSWER_SYSTEM = """
Je bent de kennisdrager van één softwareproject. Je beantwoordt vragen van de
ontwikkelagent uitsluitend op basis van de meegeleverde projectkennisbasis.

Harde regels:
- Beantwoord een vraag alleen als je het antwoord kunt onderbouwen met een bron
  uit de kennisbasis, de repository of een testuitslag. Zet die bron in
  citations, in de vorm kb:<item-id>, repo:<pad>:<regel> of test:<naam>.
- Verzin nooit een businessregel om de vraag te kunnen beantwoorden. Weet je het
  niet, laat answer dan leeg. Dat is een goed antwoord, geen falen.
- Een item met een andere status dan "bevestigd" is geen geldige bron.
- Vul altijd better_alternative in; zie je niets beters, zet recommendation op "geen".
"""

REVIEW_SYSTEM = """
Je beoordeelt een wijziging die de harde verificatie al gehaald heeft.

Harde regels:
- Je kunt een testuitslag niet tegenspreken en niet ongeldig verklaren.
- Geef alleen "pass" als elk acceptatiecriterium aantoonbaar gehaald is.
- Betwist ook de taak zelf: is dit het juiste probleem, bestaat er een
  eenvoudiger oplossing, maakt bestaande code dit overbodig.
- Vul altijd better_alternative in; zie je niets beters, zet recommendation op "geen".
"""

_ALTERNATIVE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["proposal", "why_better", "evidence", "cost_of_switching", "recommendation"],
    "properties": {
        "proposal": {"type": "string"},
        "why_better": {"type": "string"},
        "evidence": {"type": "string"},
        "cost_of_switching": {"type": "string"},
        "recommendation": {"type": "string"},
    },
}

ANSWER_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["answers", "better_alternative"],
    "properties": {
        "answers": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["question", "answer", "citations", "category",
                             "proposed_default", "options"],
                "properties": {
                    "question": {"type": "string"},
                    "answer": {"type": "string"},
                    "citations": {"type": "array", "items": {"type": "string"}},
                    "category": {"type": "string"},
                    "proposed_default": {"type": "string"},
                    "options": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
        "better_alternative": _ALTERNATIVE_SCHEMA,
    },
}

REVIEW_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["verdict", "findings", "next_instruction", "open_questions",
                 "acceptance_met", "acceptance_missing", "better_alternative"],
    "properties": {
        "verdict": {"type": "string", "enum": ["pass", "revise", "escalate"]},
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["severity", "file", "issue", "fix"],
                "properties": {
                    "severity": {"type": "string", "enum": ["blocker", "major", "minor"]},
                    "file": {"type": "string"},
                    "issue": {"type": "string"},
                    "fix": {"type": "string"},
                },
            },
        },
        "next_instruction": {"type": "string"},
        "open_questions": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["question", "why_blocking", "category"],
                "properties": {
                    "question": {"type": "string"},
                    "why_blocking": {"type": "string"},
                    "category": {"type": "string"},
                },
            },
        },
        "acceptance_met": {"type": "array", "items": {"type": "string"}},
        "acceptance_missing": {"type": "array", "items": {"type": "string"}},
        "better_alternative": _ALTERNATIVE_SCHEMA,
    },
}


def _alternative(raw: dict) -> Alternative:
    raw = raw or {}
    return Alternative(
        proposal=raw.get("proposal", ""),
        why_better=raw.get("why_better", ""),
        evidence=raw.get("evidence", ""),
        cost_of_switching=raw.get("cost_of_switching", ""),
        recommendation=raw.get("recommendation", "geen"),
    )



def _cached_tokens(usage) -> int:
    """Cachetokens uit input_tokens_details.

    De Responses-API zet ze in een subobject; ontbreekt dat, dan is er niets
    uit de cache gekomen en is 0 het juiste antwoord, geen aanname.
    """
    details = getattr(usage, "input_tokens_details", None)
    if details is None:
        return 0
    return int(getattr(details, "cached_tokens", 0) or 0)

class OpenAIReviewer:
    def __init__(self, model: str, client: Any | None = None):
        self.model = model
        self._client = client

    @property
    def client(self) -> Any:
        if self._client is None:
            try:
                from openai import OpenAI  # lazy: de kern draait zonder deze afhankelijkheid
            except ImportError as exc:  # pragma: no cover
                raise RuntimeError(
                    "pakket 'openai' ontbreekt; installeer het of draai met een andere reviewer"
                ) from exc
            self._client = OpenAI()
        return self._client

    def _call(self, system: str, user: str, schema: dict, name: str,
              previous_response_id: str | None) -> tuple[dict, str | None, Usage]:
        response = self.client.responses.create(
            model=self.model,
            previous_response_id=previous_response_id,
            input=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": name,
                    "schema": schema,
                    "strict": True,
                }
            },
        )
        text = getattr(response, "output_text", None)
        if not text:
            raise RuntimeError("reviewer gaf geen tekstuitvoer terug")
        usage = getattr(response, "usage", None)
        return (
            json.loads(text),
            getattr(response, "id", None),
            Usage(
                model=self.model,
                tokens_in=int(getattr(usage, "input_tokens", 0) or 0),
                tokens_out=int(getattr(usage, "output_tokens", 0) or 0),
                cached_in=_cached_tokens(usage),
            ),
        )

    # -- rol 1: beantwoorder ---------------------------------------------
    def answer(self, *, questions: list[Question], context: str,
               previous_response_id: str | None = None) -> AnswerResult:
        listing = "\n".join(
            f"{i + 1}. {q.text} (waarom het blokkeert: {q.why_blocking or 'niet vermeld'})"
            for i, q in enumerate(questions)
        )
        user = (
            f"Projectkennisbasis:\n{context}\n\n"
            f"Openstaande vragen:\n{listing}\n\n"
            "Beantwoord alleen wat je met een bron kunt onderbouwen."
        )
        payload, response_id, usage = self._call(
            ANSWER_SYSTEM, user, ANSWER_SCHEMA, "answers", previous_response_id
        )
        answered: list[Question] = []
        by_text = {q.text.strip().lower(): q for q in questions}
        for item in payload.get("answers", []):
            original = by_text.get(item.get("question", "").strip().lower())
            answered.append(
                Question(
                    text=item.get("question", ""),
                    why_blocking=(original.why_blocking if original else ""),
                    options=list(item.get("options") or (original.options if original else [])),
                    proposed_answer=item.get("answer") or None,
                    proposed_default=item.get("proposed_default") or None,
                    citations=[Citation(c) for c in item.get("citations") or []],
                    category=item.get("category") or (original.category if original else None),
                    task_id=original.task_id if original else None,
                )
            )
        return AnswerResult(questions=answered, response_id=response_id, usage=usage)

    # -- rol 2: beoordelaar ----------------------------------------------
    def review(self, *, diff: str, verification_summary: str, acceptance: list[str],
               context: str, previous_response_id: str | None = None) -> ReviewResult:
        user = (
            f"Projectkennisbasis:\n{context}\n\n"
            f"Acceptatiecriteria:\n" + "\n".join(f"- {c}" for c in acceptance) + "\n\n"
            f"Uitslag van de harde verificatie (feit, niet ter discussie):\n"
            f"{verification_summary}\n\n"
            f"Diff:\n{diff}"
        )
        payload, response_id, usage = self._call(
            REVIEW_SYSTEM, user, REVIEW_SCHEMA, "review", previous_response_id
        )
        return ReviewResult(
            verdict=Verdict(payload.get("verdict", "escalate")),
            findings=[
                Finding(
                    severity=f.get("severity", "minor"),
                    file=f.get("file", ""),
                    issue=f.get("issue", ""),
                    fix=f.get("fix", ""),
                )
                for f in payload.get("findings", [])
            ],
            next_instruction=payload.get("next_instruction", ""),
            open_questions=[
                Question(
                    text=q.get("question", ""),
                    why_blocking=q.get("why_blocking", ""),
                    category=q.get("category") or None,
                )
                for q in payload.get("open_questions", [])
                if q.get("question")
            ],
            acceptance_met=list(payload.get("acceptance_met") or []),
            acceptance_missing=list(payload.get("acceptance_missing") or []),
            alternative=_alternative(payload.get("better_alternative")),
            response_id=response_id,
            usage=usage,
        )


def validate_verdict(review: ReviewResult, acceptance: list[str]) -> ReviewResult:
    """De beoordelaar mag de feiten niet tegenspreken.

    Een 'pass' terwijl er meetbaar criteria openstaan, wordt verworpen en
    omgezet naar 'revise'. Dat wordt geteld als reviewerfout.
    """
    if review.verdict is Verdict.PASS and review.acceptance_missing:
        review.verdict = Verdict.REVISE
        review.next_instruction = (
            "Verdict 'pass' verworpen: deze acceptatiecriteria zijn niet gehaald: "
            + ", ".join(review.acceptance_missing)
            + ". "
            + review.next_instruction
        )
    blockers = [f for f in review.findings if f.severity == "blocker"]
    if review.verdict is Verdict.PASS and blockers:
        review.verdict = Verdict.REVISE
        review.next_instruction = (
            "Verdict 'pass' verworpen: er staan blokkerende bevindingen open. "
            + review.next_instruction
        )
    return review
