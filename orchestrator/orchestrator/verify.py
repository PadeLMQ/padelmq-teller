"""Harde verificatie. Deterministisch, zonder model.

Dit is de motor van de lus: rood bereikt de beoordelaar niet, en een model kan
een uitslag hier niet wijzigen, overslaan of als flaky bestempelen. Die knop
bestaat niet.
"""

from __future__ import annotations

import re
import shlex
import subprocess
from pathlib import Path

from .models import CheckResult, VerificationResult, VerificationStrength


class UnsafeCheck(RuntimeError):
    """Een verificatiecommando dat een bedrijfsactie zou kunnen uitvoeren."""


# Wat een verificatiecommando nooit mag doen. De orkestrator automatiseert
# softwareontwikkeling, geen bedrijfsvoering: geen live Shopify-, prijs-,
# voorraad-, sync- of importactie. Deze lijst zit bewust in de uitvoerder zelf
# en niet alleen in de configuratie, zodat een verkeerd ingestelde of gewijzigde
# project.yaml er nog steeds niet doorheen komt.
FORBIDDEN_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("synchronisatie", re.compile(r"(^|[\s:/])(sync|daily)\b", re.I)),
    ("scan van echte bronnen", re.compile(r"\bscan([:\-]|$)", re.I)),
    ("import van echte gegevens", re.compile(r"\bimport([:\-]|$)", re.I)),
    ("inrichting van echte gegevens", re.compile(r"\b(setup|seed|migrate)([:\-\s]|$)", re.I)),
    ("ontdekking via echte bronnen", re.compile(r"\bdiscover[:\-]", re.I)),
    ("markeren van echte producten", re.compile(r"\bflag[:\-]", re.I)),
    ("publiceren of uitrollen", re.compile(r"\b(publish|deploy|release)\b", re.I)),
    ("expliciet live draaien", re.compile(r"--(live|prod|production|apply|push|write)\b", re.I)),
    ("schrijven naar Shopify aanzetten", re.compile(
        r"\b(ENABLE_STOCK_WRITE|STOCK_SYNC_UP_ENABLED)\s*=\s*[\"']?true", re.I)),
    ("rechtstreekse Shopify-aanroep", re.compile(r"myshopify\.com|admin/api/.*graphql", re.I)),
    ("netwerkaanroep vanuit een check", re.compile(r"\b(curl|wget|http(ie)?)\b", re.I)),
)


def unsafe_reasons(name: str, command: str) -> list[str]:
    """Welke verboden patronen raakt dit commando?"""
    return [
        f"{label} ({pattern.pattern})"
        for label, pattern in FORBIDDEN_PATTERNS
        if pattern.search(command)
    ]


def assert_safe_checks(checks: dict[str, str]) -> None:
    """Weigert een verzameling checks waar een bedrijfsactie in zit."""
    problemen: list[str] = []
    for name, command in checks.items():
        for reason in unsafe_reasons(name, command):
            problemen.append(f"  check {name!r}: {command!r} — {reason}")
    if problemen:
        raise UnsafeCheck(
            "Deze verificatiecommando's kunnen een echte bedrijfsactie uitvoeren en "
            "worden geweigerd:\n" + "\n".join(problemen)
            + "\n\nDe orkestrator draait alleen tests, typecheck, lint en build."
        )


class VerifyAdapter:
    def __init__(self, timeout_seconds: int = 900):
        self.timeout_seconds = timeout_seconds

    def run(self, repo_root: Path, checks: dict[str, str]) -> VerificationResult:
        # De poort zit hier, in de uitvoerder zelf: er is geen codepad waarlangs
        # een verboden commando alsnog gedraaid kan worden.
        assert_safe_checks(checks)
        results: list[CheckResult] = []
        for name, command in checks.items():
            results.append(self._one(repo_root, name, command))
        return VerificationResult(checks=results)

    def _one(self, repo_root: Path, name: str, command: str) -> CheckResult:
        try:
            proc = subprocess.run(
                command,
                shell=True,
                cwd=str(repo_root),
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
            output = (proc.stdout or "") + (proc.stderr or "")
            return CheckResult(name, command, proc.returncode, output.strip()[-8000:])
        except subprocess.TimeoutExpired:
            return CheckResult(
                name, command, 124, f"check {name!r} overschreed {self.timeout_seconds}s"
            )
        except OSError as exc:  # commando bestaat niet, geen rechten, ...
            return CheckResult(name, command, 127, f"kon {name!r} niet starten: {exc}")


def infer_strength(checks: dict[str, str]) -> VerificationStrength:
    """Leidt de verificatiesterkte af uit de checks die een project heeft.

    Bewust voorzichtig: als we het niet zeker weten, kiezen we de zwakkere
    inschatting. Een te hoge inschatting laat de lus zelfstandig doorbouwen op
    bewijs dat er niet is.
    """
    if not checks:
        return VerificationStrength.WEAK
    joined = " ".join(f"{k} {v}" for k, v in checks.items()).lower()
    has_tests = any(
        word in joined
        for word in ("pytest", "unittest", "jest", "vitest", "go test", "phpunit", "rspec", "test")
    )
    has_types_or_build = any(
        word in joined for word in ("tsc", "mypy", "pyright", "build", "compile")
    )
    if has_tests and has_types_or_build:
        return VerificationStrength.STRONG
    if has_tests or has_types_or_build:
        return VerificationStrength.MEDIUM
    return VerificationStrength.WEAK


def quote(command: str) -> str:
    """Alleen voor logboekweergave."""
    return " ".join(shlex.quote(part) for part in shlex.split(command))
