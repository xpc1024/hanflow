"""FilesystemMemory — 3-scope memory (scratch/session/long_term) (§7.1).

scratch/session use a MemoryBackend (default local_fs). long_term routes to a
SessionStore keyed by user_id (cross-session). ``summarize`` joins source keys
into a single value (an LLM-backed summariser is wired in Phase 8 via the
runtime context; here we provide a deterministic join fallback for unit tests).
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, cast

from pydantic import BaseModel

from hanflow.memory.backends.local_fs import MemoryBackend

MemoryScope = Literal["scratch", "session", "long_term"]


class MemoryEntry(BaseModel):
    key: str
    value: Any
    scope: MemoryScope
    created_at: datetime
    updated_at: datetime
    ttl_seconds: int | None = None


class FilesystemMemory:
    def __init__(
        self,
        workspace_root: Path,
        session_store: Any,
        backends: dict[MemoryScope, MemoryBackend | None],
    ) -> None:
        self.workspace_root = Path(workspace_root)
        self.session_store = session_store
        self.backends = backends

    # --- scoped read/write/update/delete ---------------------------------- #
    async def read(self, scope: MemoryScope, key: str) -> MemoryEntry | None:
        backend = self.backends.get(scope)
        if backend is None:
            return None
        raw = await backend.read(key)
        if raw is None:
            return None
        now = datetime.now(UTC)
        return MemoryEntry(
            key=key,
            value=raw.get("value") if isinstance(raw, dict) else raw,
            scope=scope,
            created_at=now,
            updated_at=now,
            ttl_seconds=raw.get("ttl") if isinstance(raw, dict) else None,
        )

    async def write(
        self, scope: MemoryScope, key: str, value: Any, ttl_seconds: int | None = None
    ) -> None:
        backend = self._require_backend(scope)
        await backend.write(key, value, ttl_seconds)

    async def update(self, scope: MemoryScope, key: str, value: Any) -> None:
        # idempotent overwrite (same as write)
        await self.write(scope, key, value)

    async def delete(self, scope: MemoryScope, key: str) -> None:
        backend = self._require_backend(scope)
        await backend.delete(key)

    async def list_keys(self, scope: MemoryScope, prefix: str | None = None) -> list[str]:
        backend = self.backends.get(scope)
        if backend is None:
            return []
        return await backend.list_keys(prefix)

    async def summarize(self, scope: MemoryScope, source_keys: list[str]) -> str:
        # Deterministic join fallback. Phase 8 wires an LLM summariser via ctx.
        parts: list[str] = []
        for k in source_keys:
            entry = await self.read(scope, k)
            if entry is not None:
                parts.append(str(entry.value))
        return "\n".join(parts)

    # --- long_term (user-scoped, via SessionStore) ------------------------- #
    async def write_long_term(
        self, user_id: str, key: str, value: Any, ttl_seconds: int | None = None
    ) -> None:
        await self.session_store.put_memory(user_id, key, value, ttl_seconds)

    async def read_long_term(self, user_id: str, key: str) -> Any | None:
        return await self.session_store.get_memory(user_id, key)

    async def delete_long_term(self, user_id: str, key: str) -> bool:
        return cast(bool, await self.session_store.delete_memory(user_id, key))

    async def list_long_term(self, user_id: str, prefix: str | None = None) -> list[str]:
        return cast(list[str], await self.session_store.list_memory(user_id, prefix))

    def _require_backend(self, scope: MemoryScope) -> MemoryBackend:
        b = self.backends.get(scope)
        if b is None:
            raise ValueError(f"no backend configured for scope {scope!r}")
        return b
