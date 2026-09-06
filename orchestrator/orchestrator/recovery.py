"""Herstel na een crash of herstart.

Een orkestrator die 24/7 draait valt af en toe om: een container die stopt, een
proces dat gedood wordt, een fout die door de lus heen breekt. Wat daarna
overblijft is een taak die vastzit in een tussenfase en een run die nooit is
afgesloten. Zonder herstel wacht die taak eeuwig, want de wachtrij pakt alleen
'queued'.

Twee dingen die hier bewust NIET gebeuren:

- Een taak die op een mens wacht (blocked, parked) wordt niet hervat. Die is
  niet gecrasht; er is een antwoord nodig.
- Er wordt niet eindeloos hersteld. Een taak die telkens opnieuw omvalt heeft
  een probleem dat herstarten niet oplost, en dan is doorgaan duurder dan
  stoppen.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from .models import TaskStatus, now

# Fasen waarin een taak alleen kan staan terwijl er iets draait. Staat ze daar
# zonder lopende run, dan is dat proces weg.
ONDERBROKEN = (
    TaskStatus.BASELINE.value,
    TaskStatus.ANSWERING.value,
    TaskStatus.IMPLEMENTING.value,
    TaskStatus.VERIFYING.value,
    TaskStatus.REVIEWING.value,
    TaskStatus.COMMITTING.value,
)

# Wachten op een mens is geen storing.
MET_RUST_LATEN = (
    TaskStatus.BLOCKED.value,
    TaskStatus.PARKED.value,
    TaskStatus.DONE.value,
    TaskStatus.PR_OPEN.value,
)

MAX_HERSTELPOGINGEN = 3


@dataclass
class Herstel:
    verweesde_runs: list[int] = field(default_factory=list)
    hervatte_taken: list[int] = field(default_factory=list)
    opgegeven_taken: list[int] = field(default_factory=list)

    @property
    def iets_gedaan(self) -> bool:
        return bool(self.verweesde_runs or self.hervatte_taken or self.opgegeven_taken)

    def regels(self) -> list[str]:
        uit = []
        for run_id in self.verweesde_runs:
            uit.append(f"run {run_id} was verweesd en is afgesloten")
        for task_id in self.hervatte_taken:
            uit.append(f"taak {task_id} lag stil na een onderbreking en staat weer in de rij")
        for task_id in self.opgegeven_taken:
            uit.append(
                f"taak {task_id} is te vaak omgevallen en wordt niet meer automatisch hervat"
            )
        return uit


def _herstelpogingen(scope, task_id: int) -> int:
    rijen = scope.conn.execute(
        "SELECT COUNT(*) AS n FROM events WHERE project_id = ? AND task_id = ?"
        " AND kind = 'hersteld'",
        (scope.project_id, task_id),
    ).fetchone()
    return int(rijen["n"])


def _kolom(rij, naam):
    try:
        return rij[naam]
    except (IndexError, KeyError):
        return None


def _al_gedaan(scope, task_id: int, soort: str) -> bool:
    """Is deze ingreep al eens gedaan? Eén keer is herstel, twee keer is rondjes."""
    rij = scope.conn.execute(
        "SELECT COUNT(*) AS n FROM events WHERE project_id = ? AND task_id = ? AND kind = ?",
        (scope.project_id, task_id, soort),
    ).fetchone()
    return int(rij["n"]) > 0


# Gebeurtenissen van het herstel zelf. Ze zeggen niets over de taak: ze zijn
# het gevolg van wat er misging, niet iets wat daarna gebeurd is.
DOORKIJKEN = ("herstel-opgegeven", "hersteld", "budget-hervat",
              "blokkade-zonder-vraag", "run-verweesd")


def _laatste_budgetstop(scope, task_id: int):
    """De meest recente gebeurtenis van deze taak, als dat een budgetstop was.

    Alleen de meest recente telt: is er daarna iets anders gebeurd, dan staat de
    taak niet meer op het budget te wachten.
    """
    # Gebeurtenissen van het herstel zelf zeggen niets over de taak: ze zijn het
    # gevolg van de budgetstop, niet iets wat daarna is gebeurd. Taak 3 raakte
    # hierdoor definitief kwijt -- de laatste gebeurtenis was
    # 'herstel-opgegeven', dus de budgetstop eronder werd niet meer gezien.
    # Niet met een vast venster: het herstel logt elke ronde opnieuw, dus na een
    # half uur staat de budgetstop honderd gebeurtenissen terug. Mijn eerste
    # opzet keek twaalf terug en verloor taak 3 daardoor alsnog. De database
    # slaat ze over.
    plaatsen = ",".join("?" * len(DOORKIJKEN))
    rij = scope.conn.execute(
        "SELECT kind, payload FROM events WHERE project_id = ? AND task_id = ?"
        f" AND kind NOT IN ({plaatsen}) ORDER BY id DESC LIMIT 1",
        (scope.project_id, task_id, *DOORKIJKEN),
    ).fetchone()
    if rij is None or rij["kind"] != "budget":
        return None
    try:
        return json.loads(rij["payload"] or "{}")
    except (TypeError, ValueError):
        return {}


def budget_ruimer_dan(gegevens: dict, settings, vandaag: str) -> bool:
    """Mag een taak die op het budget strandde het opnieuw proberen?

    Alleen als er iets veranderd is: een hogere grens, of een nieuwe dag. Zonder
    die voorwaarde probeert hij elke ronde opnieuw, valt elke ronde op dezelfde
    grens om, en levert dat elke ronde een nieuwe melding op -- dat gebeurde
    werkelijk, drie keer achter elkaar.
    """
    if not gegevens:
        return False
    if str(gegevens.get("dag") or "") != vandaag:
        return True          # nieuwe dag: het dagbudget is weer vrij
    oude_grens = gegevens.get("grens")
    if oude_grens is None:
        return False
    niveau = str(gegevens.get("niveau") or "")
    nu = _grens_voor(niveau, settings)
    return nu is not None and nu > float(oude_grens)


def _grens_voor(niveau: str, settings) -> float | None:
    """Welke grens hoorde bij dit niveau? De naam komt uit BudgetExceeded."""
    if niveau.startswith("run"):
        return settings.budget_run_eur
    if niveau.startswith("taak"):
        return settings.budget_task_eur
    if niveau.startswith("project"):
        return settings.budget_project_daily_eur
    if niveau.startswith("globaal"):
        return settings.budget_global_daily_eur
    return None


def recover(scope, settings=None, vandaag: str | None = None) -> Herstel:
    """Ruimt op wat een vorige, afgebroken run heeft achtergelaten."""
    herstel = Herstel()

    # 1 · verweesde runs afsluiten. Ze tellen hun eigen aanroepen op, zodat het
    #     geld dat er al uit is zichtbaar blijft.
    open_runs = scope.conn.execute(
        "SELECT id, task_id FROM runs WHERE project_id = ? AND ended_at IS NULL",
        (scope.project_id,),
    ).fetchall()
    for rij in open_runs:
        run_id = int(rij["id"])
        scope.mark_run_wasted(run_id, "run verweesd door een onderbreking")
        scope.end_run(run_id, "verweesd")
        scope.log("run-verweesd", {"run": run_id}, task_id=rij["task_id"])
        herstel.verweesde_runs.append(run_id)

    # 2 · taken die in een tussenfase bleven staan
    for taak in scope.tasks():
        status = taak["status"]

        # Geblokkeerd door niets is niet geblokkeerd, maar zoek. Er is dan geen
        # vraag om te beantwoorden en dus geen enkele route terug -- de taak
        # blijft voorgoed liggen zonder dat iemand er iets aan kan doen. Eén
        # keer terugzetten is veilig: raakt hij opnieuw geblokkeerd, dan hoort
        # daar nu wél een vraag bij en blijft hij liggen zoals bedoeld.
        if status == TaskStatus.BLOCKED.value and not _kolom(taak, "blocked_by_question"):
            if _al_gedaan(scope, task_id := int(taak["id"]), "blokkade-zonder-vraag"):
                continue
            scope.set_task(task_id, status=TaskStatus.QUEUED.value)
            scope.log("blokkade-zonder-vraag",
                      {"detail": "geblokkeerd zonder vraag; er was geen weg terug"},
                      task_id=task_id)
            herstel.hervatte_taken.append(task_id)
            continue

        if status in MET_RUST_LATEN or status == TaskStatus.QUEUED.value:
            continue
        if status not in ONDERBROKEN and status != TaskStatus.FAILED.value:
            continue

        task_id = int(taak["id"])

        # Een budgetstop is geen crash. Hij mag dus geen herstelpoging opsouperen,
        # en de taak hoort terug te komen zodra de grens omhoog gaat of de dag
        # omslaat -- niet pas als een mens hem met de hand terugzet.
        budget = _laatste_budgetstop(scope, task_id)
        if budget is not None:
            if settings is not None and budget_ruimer_dan(
                budget, settings, vandaag or now()[:10]
            ):
                scope.set_task(task_id, status=TaskStatus.QUEUED.value)
                scope.log("budget-hervat",
                          {"van": status, "oude_grens": budget.get("grens"),
                           "niveau": budget.get("niveau")}, task_id=task_id)
                herstel.hervatte_taken.append(task_id)
            continue

        pogingen = _herstelpogingen(scope, task_id)
        if pogingen >= MAX_HERSTELPOGINGEN:
            if status != TaskStatus.FAILED.value:
                scope.set_task(task_id, status=TaskStatus.FAILED.value)
            scope.log(
                "herstel-opgegeven",
                {"pogingen": pogingen, "grens": MAX_HERSTELPOGINGEN,
                 "detail": "telkens opnieuw omgevallen; herstarten lost dit niet op"},
                task_id=task_id,
            )
            herstel.opgegeven_taken.append(task_id)
            continue

        scope.set_task(task_id, status=TaskStatus.QUEUED.value)
        scope.log("hersteld", {"van": status, "poging": pogingen + 1}, task_id=task_id)
        herstel.hervatte_taken.append(task_id)

    return herstel
