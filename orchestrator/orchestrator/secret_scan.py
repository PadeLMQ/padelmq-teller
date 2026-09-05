"""Scant bestanden op geheimen vóór ze in git belanden.

Bewust conservatief: liever een vals alarm dat je wegwuift dan een token dat
in de geschiedenis van een repository terechtkomt, want daar krijg je hem
nooit meer helemaal uit.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("Shopify-token", re.compile(r"\bshpat_[A-Za-z0-9]{8,}")),
    ("Shopify-app-secret", re.compile(r"\bshpss_[A-Za-z0-9]{8,}")),
    ("OpenAI-sleutel", re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}")),
    ("Anthropic-sleutel", re.compile(r"\bsk-ant-[A-Za-z0-9_\-]{20,}")),
    ("GitHub-token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}")),
    ("privésleutel", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("AWS-sleutel", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    # Omgevingsvariabele-stijl: HOOFDLETTERS met een ingevulde waarde.
    # Bewust hoofdlettergevoelig, anders vangt hij ook gewone code als
    # "tokens_in = int(...)" -- dat kostte deze scanner bijna zijn geloofwaardigheid.
    ("ingevulde geheime variabele", re.compile(
        r"(?m)^\s*(?:export\s+)?[A-Z][A-Z0-9_]*"
        r"(?:SECRET|TOKEN|PASSWORD|PASSWD|API_KEY|APIKEY|COOKIE|PRIVATE_KEY)"
        r"[A-Z0-9_]*\s*[:=]\s*[\"']?(?!\s*$)(?!<)(?!\$\{)[^\s\"'#(]{8,}")),
    # Kleine letters mogen ook, maar dan alleen met een letterlijke tekstwaarde,
    # zodat een functieaanroep geen alarm geeft.
    ("geheim in code", re.compile(
        r"(?m)^\s*[A-Za-z0-9_]*"
        r"(?:secret|token|password|api_key|apikey|cookie|private_key)"
        r"[A-Za-z0-9_]*\s*[:=]\s*[\"'][^\"'\s]{12,}[\"']")),
]

# Bestandsnamen die sowieso niet in git horen.
FORBIDDEN_NAMES = re.compile(
    r"(^|/)(\.env(\.[a-z]+)?$|.*\.pem$|.*\.key$|.*\.p12$|"
    r"secrets?\.(ya?ml|json)$|conversations\.json$|.*chatgpt.*export.*\.zip$)",
    re.I,
)

# Voorbeeldbestanden mogen lege placeholders bevatten.
ALLOWED_NAMES = re.compile(r"(^|/)(\.env\.example|.*\.example|.*\.sample)$", re.I)

# Ontsnappingsluik voor testmateriaal en documentatie. Bewust op dezelfde regel
# en bewust vindbaar met grep, zodat elk gebruik ervan te beoordelen is.
ALLOWLIST_MARKER = "nep-geheim"

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}
MAX_BYTES = 2_000_000


@dataclass
class Hit:
    path: str
    line_no: int
    kind: str
    excerpt: str


def scan_text(path: str, text: str) -> list[Hit]:
    hits: list[Hit] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        if ALLOWLIST_MARKER in line:
            continue
        for kind, pattern in PATTERNS:
            if pattern.search(line):
                excerpt = line.strip()
                if len(excerpt) > 120:
                    excerpt = excerpt[:117] + "..."
                hits.append(Hit(path, line_no, kind, excerpt))
                break
    return hits


def scan_paths(paths: list[Path], root: Path) -> list[Hit]:
    hits: list[Hit] = []
    for path in paths:
        relative = str(path.relative_to(root)) if path.is_absolute() else str(path)
        if ALLOWED_NAMES.search(relative):
            continue
        if FORBIDDEN_NAMES.search(relative):
            hits.append(Hit(relative, 0, "bestand hoort niet in git", relative))
            continue
        try:
            if path.stat().st_size > MAX_BYTES:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        hits.extend(scan_text(relative, text))
    return hits


def scan_tree(root: Path) -> list[Hit]:
    root = Path(root)
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if SKIP_DIRS & set(path.relative_to(root).parts):
            continue
        files.append(path)
    return scan_paths(files, root)


def scan_staged(root: Path) -> list[Hit]:
    """Alleen wat op het punt staat gecommit te worden."""
    root = Path(root)
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        cwd=str(root), capture_output=True, text=True,
    )
    names = [n for n in result.stdout.splitlines() if n.strip()]
    paths = [root / name for name in names if (root / name).is_file()]
    return scan_paths(paths, root)


def format_hits(hits: list[Hit]) -> str:
    if not hits:
        return "Geen geheimen gevonden."
    lines = [f"{len(hits)} mogelijke geheimen gevonden — commit geweigerd:", ""]
    for hit in hits:
        where = f"{hit.path}:{hit.line_no}" if hit.line_no else hit.path
        lines.append(f"  [{hit.kind}] {where}")
        lines.append(f"      {hit.excerpt}")
    lines.append("")
    lines.append("Is het een vals alarm, haal de regel dan uit de commit of pas de")
    lines.append("melding aan in orchestrator/secret_scan.py. Zet nooit een echt")
    lines.append("geheim in git: uit de geschiedenis krijg je het niet meer weg.")
    return "\n".join(lines)
