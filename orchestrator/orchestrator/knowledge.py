"""De projectkennisbasis.

Platte markdown-bestanden met een vast kopformaat, zodat jij ze kunt lezen en
corrigeren en beide modellen dezelfde bron zien.

Formaat van een item::

    ## D-014 · Btw-behandeling op de teller
    status: bevestigd
    datum: 2026-09-05
    bron: antwoord op issue #12

    Bedragen op de teller zijn inclusief btw.

Harde regel: de status ``bevestigd`` ontstaat uitsluitend door een antwoord van
de mens. ``append_decision`` weigert een andere herkomst. Een model kan de
kennisbasis dus niet zelf tot waarheid verheffen.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .models import ItemStatus, now

FILES = (
    "doel.md",
    "architectuur.md",
    "beslissingen.md",
    "businessregels.md",
    "voorkeuren.md",
    "verboden.md",
    "problemen.md",
    "open.md",
    "historie.md",
    "woordenlijst.md",
)

_HEADING = re.compile(r"^##\s+(?P<id>[A-Za-z0-9][A-Za-z0-9._-]*)\s*(?:·|-|—)?\s*(?P<title>.*)$")
_META = re.compile(r"^(?P<key>status|datum|bron|vervangt|categorie)\s*:\s*(?P<value>.*)$", re.I)


class KnowledgeError(RuntimeError):
    pass


@dataclass
class Item:
    item_id: str
    title: str
    body: str
    status: ItemStatus
    source: str = ""
    date: str = ""
    category: str = ""
    file: str = ""

    @property
    def citable(self) -> bool:
        return self.status.citable and bool(self.body.strip())


@dataclass
class KnowledgeStore:
    root: Path
    _cache: dict[str, Item] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        self.root = Path(self.root)

    # -- aanmaken --------------------------------------------------------
    def scaffold(self, project_slug: str) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        headers = {
            "doel.md": "Wat dit project is en moet bereiken.",
            "architectuur.md": "Huidige opzet en status.",
            "beslissingen.md": "Append-only logboek van genomen beslissingen.",
            "businessregels.md": "Regels die het gedrag bepalen: prijzen, btw, limieten.",
            "voorkeuren.md": "Vaste keuzes in stijl, stack en werkwijze.",
            "verboden.md": "Aannames die nooit gemaakt mogen worden.",
            "problemen.md": "Bekende problemen en hun status.",
            "open.md": "Openstaande beslissingen.",
            "historie.md": "Belangrijke context die elders niet past.",
            "woordenlijst.md": "Projecttaal, zodat beide modellen hetzelfde bedoelen.",
        }
        for name in FILES:
            path = self.root / name
            if not path.exists():
                path.write_text(
                    f"# {project_slug} — {name[:-3]}\n\n_{headers[name]}_\n\n"
                    "<!-- Items krijgen de vorm:  ## <id> · <titel>  met daaronder "
                    "status/datum/bron en de tekst. -->\n",
                    encoding="utf-8",
                )

    # -- lezen -----------------------------------------------------------
    def load(self) -> dict[str, Item]:
        items: dict[str, Item] = {}
        if not self.root.exists():
            return items
        for name in sorted(p.name for p in self.root.glob("*.md")):
            for item in self._parse_file(self.root / name):
                if item.item_id in items:
                    raise KnowledgeError(
                        f"dubbel item-id {item.item_id!r} in {name} en {items[item.item_id].file}"
                    )
                items[item.item_id] = item
        self._cache = items
        return items

    def _parse_file(self, path: Path) -> list[Item]:
        items: list[Item] = []
        current: dict | None = None
        body: list[str] = []

        def flush() -> None:
            if current is None:
                return
            raw_status = (current.get("status") or "te bevestigen").strip().lower()
            try:
                status = ItemStatus(raw_status)
            except ValueError:
                status = ItemStatus.TO_CONFIRM
            items.append(
                Item(
                    item_id=current["id"],
                    title=current["title"].strip(),
                    body="\n".join(body).strip(),
                    status=status,
                    source=current.get("bron", ""),
                    date=current.get("datum", ""),
                    category=current.get("categorie", ""),
                    file=path.name,
                )
            )

        for line in path.read_text(encoding="utf-8").splitlines():
            heading = _HEADING.match(line)
            if heading:
                flush()
                current = {"id": heading.group("id"), "title": heading.group("title")}
                body = []
                continue
            if current is None:
                continue
            meta = _META.match(line.strip())
            if meta and not body:
                current[meta.group("key").lower()] = meta.group("value").strip()
                continue
            body.append(line)
        flush()
        return items

    def get(self, item_id: str) -> Item | None:
        if not self._cache:
            self.load()
        return self._cache.get(item_id)

    def search(self, text: str, limit: int = 20) -> list[Item]:
        if not self._cache:
            self.load()
        words = [w for w in re.split(r"\W+", text.lower()) if len(w) > 3]
        scored = []
        for item in self._cache.values():
            haystack = f"{item.title} {item.body}".lower()
            score = sum(1 for w in words if w in haystack)
            if score:
                scored.append((score, item))
        scored.sort(key=lambda pair: (-pair[0], pair[1].item_id))
        return [item for _, item in scored[:limit]]

    def forbidden_topics(self) -> list[str]:
        """Regels uit verboden.md — nooit automatisch beantwoorden."""
        if not self._cache:
            self.load()
        return [
            f"{i.title} {i.body}".lower()
            for i in self._cache.values()
            if i.file == "verboden.md"
        ]

    def as_prompt_context(self, max_chars: int = 20000) -> str:
        """De context die naar de reviewer gaat.

        Bevestigde items gaan volledig mee: alleen die mogen als bron dienen
        voor een automatisch antwoord. Van de rest gaat alleen de titel mee, met
        de status erbij. Zo weet de reviewer dát die kennis bestaat — hij kan er
        zelfs naar vragen — maar we betalen niet voor tekst die toch nooit een
        AUTO kan dragen. Weglaten zou de betrouwbaarheid schaden; volledig
        meesturen is verspilling.
        """
        if not self._cache:
            self.load()
        bevestigd: list[str] = []
        overig: list[str] = []
        for item in sorted(self._cache.values(), key=lambda i: (i.file, i.item_id)):
            if item.citable:
                bevestigd.append(
                    f"[{item.item_id}] ({item.status.value}) {item.title}\n{item.body}".strip()
                )
            else:
                overig.append(f"[{item.item_id}] ({item.status.value}) {item.title}")

        delen = []
        if bevestigd:
            delen.append("BEVESTIGDE PROJECTKENNIS — alleen hieruit mag je citeren:\n\n"
                         + "\n\n".join(bevestigd))
        if overig:
            delen.append(
                "NIET BEVESTIGD — bestaat wel, maar mag NOOIT als bron dienen. "
                "Is het antwoord hiervan afhankelijk, meld dat dan in plaats van te "
                "antwoorden:\n"
                + "\n".join(overig)
            )
        return "\n\n".join(delen)[:max_chars]

    # -- schrijven -------------------------------------------------------
    def next_decision_id(self) -> str:
        if not self._cache:
            self.load()
        numbers = [
            int(m.group(1))
            for key in self._cache
            if (m := re.fullmatch(r"D-(\d+)", key))
        ]
        return f"D-{(max(numbers) + 1) if numbers else 1:03d}"

    def append_decision(
        self, title: str, body: str, *, source: str, confirmed_by_human: bool
    ) -> str:
        """Voegt een beslissing toe. Alleen een mens levert 'bevestigd' op.

        Een model dat dit aanroept krijgt status 'te bevestigen' en daarmee een
        item dat niet als bron voor een automatisch antwoord mag dienen.
        """
        if confirmed_by_human and not source.strip():
            raise KnowledgeError("een bevestigde beslissing moet een bron vermelden")
        status = ItemStatus.CONFIRMED if confirmed_by_human else ItemStatus.TO_CONFIRM
        item_id = self.next_decision_id()
        path = self.root / "beslissingen.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        existing = path.read_text(encoding="utf-8") if path.exists() else ""
        block = (
            f"\n## {item_id} · {title.strip()}\n"
            f"status: {status.value}\n"
            f"datum: {now()[:10]}\n"
            f"bron: {source.strip() or 'onbekend'}\n\n"
            f"{body.strip()}\n"
        )
        path.write_text(existing.rstrip() + "\n" + block, encoding="utf-8")
        self._cache = {}
        return item_id

    def supersede(self, item_id: str, replaced_by: str) -> None:
        """Markeert een item als vervallen. Alleen na een bevestigd nieuw besluit.

        De tekst van het item blijft staan: de historie is juist waarom je dit
        wilt vastleggen in plaats van overschrijven.
        """
        item = self.get(item_id)
        if item is None:
            raise KnowledgeError(f"onbekend item {item_id!r}")
        path = self.root / item.file
        text = path.read_text(encoding="utf-8")

        # Alleen de statusregel van DIT item vervangen. Een eerdere versie
        # gebruikte re.S, waardoor '.' ook nieuwe regels ving en de rest van het
        # bestand werd opgeslokt -- inclusief alle items eronder.
        patroon = re.compile(
            rf"(?P<kop>^##[ \t]+{re.escape(item_id)}\b[^\n]*\n)"
            rf"(?P<status>[ \t]*status[ \t]*:[^\n]*\n)"
            rf"(?P<vervangt>[ \t]*vervangt[ \t]*:[^\n]*\n)?",
            re.M | re.I,
        )

        def vervang(m: re.Match) -> str:
            return (
                m.group("kop")
                + f"status: {ItemStatus.SUPERSEDED.value}\n"
                + f"vervangt: {replaced_by}\n"
            )

        nieuwe_tekst, aantal = patroon.subn(vervang, text, count=1)
        if not aantal:
            raise KnowledgeError(
                f"kon de statusregel van {item_id!r} niet vinden in {item.file}"
            )
        if len(nieuwe_tekst) < len(text) * 0.9:
            # Zekerheid boven elegantie: verliest deze bewerking meer dan een
            # tiende van het bestand, dan klopt er iets niet en schrijven we niet.
            raise KnowledgeError(
                f"supersede van {item_id!r} zou het grootste deel van {item.file}"
                " wissen; niet uitgevoerd"
            )
        path.write_text(nieuwe_tekst, encoding="utf-8")
        self._cache = {}
