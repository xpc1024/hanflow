"""Leaf executors: LLM / Tool / Research / Execution (§3.4).

Thin wrappers: LLM/Tool call ctx directly; Research/Execution delegate to the
L3 atoms (Phase 9). Until the atoms exist they raise a clear 'not wired' error
so the rest of Phase 8 stays independently testable.
"""

from __future__ import annotations

from typing import Any, cast

from hanflow.core.dsl import NodeConfig, WorkflowNode
from hanflow.core.errors import HanflowError
from hanflow.core.expr import interpolate
from hanflow.core.result import AtomResult, NextAction


def _cfg(node: WorkflowNode) -> dict[str, Any]:
    return node.config.__pydantic_extra__ or {}


class LLMExecutor:
    node_type = "LLM"

    def validate_config(self, config: NodeConfig) -> None:
        cfg = config.__pydantic_extra__ or {}
        if not (cfg.get("template") or cfg.get("prompt")):
            raise HanflowError("LLM requires 'template' or 'prompt'")

    async def run(self, ctx: Any, node: WorkflowNode, inputs: dict[str, Any]) -> AtomResult:
        cfg = _cfg(node)
        template = cfg.get("template") or cfg.get("prompt", "")
        prompt = interpolate(template, inputs)
        messages = [{"role": "user", "content": prompt}]
        prefer = cfg.get("model")  # named-model string, e.g. "strong"
        role = cfg.get("role")
        resp = await ctx.complete(
            messages,
            role=role,
            prefer=prefer,
            sensitivity=node.sensitivity,
        )
        return AtomResult(
            output={"content": resp.content, "model": getattr(resp, "model_used", None)},
            next_action=NextAction(type="continue"),
        )


class ToolExecutor:
    node_type = "Tool"

    def validate_config(self, config: NodeConfig) -> None:
        cfg = config.__pydantic_extra__ or {}
        if not cfg.get("tool"):
            raise HanflowError("Tool requires 'tool' (server.tool name)")

    async def run(self, ctx: Any, node: WorkflowNode, inputs: dict[str, Any]) -> AtomResult:
        cfg = _cfg(node)
        tool_name: str = cfg["tool"]
        raw_args = cfg.get("args", {})
        args = {k: interpolate(v, inputs) if isinstance(v, str) else v for k, v in raw_args.items()}
        out = await ctx.tool_call(tool_name, args)
        return AtomResult(output={"result": out}, next_action=NextAction(type="continue"))


class ResearchExecutor:
    node_type = "Research"

    def validate_config(self, config: NodeConfig) -> None:
        cfg = config.__pydantic_extra__ or {}
        if not cfg.get("query"):
            raise HanflowError("Research requires 'query'")

    async def run(self, ctx: Any, node: WorkflowNode, inputs: dict[str, Any]) -> AtomResult:
        cfg = _cfg(node)
        query = interpolate(cfg["query"], inputs)
        try:
            from hanflow.atoms.research import (  # type: ignore[import-untyped]
                ResearchAtom,
                ResearchOptions,
            )
        except ImportError as exc:  # pragma: no cover - Phase 9 wires this
            raise HanflowError("Research atom not yet wired (Phase 9)") from exc
        atom = ResearchAtom()
        result = await atom.run(
            ctx,
            inputs,
            ResearchOptions(
                query=query,
                depth=cfg.get("depth", "standard"),
                max_sources=cfg.get("max_sources", 10),
                private_kb=cfg.get("private_kb"),
                citation=cfg.get("citation", True),
            ),
        )
        return cast(AtomResult, result)


class ExecutionExecutor:
    node_type = "Execution"

    def validate_config(self, config: NodeConfig) -> None:
        cfg = config.__pydantic_extra__ or {}
        if not cfg.get("task"):
            raise HanflowError("Execution requires 'task'")

    async def run(self, ctx: Any, node: WorkflowNode, inputs: dict[str, Any]) -> AtomResult:
        cfg = _cfg(node)
        task = interpolate(cfg["task"], inputs)
        try:
            from hanflow.atoms.execution import (  # type: ignore[import-untyped]
                ExecutionAtom,
                ExecutionOptions,
            )
        except ImportError as exc:  # pragma: no cover - Phase 9 wires this
            raise HanflowError("Execution atom not yet wired (Phase 9)") from exc
        atom = ExecutionAtom()
        result = await atom.run(
            ctx,
            inputs,
            ExecutionOptions(
                task=task,
                sandbox=cfg.get("sandbox", "docker"),
                max_steps=cfg.get("max_steps", 20),
                allow_delegate=cfg.get("allow_delegate", True),
                skills=cfg.get("skills"),
                tools_whitelist=cfg.get("tools_whitelist"),
            ),
        )
        return cast(AtomResult, result)
