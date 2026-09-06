"""Afhankelijkheden installeren voordat er geverifieerd wordt.

Een verse worktree bevat de broncode, maar niet `node_modules`. De checks
draaien daar dan niet op een fout in het werk stuk, maar op een lege omgeving.
Dat verschil kostte in de pilot al geld: defect D-10, exitcode 127 gelezen als
kapot werk, $0,296538 voor niets.

De orkestrator kan dat niet zelf verzinnen -- welk commando een project nodig
heeft verschilt per project -- dus staat het in de projectconfiguratie. Wat
hier wel wordt afgedwongen: het commando gaat door dezelfde veiligheidspoort
als een verificatiecheck, en het draait niet vaker dan nodig.

Vaker dan nodig is niet gratis: `npm ci` gooit `node_modules` weg en
installeert opnieuw. Daarom een merkteken met daarin het commando én een
vingerafdruk van de lockbestanden. Verandert een van beide, dan wordt er
opnieuw geinstalleerd; anders niet.

Dat merkteken staat met opzet BUITEN de werkmap. Een bestand in de repository
zou door `git add -A` in de commit belanden en daarmee in de pull request --
een spoor van de orkestrator in het werk van de gebruiker, en precies het soort
rommel dat een diff onleesbaar maakt.
"""

from __future__ import annotations

import hashlib
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .verify import assert_safe_checks

def merkteken_voor(state_dir: Path, pad: Path) -> Path:
    """Waar het merkteken van deze map staat: in de projectstaat, niet in de repo."""
    sleutel = hashlib.sha256(str(Path(pad).resolve()).encode()).hexdigest()[:16]
    return Path(state_dir) / f"voorbereid-{sleutel}"

# Bestanden die zeggen "de afhankelijkheden zijn veranderd". Bewust een korte,
# expliciete lijst: raden welk bestand ertoe doet levert of te vaak werk op, of
# een omgeving die stilletjes achterloopt.
LOCKBESTANDEN = (
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "npm-shrinkwrap.json",
    "requirements.txt", "poetry.lock", "uv.lock", "Pipfile.lock",
    "go.sum", "Cargo.lock", "composer.lock",
)


class VoorbereidingMislukt(RuntimeError):
    """De omgeving kon niet klaargezet worden. Dat is geen rode verificatie."""


@dataclass
class Uitkomst:
    gedraaid: bool
    reden: str
    uitvoer: str = ""


def _vingerafdruk(pad: Path, commando: str) -> str:
    haas = hashlib.sha256(commando.encode())
    for naam in LOCKBESTANDEN:
        bestand = pad / naam
        if bestand.is_file():
            haas.update(naam.encode())
            haas.update(bestand.read_bytes())
    return haas.hexdigest()


def zorg_voor(pad: Path, commando: str, *, state_dir: Path,
              timeout: int = 1800, run=subprocess.run) -> Uitkomst:
    """Zorgt dat deze map klaar is om de checks te draaien."""
    if not commando.strip():
        return Uitkomst(False, "geen voorbereidingscommando ingesteld")

    # Dezelfde poort als voor een check: een omgevingscommando is geen
    # achterdeur om alsnog een bedrijfsactie te draaien.
    assert_safe_checks({"voorbereiding": commando})

    merkteken = merkteken_voor(state_dir, pad)
    merkteken.parent.mkdir(parents=True, exist_ok=True)
    wil = _vingerafdruk(pad, commando)
    if merkteken.is_file() and merkteken.read_text().strip() == wil:
        return Uitkomst(False, "afhankelijkheden zijn al klaargezet")

    try:
        uit = run(commando, shell=True, cwd=str(pad), capture_output=True,
                  text=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise VoorbereidingMislukt(
            f"{commando!r} overschreed {timeout}s in {pad}"
        ) from exc
    except OSError as exc:
        raise VoorbereidingMislukt(f"{commando!r} kon niet starten: {exc}") from exc

    uitvoer = ((uit.stdout or "") + (uit.stderr or "")).strip()
    if uit.returncode != 0:
        raise VoorbereidingMislukt(
            f"{commando!r} gaf exitcode {uit.returncode} in {pad}:\n{uitvoer[-4000:]}"
        )
    merkteken.write_text(wil)
    return Uitkomst(True, "afhankelijkheden geinstalleerd", uitvoer[-4000:])
