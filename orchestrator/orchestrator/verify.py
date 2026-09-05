"""Harde verificatie. Deterministisch, zonder model.

Dit is de motor van de lus: rood bereikt de beoordelaar niet, en een model kan
een uitslag hier niet wijzigen, overslaan of als flaky bestempelen. Die knop
bestaat niet.
"""

from __future__ import annotations

import shlex
import subprocess
from pathlib import Path

from .models import CheckResult, VerificationResult, VerificationStrength


class VerifyAdapter:
    def __init__(self, timeout_seconds: int = 900):
        self.timeout_seconds = timeout_seconds

    def run(self, repo_root: Path, checks: dict[str, str]) -> VerificationResult:
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
