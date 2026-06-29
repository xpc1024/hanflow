"""Compiler — DSL → LangGraph StateGraph (§3.1).

4 steps: validate → build_graph → wire_edges → compile. Each node is wrapped
to read state → render templates → call executor.run → write NodeState + trace.
Control-flow primitives are mostly compile-time wiring; the wrapper handles
state bookkeeping and on_error policy uniformly.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel

from hanflow.core.dsl import WorkflowDSL, WorkflowNode
from hanflow.core.errors import HanflowError, NodeExecutionError
from hanflow.core.expr import interpolate
from hanflow.core.state import NexusState, NodeState


class CompiledGraph(BaseModel):
    graph: Any  # CompiledStateGraph
    dsl: WorkflowDSL
    entry_node: str
    exit_nodes: list[str]

    model_config = {"arbitrary_types_allowed": True}


class Compiler:
    def __init__(self, registry: Any) -> None:
        self.registry = registry

    def compile(
        self,
        dsl: WorkflowDSL,
        checkpoint: Any | None = None,
        ctx: Any | None = None,
    ) -> CompiledGraph:
        # validate configs against each executor
        for node in dsl.nodes:
            executor = self.registry.get(node.type)
            executor.validate_config(node.config)

        entry = _entry_node(dsl)
        exits = _exit_nodes(dsl)

        graph = StateGraph(NexusState)
        for node in dsl.nodes:
            executor = self.registry.get(node.type)
            graph.add_node(node.id, _wrap(executor, node, self.registry, ctx))

        graph.add_edge(START, entry)
        for node in dsl.nodes:
            successors = _resolve_successors(node, dsl)
            if node.condition:
                graph.add_conditional_edges(
                    node.id,
                    _make_router(node),
                    {succ: succ for succ in successors},
                )
            else:
                for succ in successors:
                    graph.add_edge(node.id, succ)
        for ex in exits:
            graph.add_edge(ex, END)

        compiled = graph.compile(checkpointer=checkpoint) if checkpoint else graph.compile()
        return CompiledGraph(graph=compiled, dsl=dsl, entry_node=entry, exit_nodes=exits)


def _entry_node(dsl: WorkflowDSL) -> str:
    for n in dsl.nodes:
        if not n.depends_on:
            return n.id
    raise HanflowError("DSL has no entry node")


def _exit_nodes(dsl: WorkflowDSL) -> list[str]:
    deps = {dep for n in dsl.nodes for dep in n.depends_on}
    return [n.id for n in dsl.nodes if n.id not in deps]


def _resolve_successors(node: WorkflowNode, dsl: WorkflowDSL) -> list[str]:
    successors: list[str] = []
    for other in dsl.nodes:
        if node.id in other.depends_on:
            successors.append(other.id)
    return successors


def _make_router(node: WorkflowNode) -> Any:
    condition = node.condition or ""

    def _route(state: Any) -> str:
        ctx_inputs = _collect_inputs(state, node)
        rendered = interpolate(condition, ctx_inputs) if "{{" in condition else condition
        # evaluate against node outputs (dotted paths)
        from hanflow.core.expr import evaluate

        try:
            if evaluate(rendered, ctx_inputs):
                # first successor is the "true" branch
                return ""
        except Exception:
            pass
        return ""

    return _route


def _collect_inputs(state: Any, node: WorkflowNode) -> dict[str, Any]:
    """Gather upstream node outputs as inputs for templating/conditions."""
    inputs: dict[str, Any] = {}
    if hasattr(state, "node_states"):
        for nid, ns in state.node_states.items():
            inputs[nid] = ns.outputs
    return inputs


def _wrap(executor: Any, node: WorkflowNode, registry: Any, ctx: Any | None = None) -> Any:
    """Build the LangGraph node function for one WorkflowNode.

    ``ctx`` is captured in the closure (NOT stored on state, which LangGraph
    serializes). If ctx is None at compile time, the wrapper reads it from
    ``state._runtime_ctx`` as a fallback (set per-invoke by callers that build
    graphs once and run many times).
    """

    async def _node_fn(state: NexusState) -> dict[str, Any]:
        runtime_ctx = ctx if ctx is not None else getattr(state, "_runtime_ctx", None)
        inputs = _collect_inputs(state, node)
        node_state = NodeState(
            node_id=node.id,
            node_type=node.type,
            status="running",
            started_at=datetime.now(UTC),
            inputs=inputs,
        )
        # attach node state
        new_node_states = {**state.node_states, node.id: node_state}
        try:
            if runtime_ctx is None:
                raise NodeExecutionError(
                    f"no runtime context attached to state for node {node.id!r}"
                )
            result = await executor.run(runtime_ctx, node, inputs)
            node_state.status = "succeeded"
            node_state.outputs = result.output
            node_state.ended_at = datetime.now(UTC)
            # accumulate artifacts/memory_ops/sources on state
            new_artifacts = [*state.artifacts, *result.artifacts]
            new_memory_ops = [*state.memory_ops, *result.memory_ops]
            update: dict[str, Any] = {
                "node_states": {**new_node_states, node.id: node_state},
                "artifacts": new_artifacts,
                "memory_ops": new_memory_ops,
            }
            if result.next_action.type == "abort":
                update["outputs"] = {**state.outputs, node.id: result.output}
            return update
        except HanflowError as exc:
            node_state.status = "failed"
            node_state.error = str(exc)
            node_state.ended_at = datetime.now(UTC)
            policy = node.on_error
            if policy.type == "skip":
                node_state.status = "skipped"
                return {"node_states": {**new_node_states, node.id: node_state}}
            # abort (default) — surface the error
            return {
                "node_states": {**new_node_states, node.id: node_state},
                "outputs": {**state.outputs, "_error": str(exc)},
            }

    return _node_fn
