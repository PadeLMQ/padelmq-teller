"""Hergebruik van reviewerantwoorden.

De regel: dezelfde inhoudelijke vraag met dezelfde relevante context wordt niet
tweemaal betaald. De sleutel bevat daarom alles wat het antwoord materieel kan
beïnvloeden. Verandert er iets aan de vraag, de bevestigde kennis, de code, de
acceptatiecriteria of het model, dan verandert de sleutel en wordt er gewoon
opnieuw gevraagd. Er wordt nooit blind hergebruikt.

Wat hier bewaard wordt is het **ruwe antwoord van de reviewer**, niet de
beslissing. De triage draait bij een treffer gewoon opnieuw, met de actuele
kennisbasis. De veiligheidspoort wordt dus nooit overgeslagen.
"""

from __future__ import annotations

import hashlib
import json

from .adapters import (
    Alternative, AnswerResult, Finding, ReviewResult, Reviewer, Usage,
)
from .db import ProjectScope
from .models import Citation, Question, Verdict

# Verhoog dit zodra de vorm van een antwoord verandert; oude regels vervallen dan.
SCHEMA_VERSIE = "1"


def _sleutel(soort: str, model: str, delen: list[str]) -> str:
    ruw = "␟".join([SCHEMA_VERSIE, soort, model, *delen])
    return hashlib.sha256(ruw.encode("utf-8")).hexdigest()


def _normaliseer(tekst: str) -> str:
    return " ".join((tekst or "").lower().split())


# ---------- serialiseren ----------------------------------------------------
def _vraag_naar_dict(q: Question) -> dict:
    return {
        "text": q.text, "why_blocking": q.why_blocking, "options": list(q.options),
        "proposed_answer": q.proposed_answer, "proposed_default": q.proposed_default,
        "citations": [c.raw for c in q.citations], "category": q.category,
    }


def _dict_naar_vraag(d: dict) -> Question:
    return Question(
        text=d.get("text", ""), why_blocking=d.get("why_blocking", ""),
        options=list(d.get("options") or []),
        proposed_answer=d.get("proposed_answer"),
        proposed_default=d.get("proposed_default"),
        citations=[Citation(c) for c in d.get("citations") or []],
        category=d.get("category"),
    )


def _alt_naar_dict(a: Alternative) -> dict:
    return {
        "proposal": a.proposal, "why_better": a.why_better, "evidence": a.evidence,
        "cost_of_switching": a.cost_of_switching, "recommendation": a.recommendation,
    }


def _dict_naar_alt(d: dict) -> Alternative:
    return Alternative(**{k: d.get(k, "") for k in
                          ("proposal", "why_better", "evidence", "cost_of_switching")},
                       recommendation=d.get("recommendation", "geen"))


class ReviewCache(Reviewer):
    """Omhulsel om een reviewer. Zelfde interface, betaalt alleen wat nieuw is."""

    def __init__(self, inner: Reviewer, scope: ProjectScope, model: str, on_hit=None):
        self.inner = inner
        self.scope = scope
        self.model = model
        self.on_hit = on_hit or (lambda soort, sleutel, usage: None)
        self.treffers = 0
        self.missers = 0

    # ---------- beantwoorden ----------
    def answer(self, *, questions: list[Question], context: str,
               previous_response_id: str | None = None) -> AnswerResult:
        sleutel = _sleutel("answer", self.model, [
            "|".join(sorted(_normaliseer(q.text) for q in questions)),
            hashlib.sha256(context.encode("utf-8")).hexdigest(),
        ])
        bewaard = self.scope.cache_get("answer", sleutel)
        if bewaard is not None:
            self.treffers += 1
            data = json.loads(bewaard["resultaat"])
            usage = Usage(self.model, int(bewaard["tokens_in"]), int(bewaard["tokens_out"]))
            self.on_hit("answer", sleutel, usage)
            return AnswerResult(
                questions=[_dict_naar_vraag(q) for q in data["questions"]],
                response_id=None,   # geen nieuwe beurt: de keten mist niets nieuws
                usage=None,         # niets betaald, dus niets te boeken
            )

        self.missers += 1
        result = self.inner.answer(
            questions=questions, context=context, previous_response_id=previous_response_id
        )
        self.scope.cache_put(
            "answer", sleutel, self.model,
            json.dumps({"questions": [_vraag_naar_dict(q) for q in result.questions]},
                       ensure_ascii=False),
            tokens_in=result.usage.tokens_in if result.usage else 0,
            tokens_out=result.usage.tokens_out if result.usage else 0,
        )
        return result

    # ---------- beoordelen ----------
    def review(self, *, diff: str, verification_summary: str, acceptance: list[str],
               context: str, previous_response_id: str | None = None) -> ReviewResult:
        sleutel = _sleutel("review", self.model, [
            hashlib.sha256(diff.encode("utf-8")).hexdigest(),
            _normaliseer(verification_summary),
            "|".join(sorted(_normaliseer(a) for a in acceptance)),
            hashlib.sha256(context.encode("utf-8")).hexdigest(),
        ])
        bewaard = self.scope.cache_get("review", sleutel)
        if bewaard is not None:
            self.treffers += 1
            d = json.loads(bewaard["resultaat"])
            usage = Usage(self.model, int(bewaard["tokens_in"]), int(bewaard["tokens_out"]))
            self.on_hit("review", sleutel, usage)
            return ReviewResult(
                verdict=Verdict(d["verdict"]),
                findings=[Finding(**f) for f in d.get("findings", [])],
                next_instruction=d.get("next_instruction", ""),
                open_questions=[_dict_naar_vraag(q) for q in d.get("open_questions", [])],
                acceptance_met=list(d.get("acceptance_met") or []),
                acceptance_missing=list(d.get("acceptance_missing") or []),
                alternative=_dict_naar_alt(d.get("alternative") or {}),
                response_id=None,
                usage=None,
            )

        self.missers += 1
        result = self.inner.review(
            diff=diff, verification_summary=verification_summary, acceptance=acceptance,
            context=context, previous_response_id=previous_response_id,
        )
        self.scope.cache_put(
            "review", sleutel, self.model,
            json.dumps({
                "verdict": result.verdict.value,
                "findings": [{"severity": f.severity, "file": f.file, "issue": f.issue,
                              "fix": f.fix} for f in result.findings],
                "next_instruction": result.next_instruction,
                "open_questions": [_vraag_naar_dict(q) for q in result.open_questions],
                "acceptance_met": result.acceptance_met,
                "acceptance_missing": result.acceptance_missing,
                "alternative": _alt_naar_dict(result.alternative),
            }, ensure_ascii=False),
            tokens_in=result.usage.tokens_in if result.usage else 0,
            tokens_out=result.usage.tokens_out if result.usage else 0,
        )
        return result
