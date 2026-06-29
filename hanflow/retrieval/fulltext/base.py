"""FullTextProvider Protocol + record types (§6.3)."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel


class FullTextRecord(BaseModel):
    id: str
    text: str
    metadata: dict[str, Any] = {}


class FullTextHit(BaseModel):
    id: str
    score: float
    metadata: dict[str, Any] = {}
    highlight: str | None = None


@runtime_checkable
class FullTextProvider(Protocol):
    name: str

    async def create_index(self, index: str, fields_schema: Any = None) -> None: ...

    async def index(self, index_name: str, documents: list[FullTextRecord]) -> None: ...

    async def search(
        self,
        index_name: str,
        query: str,
        *,
        top_k: int = 5,
        filter: Any = None,
    ) -> list[FullTextHit]: ...

    async def delete(
        self, index_name: str, *, ids: list[str] | None = None, filter: Any = None
    ) -> int: ...

    async def health(self) -> bool: ...
