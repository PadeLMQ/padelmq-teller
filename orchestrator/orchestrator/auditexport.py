"""De audittrail in leesbare vorm, buiten de database om.

De database staat op een volume. Volumes overleven een herstart, maar niet
elke verhuizing, en een sqlite-bestand is geen ding dat je nog kunt lezen als
de orkestrator er niet meer is. Alles wat er is gebeurd -- welke beslissingen
de eigenaar heeft genomen, wat een taak heeft gekost, waar van het draaiboek
is afgeweken -- hoort daarom ook als tekst te bestaan, in versiebeheer.

Dit is een export, geen samenvatting: er wordt niets weggelaten omdat het
onbelangrijk lijkt, en er wordt niets bij verzonnen. Ontbreekt iets in de
database, dan staat dat er zo.
"""

from __future__ import annotations

import json

# Gebeurtenissen die zeggen dat er van de voorgeschreven werkwijze is afgeweken.
# Die zijn het belangrijkst om te bewaren: ze verklaren waarom iets anders is
# gegaan dan het draaiboek zegt.
AFWIJKINGEN = (
    "afwijking", "budget-uitzondering", "kennis-vervallen", "kennis-gecorrigeerd",
    "configuratie-gecorrigeerd", "run-gecrasht", "run-verweesd",
    "hervatting-overgeslagen", "feedback-hersteld", "handtekening-opgeruimd",
    "reviewteller-gereset", "verificatie-rommel",
)


def _kolom(rij, naam, standaard=None):
    try:
        waarde = rij[naam]
    except (IndexError, KeyError):
        return standaard
    return standaard if waarde is None else waarde


def bouw(scope, slug: str, *, symbool: str = "$") -> str:
    """Bouwt de volledige markdown-export voor één project."""
    uit: list[str] = [
        f"# Audittrail — {slug}",
        "",
        "_Automatisch geëxporteerd uit de audittrail van de orkestrator._",
        "_Dit bestand wordt niet gelezen door de lus; het is er voor mensen._",
        "",
    ]

    taken = scope.tasks()
    uit += ["## Taken", ""]
    if not taken:
        uit.append("Geen taken vastgelegd.")
    for taak in taken:
        uit.append(
            f"- **#{taak['id']} {taak['title']}** — status `{taak['status']}`,"
            f" {_kolom(taak, 'iterations', 0)} iteratie(s),"
            f" {_kolom(taak, 'review_rounds', 0)} beoordelingsronde(s)"
        )
        spec = (_kolom(taak, "spec", "") or "").strip()
        if spec:
            uit.append(f"  - opdracht: {spec.splitlines()[0][:200]}")
    uit.append("")

    uit += ["## Beslissingen van de eigenaar", "",
            "_Elke vraag die de lus heeft laten stoppen, met het antwoord dat"
            " erop volgde. Dit is de bron van waarheid voor wat er is afgesproken._", ""]
    alle_vragen = scope.all_questions()
    if not alle_vragen:
        uit.append("Geen vragen vastgelegd.")
    for vraag in alle_vragen:
        issue = _kolom(vraag, "issue_number")
        herkomst = f" (GitHub-issue #{issue})" if issue else ""
        uit += [
            f"### Vraag {vraag['id']}{herkomst}",
            "",
            f"- uitkomst: `{_kolom(vraag, 'outcome', '?')}`,"
            f" status: `{_kolom(vraag, 'status', '?')}`",
            f"- vraag: {vraag['text']}",
        ]
        waarom = (_kolom(vraag, "why_blocking", "") or "").strip()
        if waarom:
            uit.append(f"- waarom blokkerend: {waarom}")
        antwoord = (_kolom(vraag, "answer", "") or "").strip()
        uit.append(f"- antwoord: {antwoord}" if antwoord
                   else "- antwoord: _(geen antwoord vastgelegd)_")
        uit.append("")

    aanroepen = scope.all_calls()
    totaal = sum(_kolom(c, "cost_eur", 0.0) or 0.0 for c in aanroepen)
    tokens_in = sum(_kolom(c, "tokens_in", 0) or 0 for c in aanroepen)
    tokens_uit = sum(_kolom(c, "tokens_out", 0) or 0 for c in aanroepen)
    cache = sum(_kolom(c, "cached_in", 0) or 0 for c in aanroepen)
    uit += [
        "## Kosten", "",
        f"- {len(aanroepen)} betaalde aanroep(en), samen **{symbool}{totaal:.6f}**",
        f"- {tokens_in} invoertokens, waarvan {cache} uit cache; {tokens_uit} uitvoertokens",
        "",
    ]
    if aanroepen:
        uit += ["| # | fase | rol | model | in | cache | uit | kosten | verspild |",
                "|---|------|-----|-------|----|-------|-----|--------|----------|"]
        for c in aanroepen:
            verspild = _kolom(c, "wasted_reason", "") or ""
            uit.append(
                f"| {c['id']} | {_kolom(c, 'phase', '')} | {_kolom(c, 'role', '')}"
                f" | {_kolom(c, 'model', '')} | {_kolom(c, 'tokens_in', 0)}"
                f" | {_kolom(c, 'cached_in', 0)} | {_kolom(c, 'tokens_out', 0)}"
                f" | {symbool}{_kolom(c, 'cost_eur', 0.0) or 0.0:.6f} | {verspild} |"
            )
        uit.append("")

    uit += ["## Afwijkingen van het draaiboek", "",
            "_Waar de werkelijke stap afweek van de voorgeschreven stap._", ""]
    gebeurtenissen = scope.events(limit=100000)
    afwijkingen = [e for e in gebeurtenissen if e["kind"] in AFWIJKINGEN]
    if not afwijkingen:
        uit.append("Geen afwijkingen vastgelegd.")
    for e in reversed(afwijkingen):
        payload = e["payload"]
        try:
            gegevens = json.loads(payload) if payload else {}
        except (TypeError, ValueError):
            gegevens = {"ruw": payload}
        kort = ", ".join(f"{k}={str(v)[:160]}" for k, v in gegevens.items()) or "(geen details)"
        taak = f" taak #{e['task_id']}" if _kolom(e, "task_id") else ""
        uit.append(f"- `{e['ts']}` **{e['kind']}**{taak}: {kort}")
    uit.append("")

    uit += ["## Volledig gebeurtenissenlogboek", "",
            f"_{len(gebeurtenissen)} gebeurtenissen, oudste eerst._", ""]
    for e in reversed(gebeurtenissen):
        taak = f" #{e['task_id']}" if _kolom(e, "task_id") else ""
        uit.append(f"- `{e['ts']}`{taak} **{e['kind']}**")
    uit.append("")
    return "\n".join(uit)
