"""Projectoverstijgende laag boven VoiceQueue.

Een spraaktransport weet niet welk project aan de beurt is; het vraagt alleen
"wat staat er open". Deze laag zoekt dat op over alle projecten heen en houdt de
koppeling sessie → project vast, zodat een antwoord altijd bij de juiste taak
terechtkomt.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..answer_session import Interpreter
from ..config import Settings
from ..db import Database
from .. import projects as projects_mod
from . import VoicePrompt, VoiceQueue, VoiceReply


class OnbekendeSessie(LookupError):
    pass


@dataclass
class VoiceService:
    settings: Settings
    db: Database
    interpreter: Interpreter | None = None

    def _queue(self, slug: str) -> VoiceQueue:
        project = projects_mod.load(self.settings, slug)
        return VoiceQueue(self.db.scope(slug), project, interpreter=self.interpreter)

    def projecten(self) -> list[str]:
        return projects_mod.list_projects(self.settings)

    def volgende(self, project: str | None = None) -> VoicePrompt | None:
        """De oudste openstaande blokkade, over alle projecten heen."""
        slugs = [project] if project else self.projecten()
        for slug in slugs:
            prompt = self._queue(slug).next_question()
            if prompt is not None:
                return prompt
        return None

    def _project_van_sessie(self, session_id: int) -> str:
        """Zoekt bij welk project een sessie hoort. Nooit raden."""
        rows = self.db.across_projects(
            "SELECT p.slug AS slug FROM answer_sessions s"
            " JOIN projects p ON p.id = s.project_id WHERE s.id = ?",
            (session_id,),
        )
        if not rows:
            raise OnbekendeSessie(f"sessie {session_id} bestaat niet")
        return str(rows[0]["slug"])

    def antwoord(
        self, session_id: int, transcript: str, confidence: float | None = None
    ) -> tuple[str, VoiceReply]:
        slug = self._project_van_sessie(session_id)
        return slug, self._queue(slug).submit(session_id, transcript, confidence)

    def audit(self, session_id: int) -> list[dict]:
        slug = self._project_van_sessie(session_id)
        return self._queue(slug).audit(session_id)
