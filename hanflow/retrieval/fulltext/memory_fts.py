"""InMemoryFullTextProvider — token-overlap scoring (§6.3)."""

from __future__ import annotations

from typing import Any

from hanflow.retrieval.fulltext.base import FullTextHit, FullTextProvider, FullTextRecord
from hanflow.retrieval.vector.memory import _match_filter


class InMemoryFullTextProvider(FullTextProvider):
    name = "memory_fts"

    def __init__(self) -> None:
        self._indexes: dict[str, dict[str, FullTextRecord]] = {}

    async def create_index(self, index: str, fields_schema: Any = None) -> None:
        self._indexes.setdefault(index, {})

    async def index(self, index_name: str, documents: list[FullTextRecord]) -> None:
        store = self._indexes.setdefault(index_name, {})
        for d in documents:
            store[d.id] = d

    async def search(
        self,
        index_name: str,
        query: str,
        *,
        top_k: int = 5,
        filter: Any = None,
    ) -> list[FullTextHit]:
        store = self._indexes.get(index_name, {})
        q_terms = set(query.lower().split())
        scored: list[tuple[float, FullTextRecord]] = []
        for rec in store.values():
            if not _match_filter(rec.metadata, filter):
                continue
            terms = set(rec.text.lower().split())
            overlap = len(q_terms & terms)
            if overlap > 0:
                scored.append((overlap / max(len(q_terms), 1), rec))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [FullTextHit(id=r.id, score=s, metadata=r.metadata) for s, r in scored[:top_k]]

    async def delete(
        self, index_name: str, *, ids: list[str] | None = None, filter: Any = None
    ) -> int:
        store = self._indexes.get(index_name, {})
        if ids:
            return sum(1 for i in ids if store.pop(i, None) is not None)
        before = len(store)
        for k in list(store):
            if _match_filter(store[k].metadata, filter):
                store.pop(k)
        return before - len(store)

    async def health(self) -> bool:
        return True
