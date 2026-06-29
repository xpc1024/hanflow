"""VectorProvider Protocol + record types (§6.2)."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel


class VectorRecord(BaseModel):
    id: str
    vector: list[float]
    metadata: dict[str, Any] = {}


class VectorHit(BaseModel):
    id: str
    score: float
    metadata: dict[str, Any] = {}


@runtime_checkable
class VectorProvider(Protocol):
    name: str

    async def create_collection(
        self, collection: str, dim: int, metadata_schema: Any = None
    ) -> None: ...

    async def upsert(self, collection: str, vectors: list[VectorRecord]) -> None: ...

    async def search(
        self,
        collection: str,
        query_vec: list[float],
        *,
        top_k: int = 5,
        filter: Any = None,
    ) -> list[VectorHit]: ...

    async def delete(
        self, collection: str, *, ids: list[str] | None = None, filter: Any = None
    ) -> int: ...

    async def count(self, collection: str) -> int: ...

    async def health(self) -> bool: ...
