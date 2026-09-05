"""Wat de mens te zien krijgt: de PR-omschrijving en het dagrapport."""

from __future__ import annotations

import json
from datetime import date

from .adapters import ReviewResult
from .db import Database, ProjectScope
from .models import Question, VerificationResult
from .projects import Project
from .redact import redact_text


def pr_body(
    *,
    project: Project,
    task,
    acceptance: list[str],
    verification: VerificationResult,
    review: ReviewResult | None,
    auto_answers: list[Question],
    parked: list[str],
) -> str:
    lines: list[str] = []
    lines.append("## Wat er gewijzigd is en waarom")
    lines.append(task["title"])
    if task["spec"]:
        lines.append("")
        lines.append(task["spec"])

    lines.append("\n## Acceptatiecriteria")
    met = set(review.acceptance_met) if review else set()
    for criterion in acceptance:
        mark = "x" if criterion in met or review is None else " "
        lines.append(f"- [{mark}] {criterion}")

    lines.append("\n## Verificatie")
    for check in verification.checks:
        lines.append(f"- {check.name}: {'geslaagd' if check.ok else 'GEFAALD'}")
    if not verification.checks:
        lines.append("- geen geautomatiseerde checks in dit project")
    lines.append(
        f"\nVerificatiesterkte van dit project: **{project.strength.value}**."
    )
    if project.strength.needs_pr_warning:
        lines.append(
            "> Let op: er is beperkt hard bewijs voor deze wijziging. "
            "Lees de diff met extra aandacht."
        )

    lines.append("\n## Vragen die automatisch beantwoord zijn")
    if auto_answers:
        for question in auto_answers:
            bronnen = ", ".join(c.raw for c in question.citations) or "onbekend"
            lines.append(f"- {question.text}\n  - antwoord: {question.proposed_answer}")
            lines.append(f"  - bron: {bronnen}")
    else:
        lines.append("- geen")

    lines.append("\n## Resterende risico's")
    if review and review.findings:
        for finding in review.findings:
            lines.append(f"- [{finding.severity}] {finding.file}: {finding.issue}")
    else:
        lines.append("- geen gemeld door de beoordelaar")

    lines.append("\n## Geparkeerde vragen die hieraan raken")
    lines.extend([f"- {p}" for p in parked] or ["- geen"])

    if review and review.alternative.present:
        lines.append("\n## Voorgesteld beter alternatief")
        lines.append(f"**{review.alternative.proposal}**")
        lines.append(f"- waarom beter: {review.alternative.why_better}")
        lines.append(f"- bewijs: {review.alternative.evidence}")
        lines.append(f"- kosten van wisselen: {review.alternative.cost_of_switching}")
        lines.append(f"- aanbeveling: {review.alternative.recommendation}")

    lines.append(
        "\n---\n_Voorbereid door de orkestrator. Er wordt nooit automatisch gemerged._"
    )
    return redact_text("\n".join(lines), project.redact_patterns)


def daily_digest(db: Database, slugs: list[str], day: str | None = None) -> str:
    day = day or date.today().isoformat()
    blocks: list[str] = [f"# Dagrapport {day}", ""]
    total_cost = 0.0

    for slug in slugs:
        scope = db.scope(slug)
        parked = scope.pending_questions("park")
        blocked = scope.pending_questions("block")
        done = [t for t in scope.tasks() if t["status"] in ("done", "pr_open")]
        spend = scope.spend_today(day)
        total_cost += spend

        blocks.append(f"## {slug}")
        blocks.append(f"Kosten vandaag: €{spend:.2f}")

        blocks.append("\n**Geparkeerde vragen**")
        if parked:
            for row in parked:
                options = json.loads(row["options"] or "[]")
                blocks.append(f"- {row['text']}")
                if options:
                    blocks.append("  opties: " + " · ".join(options))
                if row["proposed"]:
                    blocks.append(f"  voorstel: {row['proposed']}")
        else:
            blocks.append("- geen")

        blocks.append("\n**Nog openstaande blokkades**")
        if blocked:
            for row in blocked:
                issue = f" (issue #{row['issue_number']})" if row["issue_number"] else ""
                wacht = (" — wacht op je bevestiging"
                         if row["status"] == "awaiting_confirmation" else "")
                blocks.append(f"- {row['text']}{issue}{wacht}")
        else:
            blocks.append("- geen")

        blocks.append("\n**Afgerond / klaar voor review**")
        blocks.extend([f"- {t['title']} ({t['status']})" for t in done] or ["- niets"])
        blocks.append("")

    blocks.append(f"\n**Totale kosten vandaag: €{total_cost:.2f}**")
    blocks.append(
        "\n_Antwoord op geparkeerde vragen door ze hier te beantwoorden of het"
        " bijbehorende issue te beantwoorden._"
    )
    return "\n".join(blocks)
