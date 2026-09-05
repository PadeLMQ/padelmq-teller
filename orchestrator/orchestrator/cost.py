"""Kostenbewaking. Vier limietniveaus, en de rem zit vóór de aanroep.

Eén dure run kan dus niet over een plafond heen schieten: we schatten eerst wat
de aanroep gaat kosten en weigeren hem als dat niet meer past.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .config import ModelPrice, Settings
from .db import Database, ProjectScope


class BudgetExceeded(RuntimeError):
    def __init__(self, level: str, limit: float, spent: float, estimated: float):
        self.level = level
        self.limit = limit
        self.spent = spent
        self.estimated = estimated
        super().__init__(
            f"budget {level} bereikt: besteed €{spent:.2f} + geschat €{estimated:.2f}"
            f" > limiet €{limit:.2f}"
        )


class InconsistentUsage(RuntimeError):
    """De provider rapporteert meer cachetokens dan invoertokens.

    Dat spreekt het datamodel van de provider tegen (cached_tokens is een
    onderdeel van input_tokens). We rekenen dan niet door met een gegokt
    bedrag maar stoppen, zoals bij elke andere afwijking.
    """


@dataclass
class Estimate:
    """Tokens van één aanroep.

    tokens_in is het TOTAAL aan invoertokens; cached_in is daar een deel van,
    niet iets bovenop. Zo rapporteert de Responses-API het ook:
    input_tokens_details is "a detailed breakdown of the input tokens".
    Het deel dat uit de cache kwam gaat tegen het cachetarief, de rest tegen
    het gewone invoertarief. Cacheschrijfacties hebben geen apart tarief en
    blijven dus gewoon invoer.
    """

    model: str
    tokens_in: int
    tokens_out: int
    cached_in: int = 0
    # De kostprijs zoals de aanbieder die zelf rapporteert. Is die er, dan gaat
    # ze voor: onze prijstabel is een benadering, de afrekening van de
    # aanbieder is het echte bedrag.
    reported_cost: float | None = None

    @property
    def uncached_in(self) -> int:
        if self.cached_in > self.tokens_in:
            raise InconsistentUsage(
                f"model {self.model}: {self.cached_in} cachetokens op "
                f"{self.tokens_in} invoertokens; cached_in hoort een deel van "
                "tokens_in te zijn"
            )
        return self.tokens_in - self.cached_in

    def cost(self, price: ModelPrice) -> float:
        if self.reported_cost is not None:
            return float(self.reported_cost)
        return (
            self.uncached_in / 1_000_000 * price.input_per_mtok
            + self.tokens_out / 1_000_000 * price.output_per_mtok
            + self.cached_in / 1_000_000 * price.cached_input_per_mtok
        )


WARNING_STEPS = (0.5, 0.8, 1.0)


class CostGuard:
    def __init__(self, db: Database, settings: Settings, on_warning=None):
        self.db = db
        self.settings = settings
        self.on_warning = on_warning or (lambda level, pct, spent, limit: None)
        self._warned: set[tuple[str, float]] = set()

    # -- prijzen ---------------------------------------------------------
    def price(self, model: str) -> ModelPrice:
        try:
            return self.settings.prices[model]
        except KeyError as exc:
            raise KeyError(
                f"geen prijs bekend voor model {model!r}; zet die in de instellingen"
                " voordat je hem gebruikt"
            ) from exc

    def estimate_cost(self, estimate: Estimate) -> float:
        return estimate.cost(self.price(estimate.model))

    # -- limieten --------------------------------------------------------
    def global_spend_today(self, day: str | None = None) -> float:
        day = day or date.today().isoformat()
        rows = self.db.across_projects(
            "SELECT COALESCE(SUM(cost_eur), 0) AS total FROM calls WHERE day = ?", (day,)
        )
        return float(rows[0]["total"])

    def check(
        self,
        scope: ProjectScope,
        estimate: Estimate,
        *,
        task_id: int | None = None,
        run_id: int | None = None,
        day: str | None = None,
    ) -> float:
        """Mag deze aanroep? Geeft de geschatte kosten terug, of werpt BudgetExceeded."""
        day = day or date.today().isoformat()
        cost = self.estimate_cost(estimate)
        settings = self.settings

        if run_id is not None:
            spent = scope.spend_run(run_id)
            self._gate("run", spent, cost, settings.budget_run_eur)
        if task_id is not None:
            spent = scope.spend_task(task_id)
            self._gate(f"taak {task_id}", spent, cost, settings.budget_task_eur)

        spent_project = scope.spend_today(day)
        self._gate(
            f"project {scope.slug} vandaag",
            spent_project,
            cost,
            settings.budget_project_daily_eur,
        )

        spent_global = self.global_spend_today(day)
        self._gate("globaal vandaag", spent_global, cost, settings.budget_global_daily_eur)
        return cost

    def _gate(self, level: str, spent: float, estimated: float, limit: float) -> None:
        if limit <= 0:
            return
        if spent + estimated > limit:
            raise BudgetExceeded(level, limit, spent, estimated)
        for step in WARNING_STEPS:
            if spent < limit * step <= spent + estimated:
                key = (level, step)
                if key not in self._warned:
                    self._warned.add(key)
                    self.on_warning(level, step, spent + estimated, limit)

    # -- vastleggen ------------------------------------------------------
    def record(
        self,
        scope: ProjectScope,
        estimate: Estimate,
        *,
        phase: str,
        role: str,
        task_id: int | None = None,
        run_id: int | None = None,
        day: str | None = None,
    ) -> float:
        cost = self.estimate_cost(estimate)
        scope.record_call(
            phase=phase,
            role=role,
            model=estimate.model,
            tokens_in=estimate.tokens_in,
            tokens_out=estimate.tokens_out,
            cached_in=estimate.cached_in,
            cost_eur=cost,
            task_id=task_id,
            run_id=run_id,
            day=day or date.today().isoformat(),
        )
        return cost

    # -- rapportage ------------------------------------------------------
    def report(self, day: str | None = None) -> list[dict]:
        day = day or date.today().isoformat()
        rows = self.db.across_projects(
            "SELECT p.slug AS project, c.model, c.role,"
            " SUM(c.tokens_in) AS tin, SUM(c.tokens_out) AS tout,"
            " SUM(c.cost_eur) AS cost, COUNT(*) AS calls"
            " FROM calls c JOIN projects p ON p.id = c.project_id"
            " WHERE c.day = ? GROUP BY p.slug, c.model, c.role ORDER BY cost DESC",
            (day,),
        )
        return [dict(r) for r in rows]
