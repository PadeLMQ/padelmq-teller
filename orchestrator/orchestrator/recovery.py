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

from .models import TaskStatus

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


def recover(scope) -> Herstel:
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
        if status in MET_RUST_LATEN or status == TaskStatus.QUEUED.value:
            continue
        if status not in ONDERBROKEN and status != TaskStatus.FAILED.value:
            continue

        task_id = int(taak["id"])
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
