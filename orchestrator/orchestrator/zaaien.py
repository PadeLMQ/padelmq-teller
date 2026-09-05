"""Kennis meegeven aan een vers volume, eenmalig.

Een container start met een leeg volume, dus met een lege kennisbasis. Alles
wat de eigenaar ooit heeft bevestigd -- welke checks hard zijn, wat nooit
automatisch mag -- zou daarmee weg zijn. Een orkestrator zonder die kennis
stelt vragen die al beantwoord zijn, of erger: hij kent de verboden niet.

Het zaaigoed staat in de repository van het project zelf, onder
`.orchestrator/kennis/`. Dat heeft drie voordelen boven een kopie op een
willekeurige schijf: het is versiebeheerd, het is te lezen en te corrigeren via
een pull request, en het erft de zichtbaarheid van dat project. Kennis over een
privéproject blijft daarmee privé.

Drie regels maken dit veilig, en ze zijn geen van drieën optioneel:

1. Zaaien gebeurt één keer. Daarna ligt er een merkteken en gebeurt het nooit
   meer, ook niet na een herstart of een nieuwe deploy.
2. Een bestand dat al kennis bevat wordt nooit overschreven. Het volume is de
   werkelijkheid; het zaaigoed is alleen een beginpunt.
3. Zaaigoed met iets dat op een geheim lijkt wordt in zijn geheel geweigerd.
   Een repository is te bewerken door iedereen met schrijfrechten.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .knowledge import FILES, KnowledgeStore
from .models import now
from .secret_scan import format_hits, scan_text

MERKTEKEN = ".geseed"
BRONMAP = Path(".orchestrator") / "kennis"


class ZaaiGeweigerd(RuntimeError):
    """Het zaaigoed deugt niet; er is niets geschreven."""


@dataclass
class Uitkomst:
    geschreven: list[str] = field(default_factory=list)
    overgeslagen: list[str] = field(default_factory=list)
    reden: str = ""

    def regels(self) -> list[str]:
        if self.reden:
            return [self.reden]
        uit = [f"kennis gezaaid: {', '.join(self.geschreven)}"] if self.geschreven else []
        uit += [f"ongemoeid gelaten (bevat al kennis): {n}" for n in self.overgeslagen]
        return uit or ["geen zaaigoed gevonden"]


def _bevat_kennis(pad: Path) -> bool:
    """Staat er al een item in? Een vers sjabloon heeft er nul.

    Bewust op items en niet op bytes: het sjabloon mag van tekst veranderen
    zonder dat dit onbedoeld iets als 'gewijzigd' gaat zien.
    """
    if not pad.is_file():
        return False
    winkel = KnowledgeStore(pad.parent)
    return any(item.file == pad.name for item in winkel.load().values())


def zaai(kennis_map: Path, bron: Path) -> Uitkomst:
    """Vult een lege kennisbasis met het zaaigoed uit de projectrepository."""
    merkteken = kennis_map / MERKTEKEN
    if merkteken.exists():
        return Uitkomst(reden=f"kennis is eerder al gezaaid ({merkteken.read_text().strip()})")
    if not bron.is_dir():
        return Uitkomst(reden=f"geen zaaigoed in {bron}")

    # Eerst alles inlezen en controleren, dan pas schrijven. Half zaaien zou
    # een kennisbasis achterlaten waarvan niemand weet wat er wel en niet in zit.
    te_schrijven: dict[str, str] = {}
    overgeslagen: list[str] = []
    for naam in FILES:
        bronbestand = bron / naam
        if not bronbestand.is_file():
            continue
        tekst = bronbestand.read_text(encoding="utf-8")
        treffers = scan_text(str(bronbestand), tekst)
        if treffers:
            raise ZaaiGeweigerd(
                "zaaigoed bevat mogelijk een geheim; er is niets geschreven:\n"
                + format_hits(treffers)
            )
        if _bevat_kennis(kennis_map / naam):
            overgeslagen.append(naam)
            continue
        te_schrijven[naam] = tekst

    kennis_map.mkdir(parents=True, exist_ok=True)
    for naam, tekst in te_schrijven.items():
        (kennis_map / naam).write_text(tekst, encoding="utf-8")
    merkteken.write_text(
        f"{now()} — {len(te_schrijven)} bestand(en) uit {bron}\n", encoding="utf-8"
    )
    return Uitkomst(geschreven=sorted(te_schrijven), overgeslagen=overgeslagen)
