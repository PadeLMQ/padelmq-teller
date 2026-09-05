"""Het eindrapport van één taak.

Precies de twaalf punten die vooraf zijn afgesproken, opgebouwd uit wat de lus
zelf heeft vastgelegd. Er wordt niets afgeleid dat niet in het logboek staat:
ontbreekt iets, dan staat dat er ook zo in plaats van een aanname.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime

from .db import Database, ProjectScope
from .projects import Project


def _tijd(waarde: str | None) -> datetime | None:
    if not waarde:
        return None
    try:
        return datetime.fromisoformat(waarde)
    except ValueError:
        return None


@dataclass
class Report:
    project: str
    task_id: int
    data: dict = field(default_factory=dict)

    def as_json(self) -> str:
        return json.dumps(self.data, ensure_ascii=False, indent=2)


def build_report(scope: ProjectScope, project: Project, task_id: int) -> Report:
    taak = scope.task(task_id)
    if taak is None:
        raise ValueError(f"taak {task_id} bestaat niet in project {scope.slug}")

    gebeurtenissen = [dict(r) for r in reversed(scope.events(limit=2000))]
    voor_taak = [e for e in gebeurtenissen if e["task_id"] == task_id]
    for e in voor_taak:
        e["payload"] = json.loads(e["payload"] or "{}")

    def van(soort: str) -> list[dict]:
        return [e for e in voor_taak if e["kind"] == soort]

    runs = [
        dict(r) for r in scope.conn.execute(
            "SELECT * FROM runs WHERE project_id = ? AND task_id = ? ORDER BY id",
            (scope.project_id, task_id),
        )
    ]
    calls = [
        dict(r) for r in scope.conn.execute(
            "SELECT * FROM calls WHERE project_id = ? AND task_id = ? ORDER BY id",
            (scope.project_id, task_id),
        )
    ]
    vragen = [
        dict(r) for r in scope.conn.execute(
            "SELECT * FROM questions WHERE project_id = ? AND task_id = ? ORDER BY id",
            (scope.project_id, task_id),
        )
    ]

    # --- 8 en 9: aanroepen, tokens en kosten -----------------------------
    per_rol: dict[str, int] = {}
    per_model: dict[str, dict] = {}
    for call in calls:
        per_rol[call["role"]] = per_rol.get(call["role"], 0) + 1
        m = per_model.setdefault(
            call["model"], {"aanroepen": 0, "tokens_in": 0, "tokens_uit": 0,
                            "cache_gelezen": 0, "kosten_eur": 0.0}
        )
        m["aanroepen"] += 1
        m["tokens_in"] += call["tokens_in"]
        m["tokens_uit"] += call["tokens_out"]
        m["cache_gelezen"] += call["cached_in"]
        m["kosten_eur"] = round(m["kosten_eur"] + call["cost_eur"], 4)

    # --- 9b: kosten per aanbieder ("EUR X = EUR A Claude + EUR B GPT") ----
    # De rol is betrouwbaarder dan de modelnaam: de uitvoerder is altijd Claude,
    # de beantwoorder en beoordelaar altijd de reviewer. De modelnaam dient
    # alleen als terugval voor aanroepen zonder bekende rol.
    ROL_NAAR_AANBIEDER = {
        "uitvoerder": "Claude",
        "beantwoorder": "GPT",
        "beoordelaar": "GPT",
    }
    per_aanbieder: dict[str, dict] = {}
    for call in calls:
        aanbieder = ROL_NAAR_AANBIEDER.get(call["role"])
        if aanbieder is None:
            aanbieder = "Claude" if call["model"].lower().startswith("claude") else "GPT"
        a = per_aanbieder.setdefault(aanbieder, {"aanroepen": 0, "kosten_eur": 0.0})
        a["aanroepen"] += 1
        a["kosten_eur"] = round(a["kosten_eur"] + call["cost_eur"], 4)

    treffers = [e for e in voor_taak if e["kind"] == "cache-treffer"]

    # --- 10: looptijd ----------------------------------------------------
    start = _tijd(taak["created_at"])
    starts = [_tijd(r["started_at"]) for r in runs if r["started_at"]]
    eindes = [_tijd(r["ended_at"]) for r in runs if r["ended_at"]]
    eerste_run = min([t for t in starts if t], default=None)
    laatste = max([t for t in eindes if t], default=None)
    looptijd = (laatste - eerste_run).total_seconds() if (eerste_run and laatste) else None

    # --- 7: ging Claude zelfstandig verder? ------------------------------
    volgorde = [e["kind"] for e in voor_taak]
    uitvoeringen = volgorde.count("uitvoering")
    menselijk_antwoord = any(v["status"] == "answered" for v in vragen)
    zelfstandig_vervolg = uitvoeringen > 1 and not menselijk_antwoord

    data = {
        "1_taak": {
            "id": task_id,
            "titel": taak["title"],
            "specificatie": taak["spec"],
            "acceptatiecriteria": json.loads(taak["acceptance"] or "[]"),
            "eindstatus": taak["status"],
            "aangemaakt": taak["created_at"],
        },
        "2_wat_claude_deed": [
            {
                "poging": i + 1,
                "samenvatting": e["payload"].get("samenvatting"),
                "open_vragen": e["payload"].get("open_vragen", []),
                "aannames": e["payload"].get("aannames", []),
                "voorgesteld_alternatief": e["payload"].get("alternatief"),
                "aanbeveling": e["payload"].get("aanbeveling"),
                "sessie": e["payload"].get("sessie"),
                "tijdstip": e["ts"],
            }
            for i, e in enumerate(van("uitvoering"))
        ],
        "3_harde_verificatie": [
            {
                "poging": e["payload"].get("poging"),
                "geslaagd": e["payload"].get("ok"),
                "checks": e["payload"].get("checks", []),
                "gefaald": e["payload"].get("gefaald", []),
                "tijdstip": e["ts"],
            }
            for e in van("verificatie")
        ] or [{"opmerking": "geen verificatie uitgevoerd — zie het logboek"}],
        "4_context_voor_de_reviewer": [
            {
                "fase": e["payload"].get("fase"),
                "kennisitems": e["payload"].get("kennisitems", []),
                "aantal_items": e["payload"].get("aantal_items"),
                "waarvan_bevestigd": e["payload"].get("bevestigd"),
                "context_tekens": e["payload"].get("context_tekens"),
                "context_sha256": e["payload"].get("context_sha256"),
                "diff_tekens": e["payload"].get("diff_tekens"),
                "verificatie_samenvatting": e["payload"].get("verificatie_samenvatting"),
                "acceptatiecriteria": e["payload"].get("acceptatiecriteria"),
                "voorgelegde_vragen": e["payload"].get("vragen"),
                "tijdstip": e["ts"],
            }
            for e in van("reviewer-context")
        ] or [{"opmerking": "de reviewer is niet geraadpleegd"}],
        "5_6_triage": [
            {
                "vraag": e["payload"].get("question"),
                "uitkomst": e["payload"].get("outcome"),
                "motivatie": e["payload"].get("reason"),
                "gebruikte_bronnen": e["payload"].get("bronnen", []),
                "aangeboden_bronnen": e["payload"].get("aangeboden_bronnen", []),
                "antwoord": e["payload"].get("antwoord"),
                "categorie": e["payload"].get("categorie"),
                "tijdstip": e["ts"],
            }
            for e in van("triage")
        ] or [{"opmerking": "er is geen vraag door de triage gegaan"}],
        "5b_beoordeling": [
            {
                "verdict": e["payload"].get("verdict"),
                "bevindingen": e["payload"].get("bevindingen", []),
                "criteria_gehaald": e["payload"].get("criteria_gehaald", []),
                "criteria_open": e["payload"].get("criteria_open", []),
                "voorgesteld_alternatief": e["payload"].get("alternatief"),
                "aanbeveling": e["payload"].get("aanbeveling"),
                "tijdstip": e["ts"],
            }
            for e in van("beoordeling")
        ] or [{"opmerking": "de beoordelaar is niet geraadpleegd"}],
        "7_claude_ging_zelfstandig_verder": {
            "antwoord": zelfstandig_vervolg,
            "aantal_uitvoerstappen": uitvoeringen,
            "menselijk_antwoord_tussendoor": menselijk_antwoord,
            "volgorde": volgorde,
        },
        "8_aanroepen": {
            "totaal": len(calls),
            "per_rol": per_rol,
        },
        "9_tokens_en_kosten": {
            "per_model": per_model,
            "totaal_eur": round(sum(c["cost_eur"] for c in calls), 4),
        },
        "9b_kosten_per_aanbieder": per_aanbieder,
        "9c_hergebruik": {
            "cache_treffers": len(treffers),
            "bespaarde_tokens_in": sum(
                e["payload"].get("bespaarde_tokens_in", 0) for e in treffers),
            "bespaarde_tokens_uit": sum(
                e["payload"].get("bespaarde_tokens_uit", 0) for e in treffers),
        },
        "10_looptijd": {
            "eerste_run": eerste_run.isoformat() if eerste_run else None,
            "laatste_run_einde": laatste.isoformat() if laatste else None,
            "seconden": round(looptijd, 1) if looptijd is not None else None,
            "taak_aangemaakt": start.isoformat() if start else None,
            "runs": [{"fase": r["phase"], "uitkomst": r["outcome"],
                      "start": r["started_at"], "einde": r["ended_at"]} for r in runs],
        },
        "11_oplevering": {
            "branch": next((e["payload"].get("branch") for e in van("commit")), None)
                      or next((e["payload"].get("branch") for e in van("klaar")), None),
            "commits": [e["payload"].get("sha") for e in van("commit")],
            "pull_request": next(
                (e["payload"].get("url") or e["payload"].get("number")
                 for e in van("pr-geopend")), None
            ),
            "pr_mislukt": next((e["payload"].get("detail") for e in van("pr-mislukt")), None),
            "push_mislukt": next((e["payload"].get("detail") for e in van("push-mislukt")), None),
        },
        "12_vragen_aan_de_mens": [
            {
                "id": v["id"],
                "vraag": v["text"],
                "uitkomst": v["outcome"],
                "status": v["status"],
                "waarom": v["why_blocking"],
                "opties": json.loads(v["options"] or "[]"),
                "voorstel": v["proposed"],
                "issue": v["issue_number"],
                "beantwoord_op": v["answered_at"],
            }
            for v in vragen
        ],
    }
    return Report(project=scope.slug, task_id=task_id, data=data)


def format_report(report: Report) -> str:
    d = report.data
    r: list[str] = [f"# Runrapport — {report.project} · taak {report.task_id}", ""]

    t = d["1_taak"]
    r += ["## 1. De taak", f"**{t['titel']}**", ""]
    if t["specificatie"]:
        r += [t["specificatie"], ""]
    r += ["Acceptatiecriteria:"]
    r += [f"- {c}" for c in t["acceptatiecriteria"]] or ["- (geen)"]
    r += ["", f"Eindstatus: `{t['eindstatus']}`", ""]

    r += ["## 2. Wat Claude deed"]
    for stap in d["2_wat_claude_deed"]:
        r += [f"**Poging {stap['poging']}** — {stap.get('samenvatting') or '(geen samenvatting)'}"]
        if stap.get("open_vragen"):
            r += ["  - open vragen: " + "; ".join(stap["open_vragen"])]
        if stap.get("aannames"):
            r += ["  - aannames: " + "; ".join(stap["aannames"])]
        if stap.get("voorgesteld_alternatief"):
            r += [f"  - alternatief: {stap['voorgesteld_alternatief']}"
                  f" ({stap.get('aanbeveling')})"]
    if not d["2_wat_claude_deed"]:
        r += ["(geen uitvoerstap vastgelegd)"]
    r += [""]

    r += ["## 3. Harde verificatie"]
    for v in d["3_harde_verificatie"]:
        if "opmerking" in v:
            r += [v["opmerking"]]
            continue
        r += [f"**Poging {v.get('poging')}** — "
              f"{'alles geslaagd' if v.get('geslaagd') else 'GEFAALD'}"]
        for c in v.get("checks", []):
            merk = "geslaagd" if c.get("geslaagd") else "GEFAALD"
            r += [f"  - `{c.get('naam')}`: `{c.get('commando')}` → exitcode "
                  f"{c.get('exitcode')} ({merk})"]
    r += [""]

    r += ["## 4. Welke context de reviewer had"]
    for c in d["4_context_voor_de_reviewer"]:
        if "opmerking" in c:
            r += [c["opmerking"]]
            continue
        r += [f"**Fase: {c.get('fase')}** — {c.get('aantal_items')} kennisitems, "
              f"waarvan {c.get('waarvan_bevestigd')} bevestigd; "
              f"{c.get('context_tekens')} tekens (sha256 "
              f"{str(c.get('context_sha256'))[:12]}…)"]
        for item in c.get("kennisitems", []):
            r += [f"  - `{item['id']}` ({item['status']}) uit {item['bestand']}"]
        if c.get("diff_tekens") is not None:
            r += [f"  - diff: {c['diff_tekens']} tekens"]
        if c.get("voorgelegde_vragen"):
            r += ["  - voorgelegde vragen: " + "; ".join(c["voorgelegde_vragen"])]
    r += [""]

    r += ["## 5 en 6. Triage: uitkomst, motivatie en bronnen"]
    for tr in d["5_6_triage"]:
        if "opmerking" in tr:
            r += [tr["opmerking"]]
            continue
        r += [f"**{str(tr.get('uitkomst')).upper()}** — {tr.get('vraag')}",
              f"  - motivatie: {tr.get('motivatie')}",
              "  - gebruikte bevestigde bronnen: "
              + (", ".join(tr.get("gebruikte_bronnen") or []) or "geen")]
        if tr.get("aangeboden_bronnen"):
            r += ["  - aangeboden bronnen: " + ", ".join(tr["aangeboden_bronnen"])]
        if tr.get("antwoord"):
            r += [f"  - antwoord: {tr['antwoord']}"]
    r += [""]

    r += ["## 5b. Beoordeling van de wijziging"]
    for b in d["5b_beoordeling"]:
        if "opmerking" in b:
            r += [b["opmerking"]]
            continue
        r += [f"**{b.get('verdict')}**"]
        for f in b.get("bevindingen", []):
            r += [f"  - [{f.get('ernst')}] {f.get('bestand')}: {f.get('punt')}"]
        if b.get("criteria_open"):
            r += ["  - criteria nog open: " + ", ".join(b["criteria_open"])]
        if b.get("voorgesteld_alternatief"):
            r += [f"  - alternatief: {b['voorgesteld_alternatief']} ({b.get('aanbeveling')})"]
    r += [""]

    z = d["7_claude_ging_zelfstandig_verder"]
    r += ["## 7. Ging Claude zelfstandig verder?",
          f"**{'Ja' if z['antwoord'] else 'Nee'}** — {z['aantal_uitvoerstappen']} uitvoerstappen, "
          f"menselijk antwoord tussendoor: {'ja' if z['menselijk_antwoord_tussendoor'] else 'nee'}",
          "", "Volgorde: " + " → ".join(z["volgorde"]), ""]

    a = d["8_aanroepen"]
    r += ["## 8. Aantal aanroepen", f"Totaal: {a['totaal']}"]
    r += [f"- {rol}: {n}" for rol, n in sorted(a["per_rol"].items())] or ["- geen"]
    r += [""]

    k = d["9_tokens_en_kosten"]
    r += ["## 9. Tokens en kosten per model", "",
          "| model | aanroepen | tokens in | tokens uit | cache | kosten |",
          "|---|---:|---:|---:|---:|---:|"]
    for model, m in sorted(k["per_model"].items()):
        r += [f"| `{model}` | {m['aanroepen']} | {m['tokens_in']} | {m['tokens_uit']} "
              f"| {m['cache_gelezen']} | €{m['kosten_eur']:.4f} |"]
    if not k["per_model"]:
        r += ["| (geen aanroepen) | | | | | |"]
    r += ["", f"**Totaal: €{k['totaal_eur']:.4f}**"]
    ap = d["9b_kosten_per_aanbieder"]
    if ap:
        onderdelen = " + ".join(
            f"€{v['kosten_eur']:.4f} {naam}" for naam, v in sorted(ap.items())
        )
        r += [f"Deze taak heeft €{k['totaal_eur']:.4f} gekost: {onderdelen}."]
    h = d["9c_hergebruik"]
    if h["cache_treffers"]:
        r += [f"Hergebruikt uit de cache: {h['cache_treffers']} reviewerantwoord(en), "
              f"{h['bespaarde_tokens_in']} invoer- en {h['bespaarde_tokens_uit']} "
              "uitvoertokens niet opnieuw betaald."]
    r += [""]

    lt = d["10_looptijd"]
    if lt["seconden"] is None:
        duur = "(niet vast te stellen)"
    elif lt["seconden"] < 1:
        # De tijdstempels hebben secondeprecisie; onder een seconde zegt het getal niets.
        duur = "minder dan een seconde"
    else:
        duur = f"{lt['seconden']:.0f} seconden"
    r += ["## 10. Looptijd", duur,
          f"van {lt['eerste_run']} tot {lt['laatste_run_einde']}", ""]

    o = d["11_oplevering"]
    r += ["## 11. Oplevering",
          f"- branch: `{o['branch']}`" if o["branch"] else "- branch: (geen)",
          "- commits: " + (", ".join(f"`{c[:12]}`" for c in o["commits"] if c) or "geen"),
          f"- pull request: {o['pull_request'] or 'geen'}"]
    if o.get("push_mislukt"):
        r += [f"- pushen mislukte: {o['push_mislukt']}"]
    if o.get("pr_mislukt"):
        r += [f"- PR openen mislukte: {o['pr_mislukt']}"]
    r += [""]

    r += ["## 12. Vragen die bij jou terechtkwamen"]
    if d["12_vragen_aan_de_mens"]:
        for v in d["12_vragen_aan_de_mens"]:
            r += [f"- **{v['uitkomst'].upper()}** (#{v['id']}, {v['status']}) {v['vraag']}",
                  f"  - waarom: {v['waarom']}"]
            if v["opties"]:
                r += ["  - opties: " + " · ".join(v["opties"])]
            if v["issue"]:
                r += [f"  - issue #{v['issue']}"]
    else:
        r += ["Geen. De lus is zonder jouw tussenkomst afgerond."]
    return "\n".join(r)


def build_and_format(db: Database, project: Project, task_id: int) -> str:
    return format_report(build_report(db.scope(project.slug), project, task_id))
