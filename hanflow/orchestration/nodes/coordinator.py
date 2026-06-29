"""Coordinator executor — dynamic bridge (§3.5).

State machine: PLAN → PLAN_HITL? → COMPILE → DISPATCH → AGGREGATE → CHECK.

Phase 8 ships a working Planner/Dispatcher/Aggregator driven by ctx.complete
and ctx.spawn_agent. The Planner produces a WorkflowDSL JSON which is compiled
into a subgraph; sub-agents run in isolated contexts; the Aggregator decides
whether to replan. ``max_iterations`` default 5, cap 20.
"""

from __future__ import annotations

import json
from typing import Any, cast

from hanflow.core.dsl import NodeConfig, WorkflowNode
from hanflow.core.errors import HanflowError, MaxIterationsExceeded
from hanflow.core.result import AtomResult, NextAction
from hanflow.isolation.sandbox import AgentSpec


def _cfg(node: WorkflowNode) -> dict[str, Any]:
    return node.config.__pydantic_extra__ or {}


class CoordinatorExecutor:
    node_type = "Coordinator"

    def validate_config(self, config: NodeConfig) -> None:
        cfg = config.__pydantic_extra__ or {}
        max_iter = cfg.get("max_iterations", 5)
        if not isinstance(max_iter, int) or max_iter <= 0:
            raise HanflowError("Coordinator.max_iterations must be a positive int")
        if max_iter > 20:
            raise HanflowError("Coordinator.max_iterations exceeds hard cap of 20")

    async def run(self, ctx: Any, node: WorkflowNode, inputs: dict[str, Any]) -> AtomResult:
        cfg = _cfg(node)
        task = inputs.get("task") or cfg.get("success_criteria") or node.id
        sub_agents: list[str] = cfg.get("sub_agents", [])
        max_iter = cfg.get("max_iterations", 5)
        replan = cfg.get("replan", True)
        plan_hitl = cfg.get("plan_hitl", False)
        success_criteria = cfg.get("success_criteria", task)

        feedback = ""
        last_output: Any = None
        for iteration in range(max_iter):
            # 1. PLAN
            sub_dsl = await self._plan(ctx, task, sub_agents, feedback)
            # 2. PLAN_HITL?
            if plan_hitl:
                # The engine would pause here via emit_hitl; for the synchronous
                # run we proceed (HITL wiring is exercised in resume tests).
                pass
            # 3 + 4. COMPILE + DISPATCH
            results = await self._dispatch(ctx, sub_dsl, sub_agents)
            # 5. AGGREGATE
            achieved, last_output, feedback = await self._aggregate(
                ctx, task, results, success_criteria
            )
            if achieved:
                return AtomResult(
                    output={"achieved": True, "result": last_output, "iterations": iteration + 1},
                    next_action=NextAction(type="continue"),
                )
            if not replan:
                break
        return AtomResult(
            output={"achieved": False, "result": last_output, "iterations": max_iter},
            error=MaxIterationsExceeded(
                f"Coordinator exceeded max_iterations={max_iter} without achieving goal"
            ),
            next_action=NextAction(type="continue"),
        )

    async def _plan(
        self, ctx: Any, task: str, sub_agents: list[str], feedback: str
    ) -> dict[str, Any]:
        prompt = (
            "Break the following task into a workflow. Respond with ONLY a JSON "
            'object: {"nodes": [{"id":..., "type":"LLM", "config":{"template":...}}]}. '
            f"Task: {task}. Sub-agents available: {sub_agents}. "
            f"Previous failure feedback: {feedback or 'none'}."
        )
        resp = await ctx.complete([{"role": "user", "content": prompt}], role="planner")
        try:
            data = json.loads(resp.content)
        except json.JSONDecodeError:
            # Fallback: single LLM node that just does the task.
            data = {"nodes": [{"id": "step", "type": "LLM", "config": {"template": task}}]}
        return cast(dict[str, Any], data)

    async def _dispatch(
        self, ctx: Any, sub_dsl: dict[str, Any], sub_agents: list[str]
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for i, node in enumerate(sub_dsl.get("nodes", [])):
            agent_name = sub_agents[i] if i < len(sub_agents) else f"agent-{i}"
            child = await ctx.spawn_agent(
                AgentSpec(task=node.get("config", {}).get("template", ""), sub_agent=agent_name)
            )
            # Single handoff: child runs one LLM step.
            template = node.get("config", {}).get("template", "")
            resp = await child.complete([{"role": "user", "content": template}])
            results.append({"sub_agent": agent_name, "output": resp.content})
        return results

    async def _aggregate(
        self, ctx: Any, task: str, results: list[dict[str, Any]], success_criteria: str
    ) -> tuple[bool, Any, str]:
        joined = "\n".join(f"- {r['sub_agent']}: {r['output']}" for r in results)
        prompt = (
            f"Did the sub-results achieve the goal? Goal: {success_criteria}.\n"
            f"Results:\n{joined}\n"
            'Respond with JSON: {"achieved": true|false, "feedback": "..."}'
        )
        resp = await ctx.complete([{"role": "user", "content": prompt}], role="planner")
        try:
            data = json.loads(resp.content)
            achieved = bool(data.get("achieved"))
            feedback = str(data.get("feedback", ""))
        except json.JSONDecodeError:
            achieved = False
            feedback = resp.content
        return achieved, joined, feedback
