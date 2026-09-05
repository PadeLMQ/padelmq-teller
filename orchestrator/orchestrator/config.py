"""Instellingen. Alles via omgevingsvariabelen, nul absolute paden in de code.

Zo draaien lokaal en de VPS identiek en is deployen niet meer dan de code
kopieren en een .env zetten (ontwerp, paragraaf 13).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw in (None, ""):
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} moet een getal zijn, kreeg {raw!r}") from exc


@dataclass
class ModelPrice:
    """Prijs per miljoen tokens, in de valuta van ORCH_CURRENCY.

    Er wordt nergens omgerekend. Vul je de tarieven van de provider in dollar in,
    dan zijn alle bedragen in de rapportage dollars. Een omrekening naar euro is
    een aparte handeling met een koers en een datum die jij kiest.
    """

    input_per_mtok: float
    output_per_mtok: float
    cached_input_per_mtok: float = 0.0


# Richtprijzen. Vervang ze door de actuele tarieven voordat dit in productie
# gaat; het ontwerp vermeldt expliciet dat ze geverifieerd moeten worden.
DEFAULT_PRICES: dict[str, ModelPrice] = {
    "claude-opus-5": ModelPrice(4.60, 23.00, 0.46),
    "claude-sonnet-5": ModelPrice(1.85, 9.20, 0.19),
    "claude-haiku-4-5": ModelPrice(0.92, 4.60, 0.09),
}


@dataclass
class Settings:
    data_dir: Path
    db_path: Path
    projects_dir: Path

    executor_model: str = "claude-opus-5"
    triage_model: str = "claude-haiku-4-5"
    reviewer_model: str = "gpt-5.6-terra"

    budget_global_daily_eur: float = 5.0
    budget_project_daily_eur: float = 5.0
    budget_task_eur: float = 2.0
    budget_run_eur: float = 1.0

    # De munt waarin de tarieven zijn ingevuld. Alleen een etiket: er wordt
    # nergens omgerekend, dus dit moet kloppen met wat je in de tarieven zet.
    currency: str = "USD"

    max_review_rounds: int = 3
    run_timeout_seconds: int = 1800

    prices: dict[str, ModelPrice] = field(default_factory=lambda: dict(DEFAULT_PRICES))

    @classmethod
    def from_env(cls) -> "Settings":
        # Standaard buiten de repository. De repo van dit project is publiek;
        # de kennisbasis met businessregels hoort daar nooit in te staan.
        default_root = Path.home() / ".orchestrator" / "data"
        data_dir = Path(os.environ.get("ORCH_DATA_DIR", default_root)).expanduser()
        settings = cls(
            data_dir=data_dir,
            db_path=data_dir / "orchestrator.sqlite3",
            projects_dir=data_dir / "projects",
            executor_model=os.environ.get("ORCH_EXECUTOR_MODEL", "claude-opus-5"),
            triage_model=os.environ.get("ORCH_TRIAGE_MODEL", "claude-haiku-4-5"),
            reviewer_model=os.environ.get("ORCH_REVIEWER_MODEL", "gpt-5.6-terra"),
            currency=os.environ.get("ORCH_CURRENCY", "USD").strip().upper() or "USD",
            budget_global_daily_eur=_env_float("ORCH_BUDGET_GLOBAL_DAILY_EUR", 5.0),
            budget_project_daily_eur=_env_float("ORCH_BUDGET_PROJECT_DAILY_EUR", 5.0),
            budget_task_eur=_env_float("ORCH_BUDGET_TASK_EUR", 2.0),
            budget_run_eur=_env_float("ORCH_BUDGET_RUN_EUR", 1.0),
        )
        reviewer_in = os.environ.get("ORCH_REVIEWER_PRICE_IN")
        reviewer_out = os.environ.get("ORCH_REVIEWER_PRICE_OUT")
        if reviewer_in and reviewer_out:
            settings.prices[settings.reviewer_model] = ModelPrice(
                float(reviewer_in), float(reviewer_out)
            )
        return settings

    def ensure_dirs(self) -> None:
        self.projects_dir.mkdir(parents=True, exist_ok=True)

    @property
    def symbol(self) -> str:
        return {"USD": "$", "EUR": "€", "GBP": "£"}.get(self.currency, self.currency + " ")

    @property
    def stop_file(self) -> Path:
        """Noodstop: bestaat dit bestand, dan start de orkestrator geen werk."""
        return self.data_dir / "PAUZE"

    def paused(self) -> bool:
        return self.stop_file.exists()

    def data_dir_inside_git(self) -> Path | None:
        """Staat de datamap binnen een git-werkboom?

        De kennisbasis bevat je businessregels en de database bevat je
        geschiedenis. Die horen nooit in een repository, ook niet per ongeluk
        doordat de datamap onder een gekloonde map is gezet. Geeft de map met
        de .git terug als dat zo is, anders None.
        """
        current = self.data_dir.expanduser().resolve()
        for candidate in [current, *current.parents]:
            if (candidate / ".git").exists():
                return candidate
        return None
