"""Inspecteert een repository op écht beschikbare verificatie.

Doel: de verificatiesterkte van een project vaststellen op wat er werkelijk
draait, niet op wat we hopen. En waar de dekking dun is, dat benoemen in plaats
van het te compenseren met meer vertrouwen in een taalmodel.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from .models import VerificationStrength
from .verify import infer_strength

# Welke npm-scripts als welke soort check gelden.
_NPM_ROLES = {
    "test": ("tests", ("test", "test:unit", "test:ci", "vitest", "jest")),
    "typecheck": ("typecheck", ("typecheck", "type-check", "tsc")),
    "lint": ("lint", ("lint", "eslint")),
    "build": ("build", ("build", "compile")),
}


@dataclass
class Inspection:
    root: Path
    checks: dict[str, str] = field(default_factory=dict)
    strength: VerificationStrength = VerificationStrength.WEAK
    notes: list[str] = field(default_factory=list)
    source_files: list[str] = field(default_factory=list)
    test_files: list[str] = field(default_factory=list)
    untested: list[str] = field(default_factory=list)

    def as_cli_flags(self) -> str:
        return " ".join(f'--check {name}="{cmd}"' for name, cmd in self.checks.items())


def _npm_checks(package_json: Path) -> tuple[dict[str, str], list[str]]:
    checks: dict[str, str] = {}
    notes: list[str] = []
    try:
        data = json.loads(package_json.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {}, [f"package.json niet leesbaar: {exc}"]
    scripts = data.get("scripts") or {}
    for _, (label, candidates) in _NPM_ROLES.items():
        for candidate in candidates:
            if candidate in scripts:
                checks[label] = f"npm run {candidate}"
                break
    missing = [label for label, _ in _NPM_ROLES.values() if label not in checks]
    if missing:
        notes.append("geen npm-script gevonden voor: " + ", ".join(sorted(set(missing))))
    return checks, notes


def _python_checks(root: Path) -> tuple[dict[str, str], list[str]]:
    checks: dict[str, str] = {}
    notes: list[str] = []
    has_tests_dir = (root / "tests").is_dir() or list(root.glob("test_*.py"))
    if (root / "pytest.ini").exists() or "pytest" in _read(root / "pyproject.toml"):
        checks["tests"] = "pytest -q"
    elif has_tests_dir:
        checks["tests"] = "python3 -m unittest discover -s tests -t ."
    if "mypy" in _read(root / "pyproject.toml") or (root / "mypy.ini").exists():
        checks["typecheck"] = "mypy ."
    if "ruff" in _read(root / "pyproject.toml"):
        checks["lint"] = "ruff check ."
    if not checks:
        notes.append("geen Python-testopzet gevonden")
    return checks, notes


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _module_coverage(root: Path) -> tuple[list[str], list[str], list[str]]:
    """Welke bronmodules hebben geen testbestand met een overeenkomende naam?

    Bewust voorzichtig geformuleerd: dit toont ontbrekende *toegewijde* tests.
    Een module kan indirect gedekt zijn door de test van een andere module.
    Alleen een echte coverage-run geeft daar uitsluitsel over.
    """
    source_dirs = [d for d in (root / "src" / "lib", root / "src", root / "lib") if d.is_dir()]
    if not source_dirs:
        return [], [], []
    sources: list[str] = []
    for directory in source_dirs[:1]:
        for path in sorted(directory.glob("*.ts")) + sorted(directory.glob("*.py")):
            if path.stem.endswith((".test", "_test")) or path.stem in ("types", "index"):
                continue
            sources.append(path.stem)

    tests: list[str] = []
    for pattern in ("tests/**/*.test.ts", "tests/**/*.test.py", "tests/**/test_*.py",
                    "src/**/*.test.ts", "test/**/*.test.ts"):
        for path in root.glob(pattern):
            tests.append(path.name)

    stems = {re.sub(r"\.(test|spec)$", "", Path(t).stem).lower() for t in tests}
    stems |= {re.sub(r"^test_", "", Path(t).stem).lower() for t in tests}

    untested = []
    for name in sources:
        lowered = name.lower()
        if not any(lowered == s or lowered in s or s.startswith(lowered) for s in stems):
            untested.append(name)
    return sources, sorted(tests), untested


def inspect(root: Path) -> Inspection:
    root = Path(root)
    result = Inspection(root=root)
    if not root.is_dir():
        result.notes.append(f"pad bestaat niet: {root}")
        return result

    checks: dict[str, str] = {}
    if (root / "package.json").is_file():
        found, notes = _npm_checks(root / "package.json")
        checks.update(found)
        result.notes.extend(notes)
    if (root / "pyproject.toml").is_file() or (root / "setup.py").is_file() or \
            (root / "requirements.txt").is_file():
        found, notes = _python_checks(root)
        for key, value in found.items():
            checks.setdefault(key, value)
        result.notes.extend(notes)
    if (root / "go.mod").is_file():
        checks.setdefault("tests", "go test ./...")
        checks.setdefault("build", "go build ./...")
    if (root / "Makefile").is_file() and "test:" in _read(root / "Makefile"):
        checks.setdefault("tests", "make test")

    result.checks = checks
    result.strength = infer_strength(checks)

    if (root / "migrations").is_dir():
        result.notes.append(
            "er is een migrations/-map: overweeg een databasecheck als aparte poort"
        )
    if not (root / ".github" / "workflows").is_dir():
        result.notes.append("geen GitHub Actions-workflow; de checks draaien alleen lokaal")

    sources, tests, untested = _module_coverage(root)
    result.source_files, result.test_files, result.untested = sources, tests, untested
    return result


def format_report(result: Inspection) -> str:
    lines = [f"# Inspectie van {result.root}", ""]
    if result.checks:
        lines.append("## Gevonden verificatie")
        for name, command in result.checks.items():
            lines.append(f"- {name}: `{command}`")
    else:
        lines.append("## Gevonden verificatie\n- geen")
    lines.append("")
    lines.append(f"**Verificatiesterkte: {result.strength.value}** "
                 f"({result.strength.max_implement_iterations} iteraties per taak)")
    if result.strength is not VerificationStrength.STRONG:
        lines.append("")
        lines.append("> Bij matige of zwakke verificatie bouwt de lus niet zelfstandig door. "
                     "Een gebrek aan tests wordt niet gecompenseerd met meer vertrouwen "
                     "in een taalmodel.")
    if result.notes:
        lines.append("\n## Opmerkingen")
        lines.extend(f"- {note}" for note in result.notes)
    if result.untested:
        lines.append("\n## Modules zonder toegewijd testbestand")
        lines.append("_Mogelijk indirect gedekt; alleen een coverage-run geeft uitsluitsel._")
        lines.extend(f"- {name}" for name in result.untested)
    if result.checks:
        lines.append("\n## Aankoppelen")
        lines.append(f"```\norchestrator project add <slug> --repo {result.root} \\\n"
                     f"    {result.as_cli_flags()}\n```")
    return "\n".join(lines)
