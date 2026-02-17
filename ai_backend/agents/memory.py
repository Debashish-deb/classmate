from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .memory_store import MemoryStore


@dataclass
class MemoryEvent:
    type: str
    payload: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.utcnow)


class AgentMemory:
    def __init__(self, store: Optional[MemoryStore] = None):
        self._events_by_session: Dict[str, List[MemoryEvent]] = {}
        self._kv_by_session: Dict[str, Dict[str, Any]] = {}
        self._loaded_sessions: set[str] = set()
        self._store = store

    def _ensure_loaded(self, session_id: str) -> None:
        if session_id in self._loaded_sessions:
            return
        self._loaded_sessions.add(session_id)

        if not self._store:
            return

        try:
            kv = self._store.load_kv(session_id)
            self._kv_by_session.setdefault(session_id, {}).update(kv)
        except Exception:
            # Persistence is best-effort
            pass

        try:
            events = self._store.load_events(session_id)
            loaded: List[MemoryEvent] = []
            for e in events:
                created_at_raw = e.get("created_at")
                try:
                    created_at = datetime.fromisoformat(created_at_raw) if created_at_raw else datetime.utcnow()
                except Exception:
                    created_at = datetime.utcnow()
                loaded.append(MemoryEvent(type=e.get("type", "event"), payload=e.get("payload", {}), created_at=created_at))
            if loaded:
                self._events_by_session.setdefault(session_id, []).extend(loaded)
        except Exception:
            pass

    def put(self, session_id: str, key: str, value: Any) -> None:
        self._ensure_loaded(session_id)
        self._kv_by_session.setdefault(session_id, {})[key] = value
        if self._store:
            try:
                self._store.put_kv(session_id, key, value)
            except Exception:
                pass

    def get(self, session_id: str, key: str, default: Any = None) -> Any:
        self._ensure_loaded(session_id)
        return self._kv_by_session.get(session_id, {}).get(key, default)

    def add_event(self, session_id: str, event_type: str, payload: Dict[str, Any]) -> None:
        self._ensure_loaded(session_id)
        ev = MemoryEvent(type=event_type, payload=payload)
        self._events_by_session.setdefault(session_id, []).append(ev)
        if self._store:
            try:
                self._store.add_event(session_id, event_type, payload, ev.created_at)
            except Exception:
                pass

    def events(self, session_id: str) -> List[MemoryEvent]:
        self._ensure_loaded(session_id)
        return list(self._events_by_session.get(session_id, []))

    def snapshot(self, session_id: str) -> Dict[str, Any]:
        self._ensure_loaded(session_id)
        return {
            "kv": dict(self._kv_by_session.get(session_id, {})),
            "events": [
                {"type": e.type, "payload": e.payload, "created_at": e.created_at.isoformat()}
                for e in self._events_by_session.get(session_id, [])
            ],
        }
