"""Wat je in de logs ziet als de dienst opkomt.

Railway meldde "Online / Active" terwijl er in werkelijkheid niets van de
orkestrator draaide. Dat is de gevaarlijkste toestand die er is: een groen
lampje boven een dienst die niets doet. De les is niet "meer loggen" maar
"ondubbelzinnig loggen": bij elke start hoort er een regel te staan die
ofwel OK ofwel FOUT zegt, per onderdeel, zonder dat je die conclusie zelf
uit stilte moet afleiden.

Elke controle krijgt zijn afhankelijkheden mee. Zo kan een test het hele
rapport doorlopen zonder netwerk, zonder sleutels en zonder kosten.

Geheimen komen hier nooit in beeld. Waar bewijs nodig is dat overal dezelfde
sleutel staat, gebruiken we de vingerafdruk uit cli._sleutel_status, nooit de
waarde zelf.
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from .redact import redact_text

MARKER = "opstart-marker.txt"


@dataclass
class Controle:
    naam: str
    ok: bool
    detail: str
    # Een niet-fatale controle mag rood zijn zonder de start tegen te houden:
    # de dienst kan nuttig werk doen zonder e-mail, maar niet zonder git.
    fataal: bool = True

    @property
    def symbool(self) -> str:
        return "OK  " if self.ok else "FOUT"


@dataclass
class Rapport:
    controles: list[Controle] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(c.ok for c in self.controles if c.fataal)

    def falend(self) -> list[Controle]:
        return [c for c in self.controles if not c.ok]


def controleer_datamap(pad: Path) -> Controle:
    """Bestaat de datamap, is hij beschrijfbaar, en overleeft hij een herstart?

    Het derde is het punt. Een map die bij elke deploy leeg is, is geen volume
    maar containerschijf: de takendatabase zou dan stilletijk verdwijnen. We
    laten daarom bij elke start een merkteken achter en melden of dat van een
    vorige start al bestond. Dat is bewijs in plaats van vertrouwen.
    """
    try:
        pad.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return Controle("datamap", False, f"{pad} kan niet worden aangemaakt: {exc}")

    marker = pad / MARKER
    eerder = marker.exists()
    vorige = ""
    if eerder:
        try:
            vorige = marker.read_text().strip().splitlines()[0]
        except (OSError, IndexError):
            vorige = "(onleesbaar)"
    from .models import now

    try:
        marker.write_text(f"{now()}\nhost={socket.gethostname()}\npid={os.getpid()}\n")
    except OSError as exc:
        return Controle("datamap", False, f"{pad} is niet beschrijfbaar: {exc}")

    if eerder:
        return Controle("datamap", True,
                        f"{pad} beschrijfbaar; blijft behouden (vorige start {vorige})")
    # Geen merkteken kan twee dingen betekenen: eerste start ooit, of een volume
    # dat niets bewaart. Dat verschil kunnen we nu nog niet zien, dus zeggen we
    # het eerlijk in plaats van te kiezen.
    return Controle("datamap", True,
                    f"{pad} beschrijfbaar; nog geen merkteken van een vorige start "
                    "(eerste start, of het volume bewaart niets - de volgende "
                    "start wijst het uit)")


def controleer_github(client_factory, repos: list[str] | None = None) -> Controle:
    """Werkt de GitHub-authenticatie echt?

    Kijken of ORCH_GITHUB_TOKEN gezet is bewijst niets: een verlopen of
    ingetrokken token haalt die test even goed. We vragen daarom wie we zijn.
    Alleen de login komt in de log, nooit de token.
    """
    try:
        client = client_factory()
        wie = client.whoami()
    except Exception as exc:  # noqa: BLE001 - elke fout is hier een probleem
        return Controle("github-auth", False,
                        redact_text(f"{type(exc).__name__}: {str(exc)[:160]}"))
    doel = f", repo's: {', '.join(repos)}" if repos else ""
    return Controle("github-auth", True, f"geauthenticeerd als {wie}{doel}")


def controleer_openai(auth_fn) -> Controle:
    ok, detail = auth_fn()
    return Controle("openai", ok, redact_text(detail))


def controleer_claude(run=subprocess.run, which=shutil.which) -> Controle:
    """Staat de Claude CLI er, en start hij?

    'in PATH' is niet genoeg: een half geinstalleerde npm-package staat wel in
    PATH en valt om zodra je hem aanroept. --version kost niets en bewijst meer.
    """
    pad = which("claude")
    if pad is None:
        return Controle("claude-cli", False, "'claude' staat niet in PATH")
    try:
        uit = run(["claude", "--version"], capture_output=True, text=True, timeout=60)
    except Exception as exc:  # noqa: BLE001
        return Controle("claude-cli", False, f"{pad}: {type(exc).__name__}: {exc}")
    if uit.returncode != 0:
        melding = (uit.stderr or uit.stdout or "").strip().splitlines()
        return Controle("claude-cli", False,
                        f"{pad} gaf exitcode {uit.returncode}: "
                        f"{redact_text(melding[0] if melding else '(geen uitvoer)')}")
    return Controle("claude-cli", True, f"{pad}: {(uit.stdout or '').strip()[:80]}")


def controleer_doctor(doctor_fn) -> Controle:
    """doctor draait dezelfde controles als met de hand; hier alleen de uitkomst."""
    try:
        code = doctor_fn()
    except Exception as exc:  # noqa: BLE001
        return Controle("doctor", False, f"{type(exc).__name__}: {str(exc)[:160]}")
    if code == 0:
        return Controle("doctor", True, "alle controles geslaagd")
    return Controle("doctor", False,
                    f"exitcode {code}; zie de regels met '!' hierboven")


def format_rapport(rapport: Rapport, *, versie: str, kop: str = "opstart") -> str:
    """De regels die in Railway's log komen te staan.

    Vast formaat, want dit wordt door mensen onder tijdsdruk gelezen: links het
    onderdeel, dan OK of FOUT, dan waarom.
    """
    regels = [f"===== {kop} (orchestrator {versie}) ====="]
    for c in rapport.controles:
        regels.append(f"[{c.symbool}] {c.naam:<12} {c.detail}")
    if rapport.ok:
        regels.append("[OK  ] opstart      alle noodzakelijke controles geslaagd")
    else:
        namen = ", ".join(c.naam for c in rapport.falend() if c.fataal)
        regels.append(f"[FOUT] opstart      geblokkeerd door: {namen}")
    regels.append("=" * len(regels[0]))
    return "\n".join(regels)


def hartslagregel(ronde_nummer: int, ronde, *, tijd: str, interval: int) -> str:
    """Eén regel per ronde, ook als er niets gebeurde.

    Juist de stille rondes moeten zichtbaar zijn: zonder die regel is een dienst
    die niets te doen heeft niet te onderscheiden van een dienst die dood is.
    """
    werk = (f"hersteld={ronde.hersteld} binnengekomen={ronde.antwoorden} "
            f"taken={ronde.taken} fouten={ronde.fouten}")
    staat = "stil" if ronde.stil else "werk gedaan"
    return f"[HART] ronde {ronde_nummer} {tijd} {staat}; {werk}; volgende over {interval}s"


def controleer_projecten(slugs: list[str], map_pad) -> Controle:
    """Nul projecten is geen rust, het is een verkeerd geconfigureerde dienst.

    Op een vers volume staat er niets. Zonder deze controle komt de dienst op,
    heeft niets te doen, sluit netjes af, en meldt Railway "Completed" - groen,
    en volkomen misleidend.
    """
    if not slugs:
        return Controle("projecten", False,
                        f"geen enkel project in {map_pad}; zet ORCH_PROJECTS in de "
                        "omgeving of draai 'orchestrator project add'")
    return Controle("projecten", True, f"{len(slugs)}: {', '.join(slugs)}")
