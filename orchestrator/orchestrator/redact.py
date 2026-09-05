"""Geheimen gaan nooit de lus in.

Wordt onvoorwaardelijk toegepast op alles wat naar de reviewer gaat en op alles
wat in een issue, PR of logboek belandt.
"""

from __future__ import annotations

import re

_PATTERNS = [
    # Toewijzingen aan een geheim uitziende naam.
    (re.compile(
        r"((?:api[_-]?key|secret|token|password|passwd|client[_-]?secret|access[_-]?token"
        r"|private[_-]?key)\w*\s*[:=]\s*)([\"']?)([^\s\"']{6,})",
        re.I), r"\1\2<geredigeerd>"),
    # Bekende sleutelvormen.
    (re.compile(r"\bshpat_[A-Za-z0-9]+"), "<geredigeerd:shopify-token>"),
    (re.compile(r"\bsk-[A-Za-z0-9_\-]{16,}"), "<geredigeerd:api-sleutel>"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{16,}"), "<geredigeerd:github-token>"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"),
     "<geredigeerd:private-key>"),
]

# Bestanden waarvan de inhoud nooit meegestuurd wordt.
_FORBIDDEN_FILES = re.compile(r"(^|/)(\.env(\.|$)|.*\.pem$|.*\.key$|secrets?\.(ya?ml|json))", re.I)


def redact_text(text: str, extra_patterns: list[str] | None = None) -> str:
    out = text
    for pattern, replacement in _PATTERNS:
        out = pattern.sub(replacement, out)
    for raw in extra_patterns or []:
        try:
            out = re.sub(raw, "<geredigeerd>", out, flags=re.I)
        except re.error:
            continue
    return out


def redact_diff(diff: str, extra_patterns: list[str] | None = None) -> str:
    """Verwijdert hele bestandsblokken voor verboden bestanden, redigeert de rest."""
    blocks: list[str] = []
    current: list[str] = []
    drop = False

    def flush() -> None:
        if current and not drop:
            blocks.append("\n".join(current))
        elif current and drop:
            header = current[0]
            blocks.append(f"{header}\n<inhoud weggelaten: bestand met geheimen>")

    for line in diff.splitlines():
        if line.startswith("diff --git "):
            flush()
            current = [line]
            drop = bool(_FORBIDDEN_FILES.search(line))
            continue
        current.append(line)
    flush()
    return redact_text("\n".join(blocks) if blocks else diff, extra_patterns)
