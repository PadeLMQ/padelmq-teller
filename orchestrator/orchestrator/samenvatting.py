"""Een leesbare samenvatting per taak, opgebouwd uit de audittrail.

Het volledige spoor blijft staan en is de waarheid. Deze samenvatting is een
leeswijzer: wat werd gevraagd, wat is er gebeurd, wie besliste wat, en wat het
kostte. Wie iets wil narekenen vindt onderaan de verwijzingen naar de
onderliggende gebeurtenissen.

Er wordt niets geïnterpreteerd wat niet in de audittrail staat. Ontbreekt een
stap, dan staat dat er ook -- een samenvatting die gaten opvult zou precies het
vertrouwen ondermijnen waarvoor ze bedoeld is.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field


@dataclass
class Samenvatting:
    task_id: int
    project: str
    titel: str
    status: str
    gevraagd: str = ""
    criteria: list[str] = field(default_factory=list)
    herkomst: str = ""
    uitgevoerd: list[str] = field(default_factory=list)
    beoordelingen: list[dict] = field(default_factory=list)
    beslissingen: list[dict] = field(default_factory=list)
    checks: list[dict] = field(default_factory=list)
    commit: str = ""
    pr: str = ""
    kosten: dict = field(default_factory=dict)
    event_ids: list[int] = field(default_factory=list)


def _p(rij) -> dict:
    return json.loads(rij["payload"])


def bouw(scope, task_id: int) -> Samenvatting | None:
    taak = scope.task(task_id)
    if taak is None:
        return None

    s = Samenvatting(
        task_id=task_id,
        project=scope.slug,
        titel=taak["title"],
        status=taak["status"],
        gevraagd=(taak["spec"] or "").strip(),
        criteria=json.loads(taak["acceptance"] or "[]"),
    )

    events = list(scope.conn.execute(
        "SELECT id, kind, payload FROM events WHERE project_id = ? AND task_id = ?"
        " ORDER BY id", (scope.project_id, task_id)))
    for rij in events:
        s.event_ids.append(int(rij["id"]))
        soort, p = rij["kind"], _p(rij)

        if soort == "opdracht-aangenomen":
            s.herkomst = f"GitHub-issue #{p.get('issue')}"
        elif soort == "uitvoering":
            if p.get("samenvatting"):
                s.uitgevoerd.append(p["samenvatting"])
        elif soort == "beoordeling":
            s.beoordelingen.append({
                "oordeel": p.get("verdict"),
                "bevindingen": [b.get("punt", "") for b in p.get("bevindingen", [])],
                "open_criteria": p.get("criteria_open") or [],
                "instructie": p.get("instructie"),
            })
        elif soort in ("verificatie", "hervatting"):
            if p.get("checks"):
                s.checks = p["checks"]          # de laatste telt
        elif soort == "commit":
            s.commit = p.get("sha", "")
        elif soort == "pr-geopend":
            s.pr = p.get("url", "")

    # Beslissingen van de mens: via de vragen van deze taak.
    for vraag in scope.conn.execute(
            "SELECT id, text, status, answer, issue_number FROM questions"
            " WHERE project_id = ? AND task_id = ? ORDER BY id",
            (scope.project_id, task_id)):
        antwoord = json.loads(vraag["answer"] or "{}")
        s.beslissingen.append({
            "vraag_id": vraag["id"],
            "vraag": vraag["text"],
            "status": vraag["status"],
            "issue": vraag["issue_number"],
            "antwoord": antwoord.get("interpretation") or antwoord.get("vervallen"),
            "kennisitem": antwoord.get("decision"),
        })

    for rij in scope.conn.execute(
            "SELECT role, COUNT(*) n, COALESCE(SUM(cost_eur),0) c FROM calls"
            " WHERE project_id = ? AND task_id = ? GROUP BY role",
            (scope.project_id, task_id)):
        s.kosten[rij["role"]] = {"aanroepen": rij["n"], "kosten": float(rij["c"])}
    return s


def format_samenvatting(s: Samenvatting, symbool: str = "$") -> str:
    r = [f"# Taak {s.task_id} · {s.titel}",
         f"_project {s.project} · status **{s.status}**"
         + (f" · {s.herkomst}_" if s.herkomst else "_"), ""]

    r.append("## Wat er gevraagd werd")
    r.append(s.gevraagd or "_geen aanvullende omschrijving_")
    if s.criteria:
        r.append("")
        r.append("Acceptatiecriteria:")
        r += [f"- {c}" for c in s.criteria]

    r += ["", "## Wat er uitgevoerd is"]
    r += [f"- {u}" for u in s.uitgevoerd] or ["_de uitvoerder heeft niets gerapporteerd_"]

    r += ["", "## Wat de beoordelaar vond"]
    if not s.beoordelingen:
        r.append("_geen beoordeling gedraaid_")
    for i, b in enumerate(s.beoordelingen, 1):
        r.append(f"**Ronde {i}: {b['oordeel']}**")
        for punt in b["bevindingen"]:
            r.append(f"- {punt}")
        if b["open_criteria"]:
            r.append("Nog open: " + "; ".join(b["open_criteria"]))
        if b["oordeel"] == "revise" and b["instructie"]:
            r.append(f"Gevraagde correctie: {b['instructie']}")
        r.append("")

    r.append("## Beslissingen")
    if not s.beslissingen:
        r.append("_geen; alles kon uit bevestigde kennis_")
    for b in s.beslissingen:
        bron = f" (issue #{b['issue']})" if b["issue"] else ""
        r.append(f"- **{b['vraag']}**{bron}")
        r.append(f"  {b['antwoord'] or 'nog geen antwoord'}"
                 + (f" — vastgelegd als {b['kennisitem']}" if b["kennisitem"] else ""))

    r += ["", "## Verificatie"]
    if s.checks:
        for c in s.checks:
            teken = "geslaagd" if c.get("geslaagd") else "GEFAALD"
            r.append(f"- `{c.get('commando')}` → exit {c.get('exitcode')} ({teken})")
    else:
        r.append("_geen checks gedraaid_")

    r += ["", "## Resultaat"]
    r.append(f"- commit: `{s.commit}`" if s.commit else "- geen commit")
    r.append(f"- pull request: {s.pr}" if s.pr else "- geen pull request")

    totaal = sum(v["kosten"] for v in s.kosten.values())
    r += ["", "## AI-kosten"]
    for rol, v in sorted(s.kosten.items()):
        r.append(f"- {rol}: {v['aanroepen']} aanroep(en), {symbool}{v['kosten']:.6f}")
    r.append(f"- **totaal {symbool}{totaal:.6f}**")

    if s.event_ids:
        r += ["", "---",
              f"_Volledige audittrail: gebeurtenis {s.event_ids[0]} tot en met"
              f" {s.event_ids[-1]} in project `{s.project}`."
              f" Terug te lezen met `orchestrator inspect {s.project} --task {s.task_id}`._"]
    return "\n".join(r)
