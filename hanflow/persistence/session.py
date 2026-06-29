"""SessionStore — session metadata + cross-session long-term memory.

Backends: sqlite (KV) default / postgres / mongo (later). Long-term memory is
keyed by user_id under a dedicated ``memory:<user_id>`` scope. See §9.3.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel

from hanflow.persistence.backends.sqlite import SqliteKVBackend

SessionStatus = Literal["active", "paused", "closed"]

_SESSION_SCOPE = "sessions"
_MEMORY_SCOPE = "memory"


class Session(BaseModel):
    session_id: str
    user_id: str | None = None
    run_ids: list[str] = []
    status: SessionStatus = "active"
    created_at: str
    updated_at: str
    metadata: dict[str, Any] = {}


class MemoryEntry(BaseModel):
    key: str
    value: Any
    scope: str
    created_at: datetime
    updated_at: datetime
    ttl_seconds: int | None = None


class SessionStore:
    """Session + long-term memory on top of a KV backend."""

    def __init__(self, kv: SqliteKVBackend) -> None:
        self.kv = kv

    # --- sessions -----------------------------------------------------------
    async def create_session(self, session: Session) -> str:
        await self.kv.put(_SESSION_SCOPE, session.session_id, session.model_dump_json())
        return session.session_id

    async def get_session(self, session_id: str) -> Session | None:
        raw = await self.kv.get(_SESSION_SCOPE, session_id)
        return Session.model_validate_json(raw) if raw else None

    async def list_sessions(
        self, *, user_id: str | None = None, status: SessionStatus | None = None
    ) -> list[Session]:
        rows = await self.kv.list(_SESSION_SCOPE)
        sessions = [Session.model_validate_json(v) for _, v in rows]
        if user_id is not None:
            sessions = [s for s in sessions if s.user_id == user_id]
        if status is not None:
            sessions = [s for s in sessions if s.status == status]
        return sessions

    async def update_session(self, session_id: str, **fields: Any) -> None:
        s = await self.get_session(session_id)
        if s is None:
            raise KeyError(f"session not found: {session_id}")
        updated = s.model_copy(update={**fields, "updated_at": datetime.now(UTC).isoformat()})
        await self.kv.put(_SESSION_SCOPE, session_id, updated.model_dump_json())

    async def close_session(self, session_id: str) -> None:
        await self.update_session(session_id, status="closed")

    # --- long-term memory ---------------------------------------------------
    async def put_memory(
        self, user_id: str, key: str, value: Any, ttl_seconds: int | None = None
    ) -> None:
        entry = MemoryEntry(
            key=key,
            value=value,
            scope=_MEMORY_SCOPE,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            ttl_seconds=ttl_seconds,
        )
        await self.kv.put(f"{_MEMORY_SCOPE}:{user_id}", key, entry.model_dump_json())

    async def get_memory(self, user_id: str, key: str) -> Any | None:
        raw = await self.kv.get(f"{_MEMORY_SCOPE}:{user_id}", key)
        if raw is None:
            return None
        return MemoryEntry.model_validate_json(raw).value

    async def list_memory(self, user_id: str, prefix: str | None = None) -> list[str]:
        rows = await self.kv.list(f"{_MEMORY_SCOPE}:{user_id}", prefix=prefix)
        return [k for k, _ in rows]

    async def delete_memory(self, user_id: str, key: str) -> bool:
        return await self.kv.delete(f"{_MEMORY_SCOPE}:{user_id}", key)
