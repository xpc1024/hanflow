"""InMemoryVectorProvider — deterministic, test-friendly (§6.2).

Implements the unified filter syntax ({field: value} / {field: {$gte: v}} /
{field: {$in: [...]}} / {$and| $or: [...]}) used across all backends.
"""

from __future__ import annotations

import math
from typing import Any

from hanflow.retrieval.vector.base import VectorHit, VectorProvider, VectorRecord


class InMemoryVectorProvider(VectorProvider):
    name = "memory"

    def __init__(self, dim: int = 8) -> None:
        self.dim = dim
        self._collections: dict[str, dict[str, VectorRecord]] = {}

    async def create_collection(
        self, collection: str, dim: int, metadata_schema: Any = None
    ) -> None:
        self._collections.setdefault(collection, {})
        self.dim = dim

    async def upsert(self, collection: str, vectors: list[VectorRecord]) -> None:
        store = self._collections.setdefault(collection, {})
        for v in vectors:
            store[v.id] = v

    async def search(
        self,
        collection: str,
        query_vec: list[float],
        *,
        top_k: int = 5,
        filter: Any = None,
    ) -> list[VectorHit]:
        store = self._collections.get(collection, {})
        scored: list[tuple[float, VectorRecord]] = []
        for rec in store.values():
            if not _match_filter(rec.metadata, filter):
                continue
            scored.append((_cosine(query_vec, rec.vector), rec))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [VectorHit(id=r.id, score=s, metadata=r.metadata) for s, r in scored[:top_k]]

    async def delete(
        self, collection: str, *, ids: list[str] | None = None, filter: Any = None
    ) -> int:
        store = self._collections.get(collection, {})
        if ids:
            return sum(1 for i in ids if store.pop(i, None) is not None)
        before = len(store)
        for k in list(store):
            if _match_filter(store[k].metadata, filter):
                store.pop(k)
        return before - len(store)

    async def count(self, collection: str) -> int:
        return len(self._collections.get(collection, {}))

    async def health(self) -> bool:
        return True


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _match_filter(metadata: dict[str, Any], filter: Any) -> bool:
    """Apply the unified filter syntax (§6.2)."""
    if not filter:
        return True
    if isinstance(filter, dict):
        for k, cond in filter.items():
            if k == "$and":
                if not all(_match_filter(metadata, sub) for sub in cond):
                    return False
            elif k == "$or":
                if not any(_match_filter(metadata, sub) for sub in cond):
                    return False
            else:
                actual = metadata.get(k)
                if isinstance(cond, dict):
                    if "$gte" in cond and not (actual is not None and actual >= cond["$gte"]):
                        return False
                    if "$lte" in cond and not (actual is not None and actual <= cond["$lte"]):
                        return False
                    if "$in" in cond and actual not in cond["$in"]:
                        return False
                elif actual != cond:
                    return False
    return True
