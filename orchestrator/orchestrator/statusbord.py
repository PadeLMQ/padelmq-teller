"""De toestand van de lus, zichtbaar zonder in te loggen.

Een taak die stil in de wachtrij blijft staan is van buitenaf niet te
onderscheiden van een taak die draait. Dat is precies wat er misging: de lus
leefde, intake werkte, antwoorden werden verwerkt -- en toch bewoog taak #1
niet, en niemand kon zien waarom zonder de logs van de hostingdienst te openen.

Dit bord schrijft de toestand naar één issue per repository en werkt dat issue
bij in plaats van er reacties onder te zetten. Eén regel per taak, met de
laatste gebeurtenis erbij, zodat "wachtrij" en "draait" uit elkaar te houden
zijn.
"""

from __future__ import annotations

import json

LABEL = "orch:status"
TITEL = "Toestand van de orkestrator"


def _laatste_gebeurtenis(scope, task_id: int) -> str:
    rij = scope.conn.execute(
        "SELECT kind, ts, payload FROM events WHERE project_id = ? AND task_id = ?"
        " ORDER BY id DESC LIMIT 1",
        (scope.project_id, task_id),
    ).fetchone()
    if rij is None:
        return "—"
    detail = ""
    try:
        gegevens = json.loads(rij["payload"] or "{}")
        detail = str(gegevens.get("detail") or gegevens.get("reden") or "")[:70]
    except (TypeError, ValueError):
        pass
    return f"`{rij['kind']}` {rij['ts'][11:19]}" + (f" — {detail}" if detail else "")


def bouw(db, settings, slugs, hartslag=None) -> str:
    """De markdown die in het issue komt te staan."""
    from .models import now

    regels = [
        f"_Bijgewerkt: {now()}_",
        "",
    ]
    if hartslag is not None:
        stil = hartslag.get("stil_seconden")
        regels += [
            f"**Lus** — ronde {hartslag.get('rondes')}, laatste ronde"
            f" {hartslag.get('laatste_ronde')}"
            + (f" ({stil}s geleden)" if stil is not None else ""),
            f"**Noodstop** — {'AAN' if settings.paused() else 'uit'}",
        ]
        # De laatste fout van de lus hoort hier te staan. Zonder dit is een
        # ronde die elke keer stilletjes op dezelfde fout omvalt van buitenaf
        # niet te onderscheiden van een ronde die niets te doen had -- en dan
        # blijft een taak in de wachtrij staan zonder dat iemand ziet waarom.
        fout = hartslag.get("laatste_fout")
        regels.append(f"**Laatste fout** — `{fout}`" if fout
                      else "**Laatste fout** — geen")
        werk = hartslag.get("laatste_werk")
        if werk:
            regels.append(f"**Laatste werk** — {werk}")
        regels.append("")

    for slug in slugs:
        scope = db.scope(slug)
        taken = scope.tasks()
        dag = now()[:10]
        regels.append(f"### {slug}")
        regels.append(
            f"Vandaag besteed: {settings.symbol}{scope.spend_today(dag):.4f}"
            f" van {settings.symbol}{settings.budget_project_daily_eur:.2f}"
        )
        regels.append("")
        if not taken:
            regels += ["_geen taken_", ""]
            continue
        regels += [
            "| # | status | besteed | wacht op vraag | laatste gebeurtenis | titel |",
            "|---|--------|---------|----------------|---------------------|-------|",
        ]
        for t in taken:
            vraag = ""
            try:
                vraag = str(t["blocked_by_question"] or "")
            except (IndexError, KeyError):
                pass
            regels.append(
                f"| {t['id']} | `{t['status']}` |"
                f" {settings.symbol}{scope.spend_task(int(t['id'])):.4f} |"
                f" {vraag or '—'} | {_laatste_gebeurtenis(scope, int(t['id']))} |"
                f" {str(t['title'])[:46]} |"
            )
        regels.append("")
    regels.append("_Dit issue wordt door de orkestrator bijgewerkt. Niet beantwoorden._")
    return "\n".join(regels)


def publiceer(client, repo: str, tekst: str) -> int | None:
    """Zet de tekst in het statusissue; maakt het aan als het nog niet bestaat.

    Bewust bijwerken en niet becommentariëren: een bord dat elke twee minuten
    een reactie plaatst is binnen een dag onleesbaar.
    """
    if not repo:
        return None
    bestaand = client.issues_with_label(repo, LABEL)
    if bestaand:
        nummer = int(bestaand[0]["number"])
        client.update_issue_body(repo, nummer, tekst)
        return nummer
    return client.create_issue(repo, TITEL, tekst, [LABEL])
