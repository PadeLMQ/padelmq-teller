"""Opslag. Eén SQLite-bestand.

Belangrijkste ontwerpregel: elke tabel met projectgegevens is uitsluitend
bereikbaar via een ProjectScope, en die zet ``project_id`` verplicht in elke
query. Er bestaat geen codepad dat rijen van twee projecten tegelijk teruggeeft
zonder dat de aanroeper daar expliciet om vraagt (``across_projects``).
Dit is het derde van de vier isolatiesloten uit het ontwerp.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any, Iterable

from .models import now

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id           INTEGER PRIMARY KEY,
    slug         TEXT NOT NULL UNIQUE,
    created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tasks (
    id            INTEGER PRIMARY KEY,
    project_id    INTEGER NOT NULL REFERENCES projects(id),
    title         TEXT NOT NULL,
    spec          TEXT NOT NULL DEFAULT '',
    acceptance    TEXT NOT NULL DEFAULT '[]',
    status        TEXT NOT NULL,
    priority      INTEGER NOT NULL DEFAULT 100,
    depends_on    INTEGER,
    blocked_by_question INTEGER,
    claude_session_id   TEXT,
    reviewer_response_id TEXT,
    iterations    INTEGER NOT NULL DEFAULT 0,
    review_rounds INTEGER NOT NULL DEFAULT 0,
    review_feedback TEXT,
    last_review_feedback TEXT,
    last_review_signature TEXT,
    cost_eur      REAL NOT NULL DEFAULT 0,
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_tasks_project ON tasks(project_id, status);

CREATE TABLE IF NOT EXISTS questions (
    id            INTEGER PRIMARY KEY,
    project_id    INTEGER NOT NULL REFERENCES projects(id),
    task_id       INTEGER,
    fingerprint   TEXT NOT NULL,
    text          TEXT NOT NULL,
    why_blocking  TEXT NOT NULL DEFAULT '',
    options       TEXT NOT NULL DEFAULT '[]',
    proposed      TEXT,
    category      TEXT,
    outcome       TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'open',
    issue_number  INTEGER,
    answer        TEXT,
    answered_at   TEXT,
    created_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_questions_project ON questions(project_id, status);

CREATE TABLE IF NOT EXISTS runs (
    id          INTEGER PRIMARY KEY,
    project_id  INTEGER NOT NULL REFERENCES projects(id),
    task_id     INTEGER NOT NULL,
    phase       TEXT NOT NULL,
    started_at  TEXT NOT NULL,
    ended_at    TEXT,
    outcome     TEXT,
    cost_eur    REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS calls (
    id            INTEGER PRIMARY KEY,
    project_id    INTEGER NOT NULL REFERENCES projects(id),
    task_id       INTEGER,
    run_id        INTEGER,
    phase         TEXT NOT NULL,
    role          TEXT NOT NULL,
    model         TEXT NOT NULL,
    tokens_in     INTEGER NOT NULL DEFAULT 0,
    tokens_out    INTEGER NOT NULL DEFAULT 0,
    cached_in     INTEGER NOT NULL DEFAULT 0,
    cost_eur      REAL NOT NULL DEFAULT 0,
    wasted_reason TEXT,
    day           TEXT NOT NULL,
    created_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_calls_day ON calls(day);
CREATE INDEX IF NOT EXISTS ix_calls_project_day ON calls(project_id, day);

CREATE TABLE IF NOT EXISTS events (
    id          INTEGER PRIMARY KEY,
    project_id  INTEGER NOT NULL REFERENCES projects(id),
    task_id     INTEGER,
    ts          TEXT NOT NULL,
    kind        TEXT NOT NULL,
    payload     TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS ix_events_project ON events(project_id, ts);

-- Hergebruik van reviewerantwoorden. De sleutel bevat alles wat het antwoord
-- materieel kan beinvloeden, dus een hit betekent per definitie: dezelfde vraag,
-- dezelfde bevestigde kennis, dezelfde code, dezelfde criteria, hetzelfde model.
CREATE TABLE IF NOT EXISTS reviewer_cache (
    id          INTEGER PRIMARY KEY,
    project_id  INTEGER NOT NULL REFERENCES projects(id),
    soort       TEXT NOT NULL,
    sleutel     TEXT NOT NULL,
    model       TEXT NOT NULL,
    resultaat   TEXT NOT NULL,
    tokens_in   INTEGER NOT NULL DEFAULT 0,
    tokens_out  INTEGER NOT NULL DEFAULT 0,
    treffers    INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS ix_cache_sleutel
    ON reviewer_cache(project_id, soort, sleutel);

CREATE TABLE IF NOT EXISTS answer_sessions (
    id             INTEGER PRIMARY KEY,
    project_id     INTEGER NOT NULL REFERENCES projects(id),
    question_id    INTEGER NOT NULL,
    task_id        INTEGER,
    channel        TEXT NOT NULL,
    state          TEXT NOT NULL,
    clarifications INTEGER NOT NULL DEFAULT 0,
    interpretation TEXT,
    decision_id    TEXT,
    created_at     TEXT NOT NULL,
    updated_at     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_sessions_project ON answer_sessions(project_id, state);

-- Volledig audit spoor: elke beurt in het gesprek, ongeacht het kanaal.
CREATE TABLE IF NOT EXISTS answer_turns (
    id          INTEGER PRIMARY KEY,
    project_id  INTEGER NOT NULL REFERENCES projects(id),
    session_id  INTEGER NOT NULL,
    ts          TEXT NOT NULL,
    direction   TEXT NOT NULL,   -- gevraagd | geantwoord | verduidelijking | bevestiging | afgesloten
    channel     TEXT NOT NULL,
    text        TEXT NOT NULL,
    confidence  REAL,
    note        TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS ix_turns_session ON answer_turns(session_id, id);

CREATE TABLE IF NOT EXISTS signatures (
    id          INTEGER PRIMARY KEY,
    project_id  INTEGER NOT NULL REFERENCES projects(id),
    task_id     INTEGER NOT NULL,
    signature   TEXT NOT NULL,
    created_at  TEXT NOT NULL
);
"""

# Tabellen die projectgegevens bevatten en dus altijd gescopeerd horen te zijn.
SCOPED_TABLES = ("tasks", "questions", "runs", "calls", "events", "signatures")


class _GedeeldeVerbinding:
    """Serialiseert toegang tot één SQLite-verbinding over meerdere draden.

    Nodig omdat het spraakeindpunt elk verzoek in een eigen draad afhandelt.
    Eén verbinding met een slot is op deze schaal eenvoudiger en veiliger dan
    een verbinding per draad: geen halfafgemaakte transacties, geen
    verbindingen die blijven hangen.
    """

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn
        self._slot = threading.RLock()

    def execute(self, sql: str, params: Iterable[Any] = ()) -> sqlite3.Cursor:
        with self._slot:
            return self._conn.execute(sql, tuple(params))

    def executescript(self, sql: str) -> sqlite3.Cursor:
        with self._slot:
            return self._conn.executescript(sql)

    def close(self) -> None:
        with self._slot:
            self._conn.close()


class Database:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        raw = sqlite3.connect(self.path, isolation_level=None, check_same_thread=False)
        raw.row_factory = sqlite3.Row
        self.conn = _GedeeldeVerbinding(raw)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(SCHEMA)
        self._migreer()

    def _migreer(self) -> None:
        """Kolommen bijzetten die na een bestaande database zijn toegevoegd.

        CREATE TABLE IF NOT EXISTS raakt een bestaande tabel niet aan, dus een
        nieuwe kolom komt er anders nooit bij en oude datamappen breken.
        """
        bestaand = {
            r["name"] for r in self.conn.execute("PRAGMA table_info(tasks)")
        }
        if "review_feedback" not in bestaand:
            self.conn.execute("ALTER TABLE tasks ADD COLUMN review_feedback TEXT")
        kolommen = {r["name"] for r in self.conn.execute("PRAGMA table_info(calls)")}
        if "wasted_reason" not in kolommen:
            self.conn.execute("ALTER TABLE calls ADD COLUMN wasted_reason TEXT")
        for kolom in ("last_review_feedback", "last_review_signature"):
            if kolom not in bestaand:
                self.conn.execute(f"ALTER TABLE tasks ADD COLUMN {kolom} TEXT")

    def close(self) -> None:
        self.conn.close()

    # -- projectbeheer ---------------------------------------------------
    def ensure_project(self, slug: str) -> int:
        row = self.conn.execute(
            "SELECT id FROM projects WHERE slug = ?", (slug,)
        ).fetchone()
        if row:
            return int(row["id"])
        cur = self.conn.execute(
            "INSERT INTO projects (slug, created_at) VALUES (?, ?)", (slug, now())
        )
        return int(cur.lastrowid)

    def project_slugs(self) -> list[str]:
        return [r["slug"] for r in self.conn.execute("SELECT slug FROM projects ORDER BY slug")]

    def scope(self, slug: str) -> "ProjectScope":
        return ProjectScope(self, self.ensure_project(slug), slug)

    # -- bewust projectoverstijgend --------------------------------------
    def across_projects(self, sql: str, params: Iterable[Any] = ()) -> list[sqlite3.Row]:
        """Uitsluitend voor rapportage over alle projecten heen.

        De naam is expres lang en expres expliciet: wie dit aanroept, doet dat
        met opzet. Alle gewone toegang loopt via ProjectScope.
        """
        return list(self.conn.execute(sql, tuple(params)))


class ProjectScope:
    """Alle projectgegevens gaan hierdoorheen, met project_id verplicht."""

    def __init__(self, db: Database, project_id: int, slug: str):
        self._db = db
        self.project_id = project_id
        self.slug = slug

    @property
    def conn(self) -> "_GedeeldeVerbinding":
        return self._db.conn

    def _q(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        return list(self.conn.execute(sql, params))

    # -- taken -----------------------------------------------------------
    def add_task(
        self,
        title: str,
        spec: str = "",
        acceptance: list[str] | None = None,
        priority: int = 100,
        depends_on: int | None = None,
    ) -> int:
        stamp = now()
        cur = self.conn.execute(
            "INSERT INTO tasks (project_id, title, spec, acceptance, status, priority,"
            " depends_on, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (
                self.project_id,
                title,
                spec,
                json.dumps(acceptance or []),
                "queued",
                priority,
                depends_on,
                stamp,
                stamp,
            ),
        )
        return int(cur.lastrowid)

    def task(self, task_id: int) -> sqlite3.Row | None:
        rows = self._q(
            "SELECT * FROM tasks WHERE id = ? AND project_id = ?",
            (task_id, self.project_id),
        )
        return rows[0] if rows else None

    def tasks(self, status: str | None = None) -> list[sqlite3.Row]:
        if status:
            return self._q(
                "SELECT * FROM tasks WHERE project_id = ? AND status = ?"
                " ORDER BY priority, id",
                (self.project_id, status),
            )
        return self._q(
            "SELECT * FROM tasks WHERE project_id = ? ORDER BY priority, id",
            (self.project_id,),
        )

    def next_queued(self) -> sqlite3.Row | None:
        rows = self._q(
            "SELECT * FROM tasks WHERE project_id = ? AND status = 'queued'"
            " ORDER BY priority, id LIMIT 1",
            (self.project_id,),
        )
        return rows[0] if rows else None

    def has_independent_work(self, excluding_task_id: int | None = None) -> bool:
        """Kan er veilig aan iets anders verder gewerkt worden in dit project?

        Bepaalt de keuze tussen PARK en BLOCK.
        """
        rows = self._q(
            "SELECT id FROM tasks WHERE project_id = ? AND status = 'queued'"
            " AND (? IS NULL OR id != ?)",
            (self.project_id, excluding_task_id, excluding_task_id),
        )
        return bool(rows)

    def set_task(self, task_id: int, **fields: Any) -> None:
        if not fields:
            return
        allowed = {
            "status", "spec", "acceptance", "priority", "depends_on",
            "blocked_by_question", "claude_session_id", "reviewer_response_id",
            "iterations", "review_rounds", "cost_eur", "review_feedback",
            "last_review_feedback", "last_review_signature",
        }
        unknown = set(fields) - allowed
        if unknown:
            raise ValueError(f"onbekende taakvelden: {sorted(unknown)}")
        sets = ", ".join(f"{k} = ?" for k in fields)
        self.conn.execute(
            f"UPDATE tasks SET {sets}, updated_at = ? WHERE id = ? AND project_id = ?",
            (*fields.values(), now(), task_id, self.project_id),
        )

    # -- vragen ----------------------------------------------------------
    def find_open_question(self, fingerprint: str) -> sqlite3.Row | None:
        rows = self._q(
            "SELECT * FROM questions WHERE project_id = ? AND fingerprint = ?"
            " AND status = 'open'",
            (self.project_id, fingerprint),
        )
        return rows[0] if rows else None

    def add_question(
        self,
        text: str,
        outcome: str,
        fingerprint: str,
        why_blocking: str = "",
        options: list[str] | None = None,
        proposed: str | None = None,
        category: str | None = None,
        task_id: int | None = None,
    ) -> int:
        existing = self.find_open_question(fingerprint)
        if existing:
            return int(existing["id"])
        cur = self.conn.execute(
            "INSERT INTO questions (project_id, task_id, fingerprint, text, why_blocking,"
            " options, proposed, category, outcome, status, created_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,'open',?)",
            (
                self.project_id, task_id, fingerprint, text, why_blocking,
                json.dumps(options or []), proposed, category, outcome, now(),
            ),
        )
        return int(cur.lastrowid)

    def open_questions(self, outcome: str | None = None) -> list[sqlite3.Row]:
        if outcome:
            return self._q(
                "SELECT * FROM questions WHERE project_id = ? AND status = 'open'"
                " AND outcome = ? ORDER BY id",
                (self.project_id, outcome),
            )
        return self._q(
            "SELECT * FROM questions WHERE project_id = ? AND status = 'open' ORDER BY id",
            (self.project_id,),
        )

    def pending_questions(self, outcome: str | None = None) -> list[sqlite3.Row]:
        """Alles wat nog jouw aandacht vraagt: open én wachtend op je bevestiging.

        Een vraag waarop je al geantwoord hebt maar die nog niet bevestigd is,
        mag niet uit beeld verdwijnen; anders blijft de taak stilstaan.
        """
        statuses = ("open", "awaiting_confirmation")
        if outcome:
            return self._q(
                "SELECT * FROM questions WHERE project_id = ? AND status IN (?, ?)"
                " AND outcome = ? ORDER BY id",
                (self.project_id, *statuses, outcome),
            )
        return self._q(
            "SELECT * FROM questions WHERE project_id = ? AND status IN (?, ?) ORDER BY id",
            (self.project_id, *statuses),
        )

    def question(self, question_id: int) -> sqlite3.Row | None:
        rows = self._q(
            "SELECT * FROM questions WHERE id = ? AND project_id = ?",
            (question_id, self.project_id),
        )
        return rows[0] if rows else None

    def set_question(self, question_id: int, **fields: Any) -> None:
        allowed = {"status", "answer", "answered_at", "issue_number", "outcome"}
        unknown = set(fields) - allowed
        if unknown:
            raise ValueError(f"onbekende vraagvelden: {sorted(unknown)}")
        sets = ", ".join(f"{k} = ?" for k in fields)
        self.conn.execute(
            f"UPDATE questions SET {sets} WHERE id = ? AND project_id = ?",
            (*fields.values(), question_id, self.project_id),
        )

    def tasks_waiting_on(self, question_id: int) -> list[sqlite3.Row]:
        return self._q(
            "SELECT * FROM tasks WHERE project_id = ? AND blocked_by_question = ?",
            (self.project_id, question_id),
        )

    # -- runs, kosten, gebeurtenissen ------------------------------------
    def start_run(self, task_id: int, phase: str) -> int:
        cur = self.conn.execute(
            "INSERT INTO runs (project_id, task_id, phase, started_at) VALUES (?,?,?,?)",
            (self.project_id, task_id, phase, now()),
        )
        return int(cur.lastrowid)

    def end_run(self, run_id: int, outcome: str, cost_eur: float | None = None) -> None:
        """Sluit de run af. Zonder bedrag telt hij zijn eigen aanroepen op.

        Elke aanroeper moest de kosten anders zelf meegeven en deed dat nergens,
        waardoor elke run $0 rapporteerde terwijl de losse aanroepen wel klopten.
        De som staat al in de database; die hoeft niemand door te geven.
        """
        if cost_eur is None:
            cost_eur = float(
                self.conn.execute(
                    "SELECT COALESCE(SUM(cost_eur), 0) FROM calls"
                    " WHERE run_id = ? AND project_id = ?",
                    (run_id, self.project_id),
                ).fetchone()[0]
            )
        self.conn.execute(
            "UPDATE runs SET ended_at = ?, outcome = ?, cost_eur = ?"
            " WHERE id = ? AND project_id = ?",
            (now(), outcome, cost_eur, run_id, self.project_id),
        )

    def record_call(
        self, *, phase: str, role: str, model: str, tokens_in: int, tokens_out: int,
        cached_in: int, cost_eur: float, task_id: int | None = None,
        run_id: int | None = None, day: str | None = None,
    ) -> None:
        stamp = now()
        self.conn.execute(
            "INSERT INTO calls (project_id, task_id, run_id, phase, role, model,"
            " tokens_in, tokens_out, cached_in, cost_eur, day, created_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                self.project_id, task_id, run_id, phase, role, model,
                tokens_in, tokens_out, cached_in, cost_eur, day or stamp[:10], stamp,
            ),
        )

    def spend_today(self, day: str) -> float:
        row = self.conn.execute(
            "SELECT COALESCE(SUM(cost_eur), 0) AS total FROM calls"
            " WHERE project_id = ? AND day = ?",
            (self.project_id, day),
        ).fetchone()
        return float(row["total"])

    def spend_task(self, task_id: int) -> float:
        row = self.conn.execute(
            "SELECT COALESCE(SUM(cost_eur), 0) AS total FROM calls"
            " WHERE project_id = ? AND task_id = ?",
            (self.project_id, task_id),
        ).fetchone()
        return float(row["total"])

    def spend_run(self, run_id: int) -> float:
        row = self.conn.execute(
            "SELECT COALESCE(SUM(cost_eur), 0) AS total FROM calls"
            " WHERE project_id = ? AND run_id = ?",
            (self.project_id, run_id),
        ).fetchone()
        return float(row["total"])

    def log(self, kind: str, payload: dict | None = None, task_id: int | None = None) -> None:
        self.conn.execute(
            "INSERT INTO events (project_id, task_id, ts, kind, payload) VALUES (?,?,?,?,?)",
            (self.project_id, task_id, now(), kind, json.dumps(payload or {}, ensure_ascii=False)),
        )

    def events(self, limit: int = 50) -> list[sqlite3.Row]:
        return self._q(
            "SELECT * FROM events WHERE project_id = ? ORDER BY id DESC LIMIT ?",
            (self.project_id, limit),
        )

    # -- hergebruik van reviewerantwoorden -------------------------------
    def cache_get(self, soort: str, sleutel: str) -> sqlite3.Row | None:
        rows = self._q(
            "SELECT * FROM reviewer_cache WHERE project_id = ? AND soort = ? AND sleutel = ?",
            (self.project_id, soort, sleutel),
        )
        if not rows:
            return None
        self.conn.execute(
            "UPDATE reviewer_cache SET treffers = treffers + 1"
            " WHERE project_id = ? AND soort = ? AND sleutel = ?",
            (self.project_id, soort, sleutel),
        )
        return rows[0]

    def cache_put(
        self, soort: str, sleutel: str, model: str, resultaat: str,
        tokens_in: int = 0, tokens_out: int = 0,
    ) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO reviewer_cache (project_id, soort, sleutel, model,"
            " resultaat, tokens_in, tokens_out, treffers, created_at)"
            " VALUES (?,?,?,?,?,?,?,COALESCE((SELECT treffers FROM reviewer_cache"
            " WHERE project_id = ? AND soort = ? AND sleutel = ?), 0), ?)",
            (self.project_id, soort, sleutel, model, resultaat, tokens_in, tokens_out,
             self.project_id, soort, sleutel, now()),
        )

    def cache_stats(self) -> dict:
        row = self.conn.execute(
            "SELECT COUNT(*) AS regels, COALESCE(SUM(treffers), 0) AS treffers,"
            " COALESCE(SUM(treffers * tokens_in), 0) AS bespaard_in,"
            " COALESCE(SUM(treffers * tokens_out), 0) AS bespaard_uit"
            " FROM reviewer_cache WHERE project_id = ?",
            (self.project_id,),
        ).fetchone()
        return dict(row)

    def spend_month(self, maand: str) -> float:
        """maand als 'JJJJ-MM'."""
        row = self.conn.execute(
            "SELECT COALESCE(SUM(cost_eur), 0) AS total FROM calls"
            " WHERE project_id = ? AND substr(day, 1, 7) = ?",
            (self.project_id, maand),
        ).fetchone()
        return float(row["total"])

    # -- antwoordsessies en audit spoor ----------------------------------
    def start_answer_session(
        self, question_id: int, channel: str, task_id: int | None = None
    ) -> int:
        stamp = now()
        cur = self.conn.execute(
            "INSERT INTO answer_sessions (project_id, question_id, task_id, channel,"
            " state, created_at, updated_at) VALUES (?,?,?,?,?,?,?)",
            (self.project_id, question_id, task_id, channel, "asked", stamp, stamp),
        )
        return int(cur.lastrowid)

    def answer_session(self, session_id: int) -> sqlite3.Row | None:
        rows = self._q(
            "SELECT * FROM answer_sessions WHERE id = ? AND project_id = ?",
            (session_id, self.project_id),
        )
        return rows[0] if rows else None

    def open_answer_session(self, question_id: int) -> sqlite3.Row | None:
        rows = self._q(
            "SELECT * FROM answer_sessions WHERE project_id = ? AND question_id = ?"
            " AND state NOT IN ('resolved', 'returned_to_block') ORDER BY id DESC LIMIT 1",
            (self.project_id, question_id),
        )
        return rows[0] if rows else None

    def set_answer_session(self, session_id: int, **fields: Any) -> None:
        allowed = {"state", "clarifications", "interpretation", "decision_id"}
        unknown = set(fields) - allowed
        if unknown:
            raise ValueError(f"onbekende sessievelden: {sorted(unknown)}")
        sets = ", ".join(f"{k} = ?" for k in fields)
        self.conn.execute(
            f"UPDATE answer_sessions SET {sets}, updated_at = ?"
            " WHERE id = ? AND project_id = ?",
            (*fields.values(), now(), session_id, self.project_id),
        )

    def add_turn(
        self, session_id: int, direction: str, channel: str, text: str,
        confidence: float | None = None, note: str = "",
    ) -> None:
        self.conn.execute(
            "INSERT INTO answer_turns (project_id, session_id, ts, direction, channel,"
            " text, confidence, note) VALUES (?,?,?,?,?,?,?,?)",
            (self.project_id, session_id, now(), direction, channel, text, confidence, note),
        )

    def turns(self, session_id: int) -> list[sqlite3.Row]:
        return self._q(
            "SELECT * FROM answer_turns WHERE project_id = ? AND session_id = ? ORDER BY id",
            (self.project_id, session_id),
        )

    # -- geen-vooruitgang-detector ---------------------------------------
    def open_run(self, task_id: int) -> int | None:
        """De nog niet afgesloten run van deze taak, als die er is."""
        rij = self._q(
            "SELECT id FROM runs WHERE project_id = ? AND task_id = ?"
            " AND ended_at IS NULL ORDER BY id DESC LIMIT 1",
            (self.project_id, task_id),
        )
        return int(rij[0]["id"]) if rij else None

    def mark_run_wasted(self, run_id: int, reason: str) -> int:
        """Markeert de aanroepen van een run als verspild.

        Het geld is uitgegeven en dat verandert niet. Wat wel verandert is of we
        het kunnen zien: zonder markering verdwijnt verspilling in het totaal en
        lijkt een dure mislukking net zo duur als nuttig werk.
        """
        cur = self.conn.execute(
            "UPDATE calls SET wasted_reason = ?"
            " WHERE run_id = ? AND project_id = ? AND wasted_reason IS NULL",
            (reason, run_id, self.project_id),
        )
        return int(cur.rowcount or 0)

    def signature_seen(self, task_id: int, signature: str) -> bool:
        """Kijkt alleen. Legt niets vast.

        Nodig omdat vastleggen en controleren niet hetzelfde moment zijn: een
        aanroep die door de budgetrem wordt tegengehouden heeft nooit
        plaatsgevonden en mag de taak niet permanent blokkeren.
        """
        if not signature:
            return False
        return bool(self._q(
            "SELECT id FROM signatures WHERE project_id = ? AND task_id = ?"
            " AND signature = ?",
            (self.project_id, task_id, signature),
        ))

    def remember_signature(self, task_id: int, signature: str) -> None:
        """Legt vast dat deze context werkelijk verstuurd is."""
        if not signature or self.signature_seen(task_id, signature):
            return
        self.conn.execute(
            "INSERT INTO signatures (project_id, task_id, signature, created_at)"
            " VALUES (?,?,?,?)",
            (self.project_id, task_id, signature, now()),
        )

    def seen_signature(self, task_id: int, signature: str) -> bool:
        if not signature:
            return False
        rows = self._q(
            "SELECT id FROM signatures WHERE project_id = ? AND task_id = ? AND signature = ?",
            (self.project_id, task_id, signature),
        )
        if rows:
            return True
        self.conn.execute(
            "INSERT INTO signatures (project_id, task_id, signature, created_at)"
            " VALUES (?,?,?,?)",
            (self.project_id, task_id, signature, now()),
        )
        return False
