"""Store — the unified persistence interface.

Every concrete store (Checkpoint/Session/Artifact backends) conforms to this
shape, which is what lets engine and worker be stateless. See §9.1.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Store(Protocol):
    async def save(self, key: str, value: Any, **meta: Any) -> None: ...
    async def load(self, key: str) -> Any | None: ...
    async def list(self, **filters: Any) -> list[Any]: ...
    async def delete(self, key: str) -> bool: ...
    async def health(self) -> bool: ...
