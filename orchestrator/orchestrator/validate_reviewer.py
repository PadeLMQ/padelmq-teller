"""Valideert de reviewer-aanroep tegen de werkelijk geïnstalleerde SDK.

Twee trappen, met opzet gescheiden:

1. **Offline** — leest de handtekening van ``client.responses.create`` uit het
   geïnstalleerde pakket en vergelijkt die met de parameters die wij versturen.
   Geen netwerk, geen sleutel, geen kosten. Dit kan vandaag al.
2. **Online** — één minimale echte aanroep, op het goedkoopste geschikte model,
   met de kleinst mogelijke invoer, langs exact hetzelfde codepad als productie.

Wijkt de vorm af, dan **stopt** dit: er wordt niet stil teruggevallen op een
andere implementatie. De uitvoer zegt precies wat er gecorrigeerd moet worden.
"""

from __future__ import annotations

import inspect as _inspect
import json
import os
from dataclasses import dataclass, field

# De parameters die onze adapter meestuurt. Blijft dit in de pas met
# adapters/reviewer.py, dan valideert deze controle het echte codepad.
REQUIRED_PARAMS = ("model", "input", "previous_response_id", "text")

# De velden die de adapter uit het antwoord leest.
REQUIRED_RESPONSE_FIELDS = ("output_text", "id", "usage")

MINIMAL_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["ok"],
    "properties": {"ok": {"type": "boolean"}},
}


@dataclass
class Finding:
    level: str          # "ok" | "waarschuwing" | "fout"
    subject: str
    detail: str


@dataclass
class ValidationReport:
    stage: str
    findings: list[Finding] = field(default_factory=list)
    cost_note: str = ""

    @property
    def failed(self) -> bool:
        return any(f.level == "fout" for f in self.findings)

    def add(self, level: str, subject: str, detail: str) -> None:
        self.findings.append(Finding(level, subject, detail))

    def render(self) -> str:
        symbols = {"ok": "  ok ", "waarschuwing": "  ?? ", "fout": " FOUT"}
        lines = [f"Reviewer-validatie — trap: {self.stage}", ""]
        for finding in self.findings:
            lines.append(f"{symbols.get(finding.level, '    ')} {finding.subject}")
            if finding.detail:
                lines.append(f"       {finding.detail}")
        if self.cost_note:
            lines.append("")
            lines.append(self.cost_note)
        lines.append("")
        lines.append(
            "AFGEKEURD — corrigeer adapters/reviewer.py voordat er een productierun draait."
            if self.failed else
            "Goedgekeurd voor deze trap."
        )
        return "\n".join(lines)


def validate_offline() -> ValidationReport:
    """Vergelijkt onze parameters met de handtekening van de geïnstalleerde SDK."""
    report = ValidationReport(stage="offline (geen netwerk, geen kosten)")
    try:
        import openai
    except ImportError:
        report.add("fout", "pakket 'openai'", "niet geïnstalleerd; pip install openai")
        return report

    version = getattr(openai, "__version__", "onbekend")
    report.add("ok", "pakket 'openai'", f"versie {version}")

    client_cls = getattr(openai, "OpenAI", None)
    if client_cls is None:
        report.add("fout", "openai.OpenAI", "klasse bestaat niet in dit pakket")
        return report

    responses = getattr(client_cls, "responses", None)
    create = None
    if responses is not None:
        create = getattr(responses, "create", None)
    if create is None:
        # In veel versies is 'responses' een property op de instantie; val terug
        # op de resource-klasse in de module.
        try:
            from openai.resources.responses import Responses  # type: ignore

            create = getattr(Responses, "create", None)
        except Exception:  # noqa: BLE001 - we rapporteren het gewoon
            create = None
    if create is None:
        report.add(
            "fout", "responses.create",
            "kon de methode niet vinden om te inspecteren; controleer handmatig "
            "of de Responses API in deze SDK-versie bestaat",
        )
        return report

    try:
        signature = _inspect.signature(create)
    except (TypeError, ValueError) as exc:
        report.add("waarschuwing", "handtekening", f"niet leesbaar: {exc}")
        return report

    accepted = set(signature.parameters)
    has_kwargs = any(
        p.kind is _inspect.Parameter.VAR_KEYWORD for p in signature.parameters.values()
    )
    for name in REQUIRED_PARAMS:
        if name in accepted:
            report.add("ok", f"parameter {name!r}", "aanvaard door de SDK")
        elif has_kwargs:
            report.add(
                "waarschuwing", f"parameter {name!r}",
                "niet in de handtekening, maar de methode accepteert **kwargs; "
                "alleen een echte aanroep geeft uitsluitsel",
            )
        else:
            report.add(
                "fout", f"parameter {name!r}",
                "wordt door deze SDK-versie niet aanvaard — corrigeer de adapter",
            )
    return report


def validate_online(model: str, client=None) -> ValidationReport:
    """Eén minimale echte aanroep langs hetzelfde codepad als productie."""
    report = ValidationReport(stage=f"online — één minimale aanroep op {model}")

    if client is None:
        if not os.environ.get("OPENAI_API_KEY"):
            report.add("fout", "OPENAI_API_KEY", "niet gezet; deze trap kan niet draaien")
            return report
        try:
            from openai import OpenAI
        except ImportError:
            report.add("fout", "pakket 'openai'", "niet geïnstalleerd")
            return report
        client = OpenAI()

    try:
        response = client.responses.create(
            model=model,
            previous_response_id=None,
            input=[
                {"role": "system", "content": "Antwoord met {\"ok\": true}."},
                {"role": "user", "content": "ok?"},
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "validatie",
                    "schema": MINIMAL_SCHEMA,
                    "strict": True,
                }
            },
        )
    except TypeError as exc:
        report.add(
            "fout", "parametervorm",
            f"de SDK weigerde onze aanroep: {exc}. "
            "Dit is precies het geval waarvoor deze controle bestaat: corrigeer "
            "adapters/reviewer.py, val niet terug op een andere vorm.",
        )
        return report
    except Exception as exc:  # noqa: BLE001 - de melding is de opbrengst
        report.add("fout", type(exc).__name__, str(exc)[:400])
        return report

    report.add("ok", "aanroep", "geaccepteerd door de API")

    for attribute in REQUIRED_RESPONSE_FIELDS:
        if hasattr(response, attribute):
            report.add("ok", f"antwoordveld {attribute!r}", "aanwezig")
        else:
            report.add(
                "fout", f"antwoordveld {attribute!r}",
                "ontbreekt; de adapter leest dit veld wel uit",
            )

    text = getattr(response, "output_text", None)
    if text:
        try:
            parsed = json.loads(text)
            if parsed.get("ok") is True:
                report.add("ok", "gestructureerde uitvoer", "schema afgedwongen en geldig")
            else:
                report.add("waarschuwing", "gestructureerde uitvoer",
                           f"onverwachte inhoud: {text[:120]}")
        except ValueError:
            report.add("fout", "gestructureerde uitvoer",
                       f"geen geldige JSON: {text[:120]}")

    usage = getattr(response, "usage", None)
    tokens_in = int(getattr(usage, "input_tokens", 0) or 0)
    tokens_out = int(getattr(usage, "output_tokens", 0) or 0)
    if usage is not None and (tokens_in or tokens_out):
        report.add("ok", "tokentelling", f"in {tokens_in}, uit {tokens_out}")
        report.cost_note = (
            f"Verbruik van deze validatie: {tokens_in} invoer- en {tokens_out} "
            "uitvoertokens. Verwaarloosbaar, maar wel echt geld."
        )
    else:
        report.add("fout", "tokentelling",
                   "geen bruikbare usage; de kostenbewaking kan dan niet meten")
    return report
