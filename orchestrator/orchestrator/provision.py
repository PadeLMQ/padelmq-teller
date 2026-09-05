"""Projecten op een vers volume zetten.

Een container start met een leeg volume. De projectconfiguratie stond alleen
op de schijf van de machine waar ooit 'project add' is gedraaid, en op Railway
is er geen shell waar dat vanzelfsprekend gebeurt. Gevolg: nul projecten, en
serve die netjes afsluit omdat er niets te doen is. Precies dezelfde soort
fout als de vorige: alles groen, niets draait.

Daarom kan de projectlijst uit een omgevingsvariabele komen. Twee regels
maken dit veilig:

1. Bestaat een project al op het volume, dan blijft het zoals het is. Het
   volume is de waarheid zodra het bestaat; anders zou een oude variabele
   later stilletjes wijzigingen terugdraaien.
2. Wat er niet in staat, wordt niet verzonnen. Ontbreekt 'slug', dan is dat
   een fout met een leesbare melding, geen aanname.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

from . import projects as projects_mod
from .projects import ProjectError

VARIABELE = "ORCH_PROJECTS"


class ProvisionError(RuntimeError):
    pass


@dataclass
class Uitkomst:
    aangemaakt: list[str]
    bestond: list[str]

    def regels(self) -> list[str]:
        uit = [f"project {slug} aangemaakt op het volume" for slug in self.aangemaakt]
        uit += [f"project {slug} stond er al; ongewijzigd gelaten" for slug in self.bestond]
        return uit


def _ontleed(ruw: str) -> list[dict]:
    ruw = (ruw or "").strip()
    if not ruw:
        return []
    try:
        data = json.loads(ruw)
    except json.JSONDecodeError as exc:
        raise ProvisionError(
            f"{VARIABELE} is geen geldige JSON: {exc.msg} (regel {exc.lineno},"
            f" teken {exc.colno})"
        ) from exc
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        raise ProvisionError(f"{VARIABELE} moet een lijst met projecten zijn")
    for item in data:
        if not isinstance(item, dict):
            raise ProvisionError(f"{VARIABELE}: {item!r} is geen project-object")
    return data


def provision(settings, ruw: str | None = None, *, repos_dir: str | None = None) -> Uitkomst:
    """Maakt ontbrekende projecten aan; laat bestaande met rust."""
    items = _ontleed(os.environ.get(VARIABELE, "") if ruw is None else ruw)
    basis = repos_dir or os.environ.get("ORCH_REPOS", "")
    bestaand = set(projects_mod.list_projects(settings))
    uitkomst = Uitkomst(aangemaakt=[], bestond=[])

    for item in items:
        slug = str(item.get("slug") or "").strip()
        if not slug:
            raise ProvisionError(f"{VARIABELE}: een project zonder 'slug': {item!r}")
        if slug in bestaand:
            uitkomst.bestond.append(slug)
            continue
        # Zonder expliciet pad hoort de kloon op het volume te staan. Ergens
        # anders zou hij bij elke herstart weg zijn.
        repo = str(item.get("repo") or "").strip()
        if not repo:
            if not basis:
                raise ProvisionError(
                    f"{VARIABELE}: project {slug!r} heeft geen 'repo' en"
                    " ORCH_REPOS is niet gezet, dus ik weet niet waar de kloon hoort"
                )
            repo = f"{basis.rstrip('/')}/{slug}"
        try:
            projects_mod.add(
                settings, slug, repo,
                checks=dict(item.get("checks") or {}),
                post_checks=dict(item.get("post_checks") or {}),
                github_repo=str(item.get("github_repo") or ""),
                default_branch=str(item.get("default_branch") or "main"),
            )
        except ProjectError as exc:
            raise ProvisionError(f"{VARIABELE}: project {slug!r}: {exc}") from exc
        uitkomst.aangemaakt.append(slug)
    return uitkomst
