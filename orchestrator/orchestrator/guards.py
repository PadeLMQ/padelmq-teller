"""Deterministische controles die geen model nodig hebben."""

from __future__ import annotations

import re
from dataclasses import dataclass

# Regels die duiden op een businesswaarde in plaats van een technische constante.
_MONEY = re.compile(r"(€|\bEUR\b|\beuro\b|\bUSD\b|\$)\s?\d|(\d[\d._]*\s?(€|EUR\b|euro\b))", re.I)
_PERCENT = re.compile(r"\d+(?:[.,]\d+)?\s?%")
# Namen die duiden op een businesswaarde. Als deelwoord gematcht, zodat ook
# samenstellingen als "verzendkosten" of "maxAantalOrders" worden gevangen.
_ASSIGNMENT = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\s*[:=]")
_SUSPICIOUS_WORDS = (
    "btw", "vat", "tax", "belasting",
    "prijs", "price", "tarief", "rate", "fee", "kosten", "cost", "bedrag",
    "korting", "discount", "marge", "margin",
    "limiet", "limit", "drempel", "threshold", "quota",
    "doel", "target", "goal",
    "max", "min", "maximum", "minimum",
    "termijn", "deadline", "bewaar",
)


def _suspicious_name(text: str) -> str | None:
    for name in _ASSIGNMENT.findall(text):
        lowered = name.lower()
        for word in _SUSPICIOUS_WORDS:
            if word in lowered:
                return name
    return None


_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")

# Getallen die vrijwel nooit een businessregel zijn.
_INNOCENT = {"0", "1", "2", "-1", "100", "0.0", "1.0", "200", "404", "500", "0.5"}


@dataclass
class InventedValue:
    file: str
    line_no: int
    line: str
    value: str
    reason: str


def _added_lines(diff: str) -> list[tuple[str, int, str]]:
    """Geeft (bestand, regelnummer, tekst) voor toegevoegde regels in een unified diff."""
    out: list[tuple[str, int, str]] = []
    current = "?"
    new_line = 0
    for raw in diff.splitlines():
        if raw.startswith("+++ "):
            current = raw[4:].strip()
            if current.startswith("b/"):
                current = current[2:]
            continue
        if raw.startswith("@@"):
            m = re.search(r"\+(\d+)", raw)
            new_line = int(m.group(1)) if m else 0
            continue
        if raw.startswith("+") and not raw.startswith("+++"):
            out.append((current, new_line, raw[1:]))
            new_line += 1
        elif not raw.startswith("-"):
            new_line += 1
    return out


def detect_invented_values(diff: str, known_text: str) -> list[InventedValue]:
    """Zoekt nieuw ingevoerde harde waarden die nergens op terug te voeren zijn.

    ``known_text`` is de samengevoegde tekst van de kennisbasis, de
    taakspecificatie en de bestaande code. Staat de waarde daar, dan is ze niet
    verzonnen maar overgenomen.
    """
    findings: list[InventedValue] = []
    haystack = known_text or ""
    for path, line_no, text in _added_lines(diff):
        stripped = text.strip()
        if not stripped or stripped.startswith(("#", "//", "*", "<!--")):
            continue
        money = _MONEY.search(text)
        percent = _PERCENT.search(text)
        named = _suspicious_name(text)
        if not (money or percent or named):
            continue
        for number in _NUMBER.findall(text):
            if number in _INNOCENT:
                continue
            normalised = number.replace(",", ".")
            if number in haystack or normalised in haystack:
                continue
            if money:
                reason = "bedrag"
            elif percent:
                reason = "percentage"
            else:
                reason = f"waarde bij {named}"
            findings.append(
                InventedValue(path, line_no, stripped[:200], number, reason)
            )
            break
    return findings


class NoProgressDetector:
    """Tweemaal dezelfde falende handtekening betekent stoppen, niet nog eens proberen."""

    def __init__(self) -> None:
        self._seen: set[str] = set()

    def stuck(self, signature: str) -> bool:
        if not signature:
            return False
        if signature in self._seen:
            return True
        self._seen.add(signature)
        return False
