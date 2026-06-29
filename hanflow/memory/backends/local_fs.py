"""Local filesystem memory backend (scratch + session scopes)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class MemoryBackend(Protocol):
    async def read(self, key: str) -> Any | None: ...
    async def write(self, key: str, value: Any, ttl: int | None = None) -> None: ...
    async def delete(self, key: str) -> None: ...
    async def list_keys(self, prefix: str | None = None) -> list[str]: ...


class LocalFsMemoryBackend:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def _path(self, key: str) -> Path:
        # key may contain '/'; treat as relative path under root
        return (self.root / key).with_suffix(".json")

    async def read(self, key: str) -> Any | None:
        p = self._path(key)
        if not p.exists():
            return None
        return json.loads(p.read_text(encoding="utf-8"))

    async def write(self, key: str, value: Any, ttl: int | None = None) -> None:
        p = self._path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"value": value, "ttl": ttl}), encoding="utf-8")

    async def delete(self, key: str) -> None:
        p = self._path(key)
        if p.exists():
            p.unlink()

    async def list_keys(self, prefix: str | None = None) -> list[str]:
        if not self.root.exists():
            return []
        out: list[str] = []
        for p in self.root.rglob("*.json"):
            rel = str(p.relative_to(self.root))[: -len(".json")]
            rel = rel.replace("\\", "/")  # normalize windows paths
            if prefix is None or rel.startswith(prefix):
                out.append(rel)
        return out
