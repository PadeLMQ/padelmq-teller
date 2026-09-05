"""Klein HTTP-eindpunt voor het spraaktransport.

Twee handelingen, meer heeft een Shortcut of een bot niet nodig:

    GET  /voice/next[?project=<slug>]   welke vraag staat open
    POST /voice/answer                  hier is mijn antwoord

Bewust op de standaardbibliotheek: geen webframework erbij voor twee routes.

Veiligheid:
  - Een token is verplicht; zonder ORCH_VOICE_TOKEN start de dienst niet.
  - Het token gaat in een kop, niet in de URL, en wordt in constante tijd
    vergeleken.
  - Standaard alleen op localhost. Van buiten bereikbaar maken doe je via een
    reverse proxy met TLS — niet door hier 0.0.0.0 te zetten zonder proxy.
  - De hoeveelheid verzoeken is begrensd; wie het token raadt, komt niet ver.
  - Vraagteksten zijn al geredigeerd voordat ze hier komen (zie VoiceQueue),
    dus er wordt nooit een geheim voorgelezen.
"""

from __future__ import annotations

import hmac
import json
import os
import time
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .service import OnbekendeSessie, VoiceService

MAX_BODY = 64 * 1024
TOKEN_HEADER = "X-Orch-Token"


@dataclass
class RateLimiter:
    """Eenvoudige emmer per afzender."""

    per_minuut: int = 60
    _emmer: dict[str, list[float]] = field(default_factory=dict)

    def toegestaan(self, sleutel: str) -> bool:
        nu = time.monotonic()
        recent = [t for t in self._emmer.get(sleutel, []) if nu - t < 60]
        if len(recent) >= self.per_minuut:
            self._emmer[sleutel] = recent
            return False
        recent.append(nu)
        self._emmer[sleutel] = recent
        return True


def maak_handler(service: VoiceService, token: str, limiter: RateLimiter):
    class Handler(BaseHTTPRequestHandler):
        server_version = "orchestrator-voice"
        protocol_version = "HTTP/1.1"

        # -- hulpjes ----------------------------------------------------
        def _stuur(self, status: HTTPStatus, payload: dict) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _gemachtigd(self) -> bool:
            afzender = self.client_address[0] if self.client_address else "?"
            if not limiter.toegestaan(afzender):
                self._stuur(HTTPStatus.TOO_MANY_REQUESTS, {"fout": "te veel verzoeken"})
                return False
            aangeboden = self.headers.get(TOKEN_HEADER, "")
            if not hmac.compare_digest(aangeboden, token):
                # Geen details: wie het token niet heeft, hoort niets te leren.
                self._stuur(HTTPStatus.UNAUTHORIZED, {"fout": "niet gemachtigd"})
                return False
            return True

        def _lees_json(self) -> dict | None:
            lengte = int(self.headers.get("Content-Length") or 0)
            if lengte <= 0 or lengte > MAX_BODY:
                self._stuur(HTTPStatus.BAD_REQUEST, {"fout": "onbruikbare inhoud"})
                return None
            try:
                return json.loads(self.rfile.read(lengte).decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                self._stuur(HTTPStatus.BAD_REQUEST, {"fout": "geen geldige JSON"})
                return None

        # -- routes -----------------------------------------------------
        def do_GET(self) -> None:  # noqa: N802 - vaste naam van de bibliotheek
            pad = urlparse(self.path)
            if pad.path == "/health":
                self._stuur(HTTPStatus.OK, {"status": "ok"})
                return
            if pad.path != "/voice/next":
                self._stuur(HTTPStatus.NOT_FOUND, {"fout": "onbekend pad"})
                return
            if not self._gemachtigd():
                return

            project = (parse_qs(pad.query).get("project") or [None])[0]
            try:
                prompt = service.volgende(project)
            except Exception as exc:  # onbekend project, kapotte configuratie
                self._stuur(HTTPStatus.BAD_REQUEST, {"fout": str(exc)[:200]})
                return
            if prompt is None:
                self._stuur(HTTPStatus.OK, {"vraag": None, "spreek": "Er staat niets open."})
                return
            self._stuur(HTTPStatus.OK, {
                "sessie": prompt.session_id,
                "project": prompt.project,
                "taak": prompt.task_id,
                "vraag_id": prompt.question_id,
                "spreek": prompt.text,
                "opties": prompt.options,
            })

        def do_POST(self) -> None:  # noqa: N802
            if urlparse(self.path).path != "/voice/answer":
                self._stuur(HTTPStatus.NOT_FOUND, {"fout": "onbekend pad"})
                return
            if not self._gemachtigd():
                return
            data = self._lees_json()
            if data is None:
                return

            try:
                sessie = int(data["sessie"])
            except (KeyError, TypeError, ValueError):
                self._stuur(HTTPStatus.BAD_REQUEST, {"fout": "veld 'sessie' ontbreekt of is geen getal"})
                return
            transcript = str(data.get("transcript") or "")
            ruwe_zekerheid = data.get("zekerheid")
            try:
                zekerheid = None if ruwe_zekerheid is None else float(ruwe_zekerheid)
            except (TypeError, ValueError):
                self._stuur(HTTPStatus.BAD_REQUEST, {"fout": "'zekerheid' is geen getal"})
                return

            try:
                project, reply = service.antwoord(sessie, transcript, zekerheid)
            except OnbekendeSessie as exc:
                self._stuur(HTTPStatus.NOT_FOUND, {"fout": str(exc)})
                return
            except Exception as exc:
                self._stuur(HTTPStatus.BAD_REQUEST, {"fout": str(exc)[:200]})
                return

            self._stuur(HTTPStatus.OK, {
                "project": project,
                "spreek": reply.speak,
                "klaar": reply.finished,
                "vastgelegd": reply.applied,
                "beslissing": reply.decision_id,
                "hervatte_taken": reply.resumed_tasks,
                "duidelijkheid": reply.clarity,
                "reden": reply.reason,
            })

        def log_message(self, *args) -> None:  # stil; de audit staat in de database
            return

    return Handler


def maak_server(
    service: VoiceService, *, host: str | None = None, port: int | None = None,
    token: str | None = None, per_minuut: int = 60,
) -> ThreadingHTTPServer:
    token = token or os.environ.get("ORCH_VOICE_TOKEN", "")
    if len(token) < 24:
        raise RuntimeError(
            "ORCH_VOICE_TOKEN ontbreekt of is te kort (minstens 24 tekens). "
            "Wie dit token heeft, kan beslissingen namens jou vastleggen."
        )
    host = host if host is not None else os.environ.get("ORCH_VOICE_HOST", "127.0.0.1")
    port = port if port is not None else int(os.environ.get("ORCH_VOICE_PORT", "8765"))
    handler = maak_handler(service, token, RateLimiter(per_minuut=per_minuut))
    return ThreadingHTTPServer((host, port), handler)
