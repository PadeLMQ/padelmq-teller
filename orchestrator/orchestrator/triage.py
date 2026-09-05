"""De beslislaag AUTO / PARK / BLOCK. Het hart van "nooit gokken".

De poort is verifieerbaarheid, niet zelfvertrouwen: een antwoord mag alleen
automatisch gebruikt worden als het naar een bron verwijst die de orkestrator
zelf kan terugvinden en die de status 'bevestigd' heeft.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .knowledge import KnowledgeStore
from .models import Citation, Question, Triage, TriageResult, VerificationResult

# Categorieen die nooit automatisch beantwoord mogen worden, ongeacht bron of
# zelfvertrouwen. Ontwerp, paragraaf 6.3.
FORBIDDEN_CATEGORIES = {
    "geld", "prijs", "prijzen", "korting", "marge",
    "btw", "fiscaal", "belasting",
    "juridisch", "contract",
    "persoonsgegevens", "klantgegevens", "privacy", "bewaartermijn",
    "beveiliging", "security", "toegang", "rechten",
    "datamodel", "migratie", "schema",
    "klantzichtbaar", "publiek",
}

# Woorden die in de vraagtekst zelf al op een verboden categorie wijzen, ook als
# het model geen categorie meegaf. Bewust ruim: bij twijfel geen AUTO.
_FORBIDDEN_HINTS = re.compile(
    r"\b(btw|vat|belasting|fiscaal|prijs|prijzen|tarief|korting|marge|bedrag|"
    r"euro|factuur|contract|juridisch|aansprakelijk|persoonsgegeven|klantgegeven|"
    r"gdpr|avg|bewaartermijn|wachtwoord|token|secret|toegangsrecht|migratie|"
    r"datamodel|schema)\b",
    re.I,
)


@dataclass
class TriageContext:
    knowledge: KnowledgeStore
    repo_root: Path
    verification: VerificationResult | None = None
    has_independent_work: bool = False


class TriageEngine:
    def __init__(self, context: TriageContext):
        self.ctx = context

    # -- bronnen controleren ---------------------------------------------
    def resolve(self, citation: Citation) -> tuple[bool, str]:
        """Bestaat deze bron, en mag ze gebruikt worden? (ok, toelichting)"""
        scheme, target = citation.scheme, citation.target
        if scheme == "kb":
            item = self.ctx.knowledge.get(target)
            if item is None:
                return False, f"kennisbasis-item {target!r} bestaat niet"
            if not item.citable:
                return False, (
                    f"{target} heeft status {item.status.value!r}; "
                    "alleen 'bevestigd' telt als bron"
                )
            return True, f"{target} ({item.title})"
        if scheme == "repo":
            path_part, _, line_part = target.rpartition(":")
            if not path_part:
                path_part, line_part = target, ""
            candidate = (self.ctx.repo_root / path_part).resolve()
            try:
                candidate.relative_to(self.ctx.repo_root.resolve())
            except ValueError:
                return False, f"pad {path_part!r} valt buiten de projectmap"
            if not candidate.is_file():
                return False, f"bestand {path_part!r} bestaat niet"
            if line_part.isdigit():
                total = len(candidate.read_text(encoding="utf-8", errors="replace").splitlines())
                if not 1 <= int(line_part) <= total:
                    return False, f"{path_part} heeft geen regel {line_part}"
            return True, f"{path_part}:{line_part}" if line_part else path_part
        if scheme == "test":
            if self.ctx.verification is None:
                return False, "er is geen verificatieresultaat om naar te verwijzen"
            names = {c.name for c in self.ctx.verification.checks}
            if target not in names:
                return False, f"check {target!r} is niet gedraaid"
            return True, f"check {target}"
        return False, f"onbekend bronschema {citation.raw!r}"

    # -- categoriepoort ---------------------------------------------------
    def is_forbidden(self, question: Question) -> str | None:
        category = (question.category or "").strip().lower()
        if category in FORBIDDEN_CATEGORIES:
            return f"categorie {category!r} mag nooit automatisch beantwoord worden"
        hit = _FORBIDDEN_HINTS.search(question.text)
        if hit:
            return (
                f"de vraag raakt {hit.group(0).lower()!r}; dat valt onder de categorieen "
                "die nooit automatisch beantwoord worden"
            )
        haystack = question.text.lower()
        for forbidden in self.ctx.knowledge.forbidden_topics():
            words = [w for w in re.split(r"\W+", forbidden) if len(w) > 4]
            if words and sum(1 for w in words if w in haystack) >= 2:
                return "de vraag raakt een regel uit verboden.md van dit project"
        return None

    # -- de beslissing ----------------------------------------------------
    def decide(self, question: Question) -> TriageResult:
        forbidden = self.is_forbidden(question)

        resolved: list[str] = []
        problems: list[str] = []
        for citation in question.citations:
            ok, note = self.resolve(citation)
            (resolved if ok else problems).append(note)

        answer = (question.proposed_answer or "").strip()

        if forbidden:
            return self._park_or_block(question, forbidden, resolved)
        if not answer:
            return self._park_or_block(question, "geen voorgesteld antwoord", resolved)
        if not question.citations:
            return self._park_or_block(
                question, "antwoord zonder bronverwijzing", resolved
            )
        if not resolved:
            return self._park_or_block(
                question,
                "geen enkele bron kon worden teruggevonden: " + "; ".join(problems),
                resolved,
            )
        if problems:
            # Twijfel tussen AUTO en PARK gaat naar PARK.
            return self._park_or_block(
                question,
                "niet elke bron klopt: " + "; ".join(problems),
                resolved,
            )
        return TriageResult(
            outcome=Triage.AUTO,
            reason="beantwoord op basis van " + ", ".join(resolved),
            resolved_citations=resolved,
            answer=answer,
        )

    def _park_or_block(
        self, question: Question, reason: str, resolved: list[str]
    ) -> TriageResult:
        """PARK versus BLOCK hangt af van of er veilig verder gewerkt kan worden."""
        if self.ctx.has_independent_work:
            return TriageResult(Triage.PARK, reason, resolved)
        return TriageResult(
            Triage.BLOCK,
            reason + " — en er is geen onafhankelijk werk over in dit project",
            resolved,
        )
