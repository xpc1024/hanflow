"""HybridStrategy — fuse vector + fulltext hits (§6.4)."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel


class FusedHit(BaseModel):
    id: str
    score: float
    sources: list[str] = []
    metadata: dict[str, Any] = {}


@runtime_checkable
class HybridStrategy(Protocol):
    name: str

    def fuse(
        self,
        vector_hits: list[Any],
        fulltext_hits: list[Any],
        top_k: int,
    ) -> list[FusedHit]: ...


class RRFFusion:
    """Reciprocal Rank Fusion (recommended default): score = Σ 1/(k + rank)."""

    name = "rrf"

    def __init__(self, k: int = 60) -> None:
        self.k = k

    def fuse(self, vector_hits: list[Any], fulltext_hits: list[Any], top_k: int) -> list[FusedHit]:
        scores: dict[str, float] = {}
        sources: dict[str, set[str]] = {}
        meta: dict[str, dict[str, Any]] = {}
        for rank, h in enumerate(vector_hits):
            scores[h.id] = scores.get(h.id, 0) + 1 / (self.k + rank + 1)
            sources.setdefault(h.id, set()).add("vector")
            meta.setdefault(h.id, dict(h.metadata))
        for rank, h in enumerate(fulltext_hits):
            scores[h.id] = scores.get(h.id, 0) + 1 / (self.k + rank + 1)
            sources.setdefault(h.id, set()).add("fulltext")
            meta.setdefault(h.id, dict(h.metadata))
        ordered = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        return [
            FusedHit(id=i, score=s, sources=sorted(sources[i]), metadata=meta[i])
            for i, s in ordered
        ]


class WeightedFusion:
    """score = w_v * norm(vec) + w_f * norm(ft)."""

    name = "weighted"

    def __init__(self, vector_weight: float = 0.5, fulltext_weight: float = 0.5) -> None:
        self.vector_weight = vector_weight
        self.fulltext_weight = fulltext_weight

    def fuse(self, vector_hits: list[Any], fulltext_hits: list[Any], top_k: int) -> list[FusedHit]:
        def _norm(hits: list[Any]) -> dict[str, float]:
            if not hits:
                return {}
            mx = max(h.score for h in hits)
            mn = min(h.score for h in hits)
            span = mx - mn or 1.0
            return {h.id: (h.score - mn) / span for h in hits}

        vn = _norm(vector_hits)
        fn = _norm(fulltext_hits)
        scores: dict[str, float] = {}
        sources: dict[str, set[str]] = {}
        meta: dict[str, dict[str, Any]] = {}
        for h in vector_hits:
            scores[h.id] = scores.get(h.id, 0) + self.vector_weight * vn[h.id]
            sources.setdefault(h.id, set()).add("vector")
            meta.setdefault(h.id, dict(h.metadata))
        for h in fulltext_hits:
            scores[h.id] = scores.get(h.id, 0) + self.fulltext_weight * fn[h.id]
            sources.setdefault(h.id, set()).add("fulltext")
            meta.setdefault(h.id, dict(h.metadata))
        ordered = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        return [
            FusedHit(id=i, score=s, sources=sorted(sources[i]), metadata=meta[i])
            for i, s in ordered
        ]


class CascadeFusion:
    """Fulltext recall → vector rerank."""

    name = "cascade"

    def __init__(self, recall_top_k: int = 50) -> None:
        self.recall_top_k = recall_top_k

    def fuse(self, vector_hits: list[Any], fulltext_hits: list[Any], top_k: int) -> list[FusedHit]:
        recalled = fulltext_hits[: self.recall_top_k] or vector_hits[: self.recall_top_k]
        vec_by_id = {h.id: h for h in vector_hits}
        reranked: list[tuple[float, Any, str]] = []
        for h in recalled:
            vh = vec_by_id.get(h.id)
            score = vh.score if vh else 0.0
            reranked.append((score, h, "fulltext"))
        for h in vector_hits:
            if h.id not in {r[1].id for r in reranked}:
                reranked.append((h.score, h, "vector"))
        reranked.sort(key=lambda x: x[0], reverse=True)
        out: list[FusedHit] = []
        for score, h, src in reranked[:top_k]:
            out.append(FusedHit(id=h.id, score=score, sources=[src], metadata=dict(h.metadata)))
        return out
