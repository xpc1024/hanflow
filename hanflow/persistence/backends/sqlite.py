"""Sqlite backend for CheckpointStore + SessionStore.

Wraps LangGraph's official ``AsyncSqliteSaver`` for checkpoints (see detailed
design §9.2), and provides a minimal async KV table for sessions (§9.3).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver


class SqliteCheckpointBackend:
    """Owns an AsyncSqliteSaver; CheckpointStore delegates put/get/list to it."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)

    @asynccontextmanager
    async def saver(self) -> AsyncIterator[AsyncSqliteSaver]:
        import aiosqlite

        async with aiosqlite.connect(self.path) as conn:
            saver = AsyncSqliteSaver(conn)
            await saver.setup()
            yield saver

    async def health(self) -> bool:
        try:
            async with self.saver() as _:
                return True
        except Exception:
            return False


class SqliteKVBackend:
    """Tiny async KV for SessionStore (long_term memory + session rows).

    Schema created lazily in ``setup()``.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)

    async def setup(self) -> None:
        import aiosqlite

        async with aiosqlite.connect(self.path) as conn:
            await conn.execute(
                """CREATE TABLE IF NOT EXISTS kv (
                       scope TEXT NOT NULL,
                       key TEXT NOT NULL,
                       value TEXT NOT NULL,
                       updated_at TEXT NOT NULL,
                       PRIMARY KEY (scope, key)
                   )"""
            )
            await conn.commit()

    async def put(self, scope: str, key: str, value: str) -> None:
        from datetime import UTC, datetime

        import aiosqlite

        async with aiosqlite.connect(self.path) as conn:
            await conn.execute(
                """INSERT INTO kv(scope, key, value, updated_at)
                   VALUES(?, ?, ?, ?)
                   ON CONFLICT(scope, key) DO UPDATE SET
                       value=excluded.value, updated_at=excluded.updated_at""",
                (scope, key, value, datetime.now(UTC).isoformat()),
            )
            await conn.commit()

    async def get(self, scope: str, key: str) -> str | None:
        import aiosqlite

        async with aiosqlite.connect(self.path) as conn:
            cur = await conn.execute("SELECT value FROM kv WHERE scope=? AND key=?", (scope, key))
            row = await cur.fetchone()
            return row[0] if row else None

    async def delete(self, scope: str, key: str) -> bool:
        import aiosqlite

        async with aiosqlite.connect(self.path) as conn:
            cur = await conn.execute("DELETE FROM kv WHERE scope=? AND key=?", (scope, key))
            await conn.commit()
            return cur.rowcount > 0

    async def list(self, scope: str, prefix: str | None = None) -> list[tuple[str, str]]:
        import aiosqlite

        async with aiosqlite.connect(self.path) as conn:
            if prefix:
                cur = await conn.execute(
                    "SELECT key, value FROM kv WHERE scope=? AND key LIKE ?",
                    (scope, f"{prefix}%"),
                )
            else:
                cur = await conn.execute("SELECT key, value FROM kv WHERE scope=?", (scope,))
            return [(r[0], r[1]) async for r in cur]

    async def health(self) -> bool:
        try:
            await self.setup()
            return True
        except Exception:
            return False
