"""SearchProvider — unified retrieval entry (§6.1).

Three implementations:
- VectorSearchProvider  : VectorProvider + EmbeddingProvider
- FullTextSearchProvider: FullTextProvider
- HybridSearchProvider  : vector + fulltext in parallel, fused

All return ``list[Chunk]`` (with a ``Source`` so provenance is uniform).
"""

from __future__ import annotations

import asyncio
from typing import Any, Protocol, runtime_checkable

from hanflow.core.result import Chunk, Source
from hanflow.retrieval.embedding import EmbeddingProvider
from hanflow.retrieval.fulltext.base import FullTextProvider
from hanflow.retrieval.hybrid import HybridStrategy, RRFFusion
from hanflow.retrieval.vector.base import VectorProvider


@runtime_checkable
class SearchProvider(Protocol):
    name: str

    async def search(
        self,
        store: str,
        query: str,
        *,
        top_k: int = 5,
        filter: dict[str, Any] | None = None,
        min_score: float = 0.0,
    ) -> list[Chunk]: ...

    async def upsert(self, documents: list[Any], *, collection: str | None = None) -> Any: ...

    async def delete(self, **kwargs: Any) -> int: ...


class VectorSearchProvider:
    def __init__(
        self,
        vector: VectorProvider,
        embedding: EmbeddingProvider,
        name: str = "vector",
    ) -> None:
        self.vector = vector
        self.embedding = embedding
        self.name = name

    async def search(
        self,
        collection: str,
        query: str,
        *,
        top_k: int = 5,
        filter: dict[str, Any] | None = None,
        min_score: float = 0.0,
    ) -> list[Chunk]:
        qv = (await self.embedding.embed([query]))[0]
        hits = await self.vector.search(collection, qv, top_k=top_k, filter=filter)
        return [
            Chunk(
                text=h.metadata.get("text", ""),
                score=h.score,
                source=Source(source_id=h.id, kind="private_kb", extra=dict(h.metadata)),
                metadata=dict(h.metadata),
            )
            for h in hits
            if h.score >= min_score
        ]

    async def upsert(
        self,
        documents: list[Any],
        *,
        collection: str | None = None,
    ) -> Any:
        from hanflow.retrieval.vector.base import VectorRecord

        coll = collection or "default"
        texts = [d.content for d in documents]
        vectors = await self.embedding.embed(texts)
        records = [
            VectorRecord(id=d.id, vector=v, metadata={**d.metadata, "text": d.content})
            for d, v in zip(documents, vectors, strict=True)
        ]
        await self.vector.upsert(coll, records)
        return {"indexed": len(records)}

    async def delete(
        self, *, collection: str, ids: list[str] | None = None, filter: Any = None
    ) -> int:
        return await self.vector.delete(collection, ids=ids, filter=filter)


class FullTextSearchProvider:
    def __init__(self, fulltext: FullTextProvider, name: str = "fulltext") -> None:
        self.fulltext = fulltext
        self.name = name

    async def search(
        self,
        index: str,
        query: str,
        *,
        top_k: int = 5,
        filter: dict[str, Any] | None = None,
        min_score: float = 0.0,
    ) -> list[Chunk]:
        hits = await self.fulltext.search(index, query, top_k=top_k, filter=filter)
        return [
            Chunk(
                text=h.metadata.get("text", h.highlight or ""),
                score=h.score,
                source=Source(source_id=h.id, kind="private_kb", extra=dict(h.metadata)),
                metadata=dict(h.metadata),
            )
            for h in hits
            if h.score >= min_score
        ]

    async def upsert(
        self,
        documents: list[Any],
        *,
        collection: str | None = None,
    ) -> Any:
        from hanflow.retrieval.fulltext.base import FullTextRecord

        idx = collection or "default"
        records = [
            FullTextRecord(id=d.id, text=d.content, metadata={**d.metadata, "text": d.content})
            for d in documents
        ]
        await self.fulltext.index(idx, records)
        return {"indexed": len(records)}

    async def delete(
        self, *, collection: str, ids: list[str] | None = None, filter: Any = None
    ) -> int:
        return await self.fulltext.delete(collection, ids=ids, filter=filter)


class HybridSearchProvider:
    def __init__(
        self,
        vector: VectorProvider,
        fulltext: FullTextProvider,
        embedding: EmbeddingProvider,
        fusion: HybridStrategy | None = None,
        name: str = "hybrid",
    ) -> None:
        self.vector = vector
        self.fulltext = fulltext
        self.embedding = embedding
        self.fusion = fusion or RRFFusion()
        self.name = name

    async def search(
        self,
        collection: str,
        query: str,
        *,
        top_k: int = 5,
        filter: dict[str, Any] | None = None,
        min_score: float = 0.0,
    ) -> list[Chunk]:
        qv = (await self.embedding.embed([query]))[0]
        v_hits, ft_hits = await asyncio.gather(
            self.vector.search(collection, qv, top_k=top_k * 2, filter=filter),
            self.fulltext.search(collection, query, top_k=top_k * 2, filter=filter),
        )
        fused = self.fusion.fuse(v_hits, ft_hits, top_k)
        return [
            Chunk(
                text=f.metadata.get("text", ""),
                score=f.score,
                source=Source(source_id=f.id, kind="private_kb", extra=dict(f.metadata)),
                metadata=dict(f.metadata),
            )
            for f in fused
            if f.score >= min_score
        ]

    async def upsert(
        self,
        documents: list[Any],
        *,
        collection: str | None = None,
    ) -> Any:
        idx = collection or "default"
        v = await VectorSearchProvider(self.vector, self.embedding).upsert(
            documents, collection=idx
        )
        f = await FullTextSearchProvider(self.fulltext).upsert(documents, collection=idx)
        return {"vector": v, "fulltext": f}

    async def delete(
        self, *, collection: str, ids: list[str] | None = None, filter: Any = None
    ) -> int:
        nv = await self.vector.delete(collection, ids=ids, filter=filter)
        nf = await self.fulltext.delete(collection, ids=ids, filter=filter)
        return max(nv, nf)
