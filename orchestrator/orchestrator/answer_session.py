"""Kanaalonafhankelijke afhandeling van een menselijk antwoord op een BLOCK.

Eén machine voor alle kanalen. GitHub, e-mail en spraak zijn transportlagen; de
regels over wanneer een antwoord voldoende is, staan hier en nergens anders.
Zo hoeft er niets herbouwd te worden wanneer spraak erbij komt.

De harde regel: een transcriptie is nooit vanzelf voldoende. Bij een slechte
opname, meerdere mogelijke lezingen of een onvolledig antwoord wordt er
doorgevraagd of blijft de BLOCK staan. Er wordt nooit iets aangevuld of geraden.
"""

from __future__ import annotations

import enum
import re
from dataclasses import dataclass, field
from typing import Protocol

from .db import ProjectScope

MIN_CONFIDENCE = 0.75
MIN_WOORDEN = 1
MAX_VERDUIDELIJKINGEN = 1  # vraag → antwoord → één verduidelijking → antwoord → klaar

_JA = re.compile(r"^\s*(ja|jawel|klopt|akkoord|correct|prima|juist|yes|ok|oké|okay)\b", re.I)
_NEE = re.compile(r"^\s*(nee|neen|niet|onjuist|fout|verkeerd|no)\b", re.I)
_WEET_NIET = re.compile(
    r"\b(weet ik niet|geen idee|dat weet ik niet|later|straks|overslaan|skip)\b", re.I
)


class Clarity(str, enum.Enum):
    CLEAR = "eenduidig"
    EMPTY = "leeg"
    LOW_CONFIDENCE = "slecht verstaan"
    MULTIPLE = "meerdere lezingen"
    INCOMPLETE = "onvolledig"
    DEFERRED = "uitgesteld"

    @property
    def usable(self) -> bool:
        return self is Clarity.CLEAR


class SessionState(str, enum.Enum):
    ASKED = "asked"
    AWAITING_CLARIFICATION = "awaiting_clarification"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    RESOLVED = "resolved"
    RETURNED_TO_BLOCK = "returned_to_block"


class Act(str, enum.Enum):
    """Wat het kanaal nu moet doen."""

    ASK_CLARIFICATION = "stel de verduidelijkingsvraag"
    ASK_CONFIRMATION = "vraag om bevestiging"
    APPLY = "leg de beslissing vast en hervat"
    KEEP_BLOCKED = "houd de blokkade en meld het"


@dataclass
class Interpretation:
    """Wat een lezer van het antwoord ervan maakt."""

    text: str
    unambiguous: bool = True
    alternatives: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)


class Interpreter(Protocol):
    """Leest een open antwoord. Mag nooit aanvullen wat er niet gezegd is."""

    def interpret(self, *, question: str, options: list[str], transcript: str
                  ) -> Interpretation: ...


@dataclass
class GateResult:
    clarity: Clarity
    interpretation: str | None = None
    clarification: str | None = None
    reason: str = ""


def _woorden(text: str) -> list[str]:
    return [w for w in re.split(r"\W+", text.strip()) if w]


def match_options(transcript: str, options: list[str]) -> list[str]:
    """Deterministisch: welke van de aangeboden opties noemt dit antwoord?

    Eerst exact op de hele optietekst, anders op onderscheidende woorden. Geen
    model nodig, en dus geen ruimte om iets te verzinnen.
    """
    # Leestekens worden spaties: zonder dit valt "exclusief," buiten de match en
    # zou een antwoord dat twee opties noemt als eenduidig doorgaan.
    lowered = " " + re.sub(r"\W+", " ", transcript.lower()).strip() + " "

    def genormaliseerd(text: str) -> str:
        return re.sub(r"\W+", " ", text.lower()).strip()

    exact = [o for o in options if f" {genormaliseerd(o)} " in lowered]
    if exact:
        return exact

    gemeenschappelijk: set[str] = set()
    per_optie: list[tuple[str, set[str]]] = []
    for option in options:
        woorden = {w.lower() for w in _woorden(option) if len(w) > 2}
        per_optie.append((option, woorden))
    for _, woorden in per_optie:
        gemeenschappelijk |= {
            w for w in woorden if sum(1 for _, andere in per_optie if w in andere) > 1
        }

    treffers = []
    for option, woorden in per_optie:
        onderscheidend = woorden - gemeenschappelijk
        if onderscheidend and any(f" {w} " in lowered for w in onderscheidend):
            treffers.append(option)
    return treffers



def _normaliseer(text: str) -> str:
    """Kleine letters, leestekens als spatie, spaties samengevouwen."""
    return re.sub(r"\s+", " ", re.sub(r"\W+", " ", (text or "").lower())).strip()


def exacte_optiekeuze(transcript: str, options: list[str]) -> str | None:
    """Wijst dit antwoord zonder enige interpretatie precies één optie aan?

    Alleen dan mag de bevestigingsronde overgeslagen worden. Dat is een strengere
    eis dan match_options(), dat ook op onderscheidende woorden matcht -- en
    woorden herkennen is inferentie, hoe deterministisch de code ook is.

    Wat telt:
      - een optienummer op zichzelf: "2", "optie 2", "2."
      - letterlijk de tekst van precies één optie

    Wat niet telt, en dus wél bevestigd moet worden:
      - "1 en 2", "niet 1", "2 maar alleen als ..." -- het antwoord is meer dan
        een keuze
      - "ja" terwijl de optie "Ja, waarschuwingen laten falen" heet -- dat is een
        samenvatting, geen exacte keuze
      - vrije tekst, extra voorwaarden, of iets wat op twee opties past

    Geeft None terug zodra er ook maar iets te interpreteren valt. Geen model
    betrokken: dit is een string die precies past of niet.
    """
    if not options:
        return None
    kaal = _normaliseer(transcript)
    if not kaal:
        return None

    nummer = re.fullmatch(r"(?:optie |keuze |nummer )?(\d{1,2})", kaal)
    if nummer:
        index = int(nummer.group(1))
        if 1 <= index <= len(options):
            return options[index - 1]
        return None

    treffers = [o for o in options if _normaliseer(o) == kaal]
    return treffers[0] if len(treffers) == 1 else None


def assess(
    *,
    question: str,
    options: list[str],
    transcript: str,
    confidence: float | None = None,
    interpreter: Interpreter | None = None,
    min_confidence: float = MIN_CONFIDENCE,
) -> GateResult:
    """De ondubbelzinnigheidspoort. Deterministisch waar het kan."""
    tekst = (transcript or "").strip()

    if not tekst or len(_woorden(tekst)) < MIN_WOORDEN:
        return GateResult(
            Clarity.EMPTY,
            clarification="Ik heb niets verstaan. Wil je het antwoord herhalen?",
            reason="leeg antwoord",
        )

    if _WEET_NIET.search(tekst):
        return GateResult(
            Clarity.DEFERRED,
            reason="je gaf aan het nu niet te beslissen",
        )

    if confidence is not None and confidence < min_confidence:
        return GateResult(
            Clarity.LOW_CONFIDENCE,
            clarification=(
                "Ik verstond je niet goed genoeg. Kun je het antwoord herhalen, "
                "graag wat langzamer?"
            ),
            reason=f"transcriptiezekerheid {confidence:.2f} onder {min_confidence:.2f}",
        )

    if options:
        treffers = match_options(tekst, options)
        if len(treffers) == 1:
            return GateResult(Clarity.CLEAR, interpretation=treffers[0],
                              reason="eenduidig gekoppeld aan een van de opties")
        if len(treffers) > 1:
            return GateResult(
                Clarity.MULTIPLE,
                clarification=(
                    "Ik hoor meerdere opties in je antwoord: "
                    + " of ".join(treffers)
                    + ". Welke bedoel je?"
                ),
                reason=f"antwoord past op {len(treffers)} opties",
            )
        return GateResult(
            Clarity.MULTIPLE,
            clarification=(
                "Ik kon je antwoord niet aan een van de opties koppelen. "
                "De opties zijn: " + ", ".join(options) + ". Welke wordt het?"
            ),
            reason="antwoord past op geen enkele optie",
        )

    if interpreter is None:
        # Geen opties en geen lezer: we nemen het antwoord letterlijk over en
        # laten het bevestigen. Aanvullen doen we niet.
        return GateResult(Clarity.CLEAR, interpretation=tekst,
                          reason="letterlijk overgenomen, ter bevestiging")

    lezing = interpreter.interpret(question=question, options=options, transcript=tekst)
    if lezing.missing:
        return GateResult(
            Clarity.INCOMPLETE,
            clarification=(
                "Je antwoord dekt nog niet alles. Ontbreekt nog: "
                + ", ".join(lezing.missing)
                + ". Kun je dat aanvullen?"
            ),
            reason="antwoord is onvolledig",
        )
    if not lezing.unambiguous or len(lezing.alternatives) > 1:
        opties = " of ".join(lezing.alternatives[:3]) or "meerdere lezingen"
        return GateResult(
            Clarity.MULTIPLE,
            clarification=f"Ik kan je antwoord op meer dan een manier lezen: {opties}. "
                          "Welke bedoel je?",
            reason="meerdere mogelijke lezingen",
        )
    return GateResult(Clarity.CLEAR, interpretation=lezing.text,
                      reason="eenduidige lezing")


@dataclass
class Step:
    """Wat het kanaal nu moet doen, en met welke tekst."""

    act: Act
    text: str = ""
    clarity: Clarity | None = None
    reason: str = ""


class AnswerFlow:
    """De sessiemachine. Kanalen roepen alleen deze methodes aan."""

    def __init__(self, scope: ProjectScope, channel: str,
                 interpreter: Interpreter | None = None, *, transcribed: bool = False):
        self.scope = scope
        self.channel = channel
        self.interpreter = interpreter
        # Komt de tekst uit een transcriptie, dan zegt "exact" alleen dat de
        # transcriptie exact is -- niet dat er exact dat gezegd is. Zulke
        # kanalen houden de bevestigingsronde, altijd. Het hangt aan het kanaal
        # en niet aan een losse aanroep, want een correctieronde binnen hetzelfde
        # gesprek is nog steeds spraak.
        self.transcribed = transcribed

    # -- starten ---------------------------------------------------------
    def open(self, question_id: int, question_text: str, task_id: int | None = None) -> int:
        existing = self.scope.open_answer_session(question_id)
        if existing:
            return int(existing["id"])
        session_id = self.scope.start_answer_session(question_id, self.channel, task_id)
        self.scope.add_turn(session_id, "gevraagd", self.channel, question_text)
        return session_id

    # -- een antwoord verwerken -------------------------------------------
    def submit(self, session_id: int, transcript: str,
               confidence: float | None = None) -> Step:
        session = self.scope.answer_session(session_id)
        if session is None:
            raise ValueError(f"sessie {session_id} bestaat niet in {self.scope.slug}")
        question = self.scope.question(int(session["question_id"]))
        if question is None:
            raise ValueError("bijbehorende vraag bestaat niet meer")

        state = SessionState(session["state"])
        self.scope.add_turn(session_id, "geantwoord", self.channel, transcript, confidence)

        if state is SessionState.AWAITING_CONFIRMATION:
            return self._handle_confirmation(session_id, session, transcript)

        import json as _json
        options = _json.loads(question["options"] or "[]")

        # Een antwoord dat zonder interpretatie precies één aangeboden optie
        # aanwijst, hoeft niet nog eens bevestigd te worden: er valt niets te
        # bevestigen wat niet al vaststaat. Alles wat ook maar iets van
        # interpretatie vraagt, gaat wél door de bevestigingsronde.
        # ... maar niet op een kanaal dat transcribeert; zie self.transcribed.
        keuze = None if self.transcribed else exacte_optiekeuze(transcript, options)
        if keuze is not None:
            self.scope.set_answer_session(
                session_id, state=SessionState.RESOLVED.value, interpretation=keuze,
            )
            self.scope.add_turn(session_id, "afgesloten", self.channel, keuze,
                                note="exacte optiekeuze; geen bevestiging nodig")
            return Step(Act.APPLY, keuze, Clarity.CLEAR,
                        "het antwoord wijst zonder interpretatie precies één aangeboden"
                        " optie aan")

        result = assess(
            question=question["text"],
            options=options,
            transcript=transcript,
            confidence=confidence,
            interpreter=self.interpreter,
        )

        if result.clarity.usable:
            self.scope.set_answer_session(
                session_id,
                state=SessionState.AWAITING_CONFIRMATION.value,
                interpretation=result.interpretation,
            )
            tekst = (
                f"Ik leg dit vast als: {result.interpretation}. Klopt dat? "
                "Zeg ja om te bevestigen, of corrigeer het."
            )
            self.scope.add_turn(session_id, "bevestiging", self.channel, tekst,
                                note=result.reason)
            return Step(Act.ASK_CONFIRMATION, tekst, result.clarity, result.reason)

        gebruikt = int(session["clarifications"] or 0)
        if result.clarity is not Clarity.DEFERRED and gebruikt < MAX_VERDUIDELIJKINGEN:
            self.scope.set_answer_session(
                session_id,
                state=SessionState.AWAITING_CLARIFICATION.value,
                clarifications=gebruikt + 1,
            )
            tekst = result.clarification or "Kun je dat verduidelijken?"
            self.scope.add_turn(session_id, "verduidelijking", self.channel, tekst,
                                note=result.reason)
            return Step(Act.ASK_CLARIFICATION, tekst, result.clarity, result.reason)

        return self._return_to_block(session_id, result.clarity, result.reason)

    # -- bevestiging -------------------------------------------------------
    def _handle_confirmation(self, session_id: int, session, transcript: str) -> Step:
        if _JA.match(transcript.strip()):
            self.scope.set_answer_session(session_id, state=SessionState.RESOLVED.value)
            self.scope.add_turn(session_id, "afgesloten", self.channel,
                                session["interpretation"] or "", note="bevestigd")
            return Step(Act.APPLY, session["interpretation"] or "", Clarity.CLEAR,
                        "bevestigd door de mens")

        if _WEET_NIET.search(transcript):
            return self._return_to_block(session_id, Clarity.DEFERRED,
                                         "uitgesteld tijdens de bevestiging")

        gebruikt = int(session["clarifications"] or 0)
        if gebruikt >= MAX_VERDUIDELIJKINGEN:
            return self._return_to_block(
                session_id, Clarity.MULTIPLE,
                "correctie na de toegestane verduidelijking; niet verder geraden",
            )

        # Een correctie is een nieuw antwoord: opnieuw door de poort, nooit
        # samengevoegd met het vorige.
        self.scope.set_answer_session(
            session_id, state=SessionState.ASKED.value, clarifications=gebruikt + 1,
            interpretation=None,
        )
        schoon = _NEE.sub("", transcript, count=1).strip(" ,.;:") or transcript
        return self.submit(session_id, schoon)

    def _return_to_block(self, session_id: int, clarity: Clarity, reason: str) -> Step:
        self.scope.set_answer_session(
            session_id, state=SessionState.RETURNED_TO_BLOCK.value
        )
        tekst = (
            "Ik heb geen antwoord waar ik zeker genoeg van ben. De taak blijft "
            "geblokkeerd; we pakken het later opnieuw op."
        )
        self.scope.add_turn(session_id, "afgesloten", self.channel, tekst, note=reason)
        return Step(Act.KEEP_BLOCKED, tekst, clarity, reason)

    # -- audit -------------------------------------------------------------
    def audit(self, session_id: int) -> list[dict]:
        return [dict(row) for row in self.scope.turns(session_id)]
