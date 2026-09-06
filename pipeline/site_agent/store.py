from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import Analysis, Observation, SCHEMA_VERSION, as_record


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class KnowledgeStore:
    """SQLite-backed evidence store with a versioned portable JSON export."""

    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self._create_schema()

    def _create_schema(self) -> None:
        self.connection.executescript(
            """
            PRAGMA foreign_keys = ON;
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS runs (
                id TEXT PRIMARY KEY,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                status TEXT NOT NULL,
                config_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS pages (
                id TEXT PRIMARY KEY,
                normalized_url TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                first_seen_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS states (
                id TEXT PRIMARY KEY,
                page_id TEXT NOT NULL REFERENCES pages(id),
                fingerprint TEXT NOT NULL,
                observed_at TEXT NOT NULL,
                observation_json TEXT NOT NULL,
                analysis_json TEXT,
                UNIQUE(page_id, fingerprint)
            );
            CREATE TABLE IF NOT EXISTS actions (
                id TEXT PRIMARY KEY,
                state_id TEXT NOT NULL REFERENCES states(id),
                control_json TEXT NOT NULL,
                safety TEXT NOT NULL,
                safety_reason TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'unexplored'
            );
            CREATE TABLE IF NOT EXISTS transitions (
                id TEXT PRIMARY KEY,
                source_state_id TEXT NOT NULL REFERENCES states(id),
                action_id TEXT NOT NULL REFERENCES actions(id),
                destination_state_id TEXT REFERENCES states(id),
                status TEXT NOT NULL,
                observed_result TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL REFERENCES runs(id),
                kind TEXT NOT NULL,
                target TEXT NOT NULL,
                status TEXT NOT NULL,
                detail TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS findings (
                id TEXT PRIMARY KEY,
                state_id TEXT REFERENCES states(id),
                kind TEXT NOT NULL,
                statement TEXT NOT NULL,
                status TEXT NOT NULL,
                confidence REAL NOT NULL,
                evidence_json TEXT NOT NULL,
                producer TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        self.connection.execute(
            "INSERT OR REPLACE INTO metadata(key, value) VALUES('schema_version', ?)",
            (SCHEMA_VERSION,),
        )
        self.connection.commit()

    def start_run(self, run_id: str, config: dict[str, Any]) -> None:
        self.connection.execute(
            "INSERT OR REPLACE INTO runs(id, started_at, status, config_json) VALUES(?, ?, ?, ?)",
            (run_id, utc_now(), "running", json.dumps(config, sort_keys=True)),
        )
        self.connection.commit()

    def complete_run(self, run_id: str, status: str = "completed") -> None:
        self.connection.execute(
            "UPDATE runs SET completed_at = ?, status = ? WHERE id = ?",
            (utc_now(), status, run_id),
        )
        self.connection.commit()

    def save_state(
        self,
        page_id: str,
        state_id: str,
        observation: Observation,
        analysis: Analysis | None,
        action_rows: list[tuple[str, dict[str, Any], str, str]],
    ) -> bool:
        now = utc_now()
        existing = self.connection.execute(
            "SELECT id FROM states WHERE page_id = ? AND fingerprint = ?",
            (page_id, observation.fingerprint),
        ).fetchone()
        self.connection.execute(
            """INSERT INTO pages(id, normalized_url, title, first_seen_at, last_seen_at)
               VALUES(?, ?, ?, ?, ?)
               ON CONFLICT(normalized_url) DO UPDATE SET title=excluded.title, last_seen_at=excluded.last_seen_at""",
            (page_id, observation.url, observation.title, now, now),
        )
        if existing:
            self.connection.commit()
            return False
        self.connection.execute(
            "INSERT INTO states(id, page_id, fingerprint, observed_at, observation_json, analysis_json) VALUES(?, ?, ?, ?, ?, ?)",
            (
                state_id,
                page_id,
                observation.fingerprint,
                now,
                json.dumps(as_record(observation), sort_keys=True),
                json.dumps(as_record(analysis), sort_keys=True) if analysis else None,
            ),
        )
        for action_id, control, safety, reason in action_rows:
            self.connection.execute(
                "INSERT INTO actions(id, state_id, control_json, safety, safety_reason) VALUES(?, ?, ?, ?, ?)",
                (action_id, state_id, json.dumps(control, sort_keys=True), safety, reason),
            )
        self.connection.commit()
        return True

    def save_finding(
        self,
        finding_id: str,
        state_id: str,
        kind: str,
        statement: str,
        status: str,
        confidence: float,
        evidence: list[str],
        producer: str,
    ) -> None:
        self.connection.execute(
            "INSERT OR IGNORE INTO findings VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                finding_id,
                state_id,
                kind,
                statement,
                status,
                max(0.0, min(1.0, confidence)),
                json.dumps(evidence),
                producer,
                utc_now(),
            ),
        )
        self.connection.commit()

    def save_event(
        self,
        event_id: str,
        run_id: str,
        kind: str,
        target: str,
        status: str,
        detail: str,
    ) -> None:
        self.connection.execute(
            "INSERT OR IGNORE INTO events VALUES(?, ?, ?, ?, ?, ?, ?)",
            (event_id, run_id, kind, target, status, detail, utc_now()),
        )
        self.connection.commit()

    def save_transition(
        self,
        transition_id: str,
        source_state_id: str,
        action_id: str,
        destination_state_id: str | None,
        status: str,
        observed_result: str,
    ) -> None:
        self.connection.execute(
            "INSERT OR IGNORE INTO transitions VALUES(?, ?, ?, ?, ?, ?, ?)",
            (
                transition_id,
                source_state_id,
                action_id,
                destination_state_id,
                status,
                observed_result,
                utc_now(),
            ),
        )
        self.connection.execute(
            "UPDATE actions SET status = ? WHERE id = ?",
            ("explored" if status == "verified" else status, action_id),
        )
        self.connection.commit()

    def export_snapshot(self, output_path: Path | str) -> Path:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload: dict[str, Any] = {"schema_version": SCHEMA_VERSION}
        for table in ("runs", "pages", "states", "actions", "transitions", "events", "findings"):
            rows = [dict(row) for row in self.connection.execute(f"SELECT * FROM {table} ORDER BY rowid")]
            for row in rows:
                for key in tuple(row):
                    if key.endswith("_json") and row[key] is not None:
                        row[key.removesuffix("_json")] = json.loads(row.pop(key))
            payload[table] = rows
        target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return target

    def coverage(self) -> dict[str, int]:
        result = {}
        for table in ("pages", "states", "actions", "transitions", "events", "findings"):
            result[table] = int(self.connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
        result["blocked_actions"] = int(
            self.connection.execute("SELECT COUNT(*) FROM actions WHERE safety = 'blocked'").fetchone()[0]
        )
        result["unexplored_actions"] = int(
            self.connection.execute("SELECT COUNT(*) FROM actions WHERE status = 'unexplored'").fetchone()[0]
        )
        result["failed_events"] = int(
            self.connection.execute("SELECT COUNT(*) FROM events WHERE status = 'failed'").fetchone()[0]
        )
        return result

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "KnowledgeStore":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
