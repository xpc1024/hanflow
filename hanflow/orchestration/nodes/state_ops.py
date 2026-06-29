"""State-combination executors: Memory / Subworkflow (§3.6)."""

from __future__ import annotations

from typing import Any

from hanflow.core.dsl import NodeConfig, WorkflowNode
from hanflow.core.errors import HanflowError, MaxSubworkflowDepthExceeded
from hanflow.core.expr import interpolate
from hanflow.core.result import AtomResult, MemoryOp, NextAction


def _cfg(node: WorkflowNode) -> dict[str, Any]:
    return node.config.__pydantic_extra__ or {}


class MemoryExecutor:
    node_type = "Memory"

    def validate_config(self, config: NodeConfig) -> None:
        cfg = config.__pydantic_extra__ or {}
        if not cfg.get("action"):
            raise HanflowError("Memory requires 'action'")
        if not cfg.get("key"):
            raise HanflowError("Memory requires 'key'")

    async def run(self, ctx: Any, node: WorkflowNode, inputs: dict[str, Any]) -> AtomResult:
        cfg = _cfg(node)
        action = cfg["action"]
        scope = cfg.get("scope", "scratch")
        key = interpolate(cfg["key"], inputs)
        value = cfg.get("value")
        if isinstance(value, str):
            value = interpolate(value, inputs)
        result = await ctx.memory(MemoryOp(action=action, scope=scope, key=key, value=value))
        return AtomResult(output={"value": result}, next_action=NextAction(type="continue"))


class SubworkflowExecutor:
    node_type = "Subworkflow"

    def validate_config(self, config: NodeConfig) -> None:
        cfg = config.__pydantic_extra__ or {}
        if not cfg.get("ref"):
            raise HanflowError("Subworkflow requires 'ref'")

    async def run(self, ctx: Any, node: WorkflowNode, inputs: dict[str, Any]) -> AtomResult:
        cfg = _cfg(node)
        depth = inputs.get("__subworkflow_depth", 0) + 1
        if depth > 5:
            raise MaxSubworkflowDepthExceeded(
                f"Subworkflow nesting exceeded max depth 5 (at depth {depth})"
            )
        # The engine resolves 'ref' to a WorkflowDSL and compiles a subgraph;
        # for the synchronous executor we surface the ref + depth.
        return AtomResult(
            output={"ref": cfg["ref"], "depth": depth},
            next_action=NextAction(type="continue"),
        )
