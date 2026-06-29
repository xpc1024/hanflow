"""Knowledge executor — retrieval primitive (§3.7)."""

from __future__ import annotations

from typing import Any

from hanflow.core.dsl import NodeConfig, WorkflowNode
from hanflow.core.errors import HanflowError
from hanflow.core.expr import interpolate
from hanflow.core.result import AtomResult, NextAction


def _cfg(node: WorkflowNode) -> dict[str, Any]:
    return node.config.__pydantic_extra__ or {}


class KnowledgeExecutor:
    node_type = "Knowledge"

    def validate_config(self, config: NodeConfig) -> None:
        cfg = config.__pydantic_extra__ or {}
        if not cfg.get("store"):
            raise HanflowError("Knowledge requires 'store'")
        if not cfg.get("query"):
            raise HanflowError("Knowledge requires 'query'")

    async def run(self, ctx: Any, node: WorkflowNode, inputs: dict[str, Any]) -> AtomResult:
        cfg = _cfg(node)
        store = cfg["store"]
        query = interpolate(cfg["query"], inputs)
        top_k = cfg.get("top_k", 5)
        rerank = cfg.get("rerank")
        filter_ = cfg.get("filter")
        min_score = cfg.get("min_score", 0.0)
        chunks = await ctx.retrieve(store, query, top_k=top_k, rerank=rerank, filter=filter_)
        if min_score:
            chunks = [c for c in chunks if c.score >= min_score]
        return AtomResult(
            output={"chunks": [c.model_dump(mode="json") for c in chunks], "count": len(chunks)},
            sources=[c.source for c in chunks],
            next_action=NextAction(type="continue"),
        )
