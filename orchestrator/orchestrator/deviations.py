"""Afwijkingen van een voorgeschreven verificatiestap.

De orchestrator mag van het draaiboek afwijken, maar nooit stilzwijgend. Elke
afwijking gaat in de audittrail met vijf verplichte velden. Ontbreekt er een,
dan wordt de afwijking geweigerd: een audittrail met een lege reden is geen
audittrail.

Een zuiver technische afwijking (een gelijkwaardige of strengere controle langs
een andere weg) hoeft niet vooraf gevraagd te worden. Raakt de afwijking
businesslogica, productie, geldbeslissingen, veiligheidsgrenzen of
onomkeerbare acties, dan blijft het BLOCK volgens de bestaande regels.

Bij twijfel blokkeren. Dat is dezelfde voorrangsregel als bij AUTO tegenover
PARK: de veilige kant wint.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import Enum

from .triage import FORBIDDEN_CATEGORIES


class DeviationOutcome(str, Enum):
    TECHNISCH = "technisch"      # geregistreerd, werk gaat door
    BLOKKEREND = "blokkerend"    # BLOCK, wacht op een beslissing van de mens


# Domeinen die een afwijking altijd blokkerend maken. Bewust ruim: het gaat om
# de vraag of een mens ernaar moet kijken, niet om een sluitende definitie.
_BLOKKERENDE_TERMEN = re.compile(
    r"\b("
    r"productie|production|deploy|deployment|release|live|"
    r"shopify|voorraad|stock|bestelling|order|"
    r"prijs|prijzen|pricing|korting|marge|geld|betaling|factuur|btw|"
    # "schema" alleen als databaseschema: een JSON-schema is onschuldig en
    # kwam in de eerste versie ten onrechte als blokkerend uit de test.
    r"migratie|migration|datamodel|drop|truncate|delete|verwijder|"
    r"merge|force[- ]push|rollback|onomkeerbaar|irreversible|"
    r"beveiliging|security|token|sleutel|credential|geheim|"
    r"persoonsgegeven|klantgegeven|privacy"
    r")\b"
    # Een databaseschema is riskant, een JSON-schema niet. Bare "schema"
    # blokkeerde in de eerste versie elke gewone technische afwijking:
    # een poort die altijd dichtslaat, beschermt niets meer.
    r"|\b(database|db|data|tabel)[- ]?schema\b"
    r"|\bschema(wijziging|migratie)\b",
    re.IGNORECASE,
)

_VERPLICHT = ("voorgeschreven", "uitgevoerd", "reden", "risico", "kosten")


class OnvolledigeAfwijking(ValueError):
    """Een afwijking zonder volledige verantwoording wordt niet geregistreerd."""


@dataclass(frozen=True)
class Deviation:
    """De vijf velden die een afwijking verantwoorden."""

    voorgeschreven: str   # welke stap het draaiboek voorschrijft
    uitgevoerd: str       # wat er werkelijk is gedaan
    reden: str            # waarom
    risico: str           # risico-impact
    kosten: str           # kostenimpact

    def __post_init__(self) -> None:
        leeg = [n for n in _VERPLICHT if not (getattr(self, n) or "").strip()]
        if leeg:
            raise OnvolledigeAfwijking(
                "afwijking mist verplichte verantwoording: " + ", ".join(leeg)
            )

    def as_payload(self) -> dict:
        return {n: getattr(self, n).strip() for n in _VERPLICHT}


def classify(deviation: Deviation, *, category: str | None = None) -> tuple[DeviationOutcome, str]:
    """Technisch of blokkerend? Geeft de uitkomst en de motivering terug."""
    if category and category.strip().lower() in FORBIDDEN_CATEGORIES:
        return (
            DeviationOutcome.BLOKKEREND,
            f"categorie {category.strip().lower()!r} valt onder de categorieen"
            " die nooit automatisch worden afgedaan",
        )
    # De hele verantwoording wordt bekeken, niet alleen de uitgevoerde stap:
    # een onschuldig ogende stap met een riskante reden blijft riskant.
    haystack = " ".join(deviation.as_payload().values())
    hit = _BLOKKERENDE_TERMEN.search(haystack)
    if hit:
        return (
            DeviationOutcome.BLOKKEREND,
            f"de afwijking raakt {hit.group(0).lower()!r};"
            " dat vraagt een beslissing van een mens",
        )
    return (
        DeviationOutcome.TECHNISCH,
        "zuiver technische afwijking; geregistreerd en voortgezet",
    )


def record(scope, deviation: Deviation, *, task_id: int | None = None,
           category: str | None = None) -> tuple[DeviationOutcome, str]:
    """Zet de afwijking in de audittrail en geef de uitkomst terug.

    Het registreren gebeurt altijd, ook als de uitkomst blokkerend is: juist
    dan moet er iets naar te wijzen zijn.
    """
    outcome, motivering = classify(deviation, category=category)
    payload = deviation.as_payload()
    payload["uitkomst"] = outcome.value
    payload["motivering"] = motivering
    if category:
        payload["categorie"] = category.strip().lower()
    scope.log("afwijking", payload, task_id=task_id)
    return outcome, motivering


def format_deviation(row) -> str:
    """Een regel uit de audittrail leesbaar maken."""
    payload = row["payload"] if isinstance(row["payload"], dict) else json.loads(row["payload"])
    regels = [f"[{row['ts']}] afwijking — {payload.get('uitkomst', '?')}"]
    etiketten = {
        "voorgeschreven": "voorgeschreven",
        "uitgevoerd": "uitgevoerd",
        "reden": "reden",
        "risico": "risico-impact",
        "kosten": "kostenimpact",
        "motivering": "motivering",
    }
    for sleutel, etiket in etiketten.items():
        if payload.get(sleutel):
            regels.append(f"  {etiket:16} {payload[sleutel]}")
    return "\n".join(regels)
