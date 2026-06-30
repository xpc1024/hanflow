"""Control-flow executors: Sequential / Parallel / Loop / Branch / HITL (§3.3).

Control-flow wiring happens at compile time (the Compiler builds the graph);
the executors' ``run()`` is mostly light (returning an empty AtomResult) since
the graph edges already express the flow. HITL is the exception: it emits a
payload + raises interrupt at runtime.
"""

from __future__ import annotations

from typing import Any

from hanflow.core.dsl import NodeConfig, WorkflowNode
from hanflow.core.errors import HanflowError
from hanflow.core.result import AtomResult, NextAction


class SequentialExecutor:
    node_type = "Sequential"

    def validate_config(self, config: NodeConfig) -> None:
        children = config.__pydantic_extra__ or {}
        if not children.get("children"):
            # Sequential is structural; children are wired via depends_on at
            # compile time. Allow empty config (pure wiring node).
            return

    async def run(self, ctx: Any, node: WorkflowNode, inputs: dict[str, Any]) -> AtomResult:
        return AtomResult(output={})  # pure compile-time wiring


class ParallelExecutor:
    node_type = "Parallel"

    def validate_config(self, config: NodeConfig) -> None:
        cfg = config.__pydantic_extra__ or {}
        join = cfg.get("join", "all")
        if join not in ("all", "any", "first_n"):
            raise HanflowError(f"Parallel.join must be all|any|first_n, got {join!r}")

    async def run(self, ctx: Any, node: WorkflowNode, inputs: dict[str, Any]) -> AtomResult:
        return AtomResult(output={"children_results": []})


class LoopExecutor:
    node_type = "Loop"

    def validate_config(self, config: NodeConfig) -> None:
        cfg = config.__pydantic_extra__ or {}
        max_iter = cfg.get("max_iterations", 100)
        if not isinstance(max_iter, int) or max_iter <= 0:
            raise HanflowError("Loop.max_iterations must be a positive int")
        if max_iter > 1000:
            raise HanflowError("Loop.max_iterations exceeds hard cap of 1000")

    async def run(self, ctx: Any, node: WorkflowNode, inputs: dict[str, Any]) -> AtomResult:
        return AtomResult(output={})


class BranchExecutor:
    node_type = "Branch"

    def validate_config(self, config: NodeConfig) -> None:
        cfg = config.__pydantic_extra__ or {}
        if not cfg.get("cases"):
            # cases optional when node.condition is set; allow.
            return

    async def run(self, ctx: Any, node: WorkflowNode, inputs: dict[str, Any]) -> AtomResult:
        return AtomResult(output={})


class HITLExecutor:
    node_type = "HITL"

    def validate_config(self, config: NodeConfig) -> None:
        cfg = config.__pydantic_extra__ or {}
        actions = cfg.get("actions")
        if actions is not None and not actions:
            raise HanflowError("HITL.actions must be non-empty if provided")

    async def run(self, ctx: Any, node: WorkflowNode, inputs: dict[str, Any]) -> AtomResult:
        """Emit a HITL payload then ``interrupt()`` to pause the graph.

        LangGraph's ``interrupt(payload)`` suspends the graph (checkpoint
        persists). On resume, ``ainvoke(Command(resume=x), ...)`` injects ``x``
        as the return value here. We normalise the resume value to
        ``{"hitl": HITLRecord_dict}`` and translate ``record.action`` into the
        NextAction (approve/edit continue; reject → reject_branch or abort;
        reroute → branch target).
        """
        from datetime import UTC, datetime

        from langgraph.types import interrupt

        from hanflow.core.result import HITLPayload

        cfg = node.config.__pydantic_extra__ or {}
        payload = HITLPayload(
            node_id=node.id,
            title=cfg.get("title", node.id),
            description=cfg.get("description", ""),
            form=cfg.get("form", {}),
            current_value=inputs,
            actions=cfg.get("actions", ["approve", "edit", "reject", "reroute"]),
            paused_at=datetime.now(UTC),
            timeout_seconds=cfg.get("timeout_seconds"),
        )
        ctx.emit_hitl(payload)
        # interrupt() suspends; resume value is {"hitl": {...HITLRecord...}}.
        resume_value = interrupt(payload.model_dump(mode="json"))
        record_raw = (resume_value or {}).get("hitl", {}) if isinstance(resume_value, dict) else {}
        action = record_raw.get("action", "approve")

        if action == "approve":
            return AtomResult(output={"action": "approve"}, next_action=NextAction(type="continue"))
        if action == "edit":
            return AtomResult(
                output={"action": "edit", "value": record_raw.get("edited_value")},
                next_action=NextAction(type="continue"),
            )
        if action == "reject":
            reject_branch = cfg.get("reject_branch")
            if reject_branch:
                return AtomResult(
                    output={"action": "reject"},
                    next_action=NextAction(type="branch", branch_label=reject_branch),
                )
            return AtomResult(output={"action": "reject"}, next_action=NextAction(type="abort"))
        if action == "reroute":
            return AtomResult(
                output={"action": "reroute"},
                next_action=NextAction(
                    type="branch", branch_label=record_raw.get("reroute_target", "")
                ),
            )
        return AtomResult(output={"action": action}, next_action=NextAction(type="continue"))
