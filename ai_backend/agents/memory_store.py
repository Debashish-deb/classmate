from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional


class MemoryStore:
    def put_kv(self, session_id: str, key: str, value: Any) -> None:
        raise NotImplementedError

    def get_kv(self, session_id: str, key: str) -> Optional[Any]:
        raise NotImplementedError

    def add_event(self, session_id: str, event_type: str, payload: Dict[str, Any], created_at: datetime) -> None:
        raise NotImplementedError

    def load_kv(self, session_id: str) -> Dict[str, Any]:
        raise NotImplementedError

    def load_events(self, session_id: str) -> List[Dict[str, Any]]:
        raise NotImplementedError


class SQLiteMemoryStore(MemoryStore):
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.getenv("AGENT_MEMORY_DB", "./agent_memory.db")
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_kv (
                    session_id TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY(session_id, key)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

    def put_kv(self, session_id: str, key: str, value: Any) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO agent_kv(session_id, key, value_json, updated_at)
                VALUES(?, ?, ?, ?)
                ON CONFLICT(session_id, key) DO UPDATE SET
                    value_json=excluded.value_json,
                    updated_at=excluded.updated_at
                """,
                (session_id, key, json.dumps(value, default=str), datetime.utcnow().isoformat()),
            )

    def get_kv(self, session_id: str, key: str) -> Optional[Any]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT value_json FROM agent_kv WHERE session_id=? AND key=?",
                (session_id, key),
            ).fetchone()
            if not row:
                return None
            return json.loads(row["value_json"])

    def add_event(self, session_id: str, event_type: str, payload: Dict[str, Any], created_at: datetime) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO agent_events(session_id, type, payload_json, created_at) VALUES(?, ?, ?, ?)",
                (session_id, event_type, json.dumps(payload, default=str), created_at.isoformat()),
            )

    def load_kv(self, session_id: str) -> Dict[str, Any]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT key, value_json FROM agent_kv WHERE session_id=?",
                (session_id,),
            ).fetchall()
            out: Dict[str, Any] = {}
            for r in rows:
                out[r["key"]] = json.loads(r["value_json"])
            return out

    def load_events(self, session_id: str) -> List[Dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT type, payload_json, created_at FROM agent_events WHERE session_id=? ORDER BY id ASC",
                (session_id,),
            ).fetchall()
            return [
                {"type": r["type"], "payload": json.loads(r["payload_json"]), "created_at": r["created_at"]}
                for r in rows
            ]


def build_default_store() -> MemoryStore:
    # Default to SQLite (works everywhere). Future: RedisMemoryStore.
    return SQLiteMemoryStore()
