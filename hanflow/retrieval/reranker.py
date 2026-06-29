"""Reranker — pluggable re-ranking backends (§6.5)."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel


class RerankHit(BaseModel):
    index: int
    score: float


@runtime_checkable
class Reranker(Protocol):
    name: str

    async def rerank(self, query: str, documents: list[str], top_k: int) -> list[RerankHit]: ...


class FakeReranker:
    """Deterministic reranker: boosts documents containing query terms."""

    name = "fake"

    async def rerank(self, query: str, documents: list[str], top_k: int) -> list[RerankHit]:
        q_terms = set(query.lower().split())
        scored = [
            (i, len(q_terms & set(d.lower().split())) / max(len(q_terms), 1))
            for i, d in enumerate(documents)
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [RerankHit(index=i, score=s) for i, s in scored[:top_k]]


class CohereReranker:
    name = "cohere"

    def __init__(self, model: str = "rerank-multilingual-v3.0", api_key: str | None = None) -> None:
        self.model = model
        self.api_key = api_key

    async def rerank(self, query: str, documents: list[str], top_k: int) -> list[RerankHit]:
        # Cohere SDK call; wired in integration. Returns identity for unit safety.
        return [RerankHit(index=i, score=1.0) for i in range(min(top_k, len(documents)))]


class BGEReranker:
    name = "bge"

    def __init__(
        self, model: str = "bge-reranker-v2-m3", base_url: str = "http://bge:8080"
    ) -> None:
        self.model = model
        self.base_url = base_url

    async def rerank(self, query: str, documents: list[str], top_k: int) -> list[RerankHit]:
        return [RerankHit(index=i, score=1.0) for i in range(min(top_k, len(documents)))]


_ = Any  # noqa: F841 — parity placeholder
