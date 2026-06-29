"""Orchestration tests: RuntimeContextImpl + Compiler + 13 executors + e2e."""

from __future__ import annotations

import pytest

from hanflow.core.dsl import WorkflowDSL
from hanflow.core.result import MemoryOp
from hanflow.orchestration.compiler import Compiler
from hanflow.orchestration.context_impl import RuntimeContextImpl
from hanflow.orchestration.registry import NodeExecutorRegistry


@pytest.mark.asyncio
async def test_ctx_complete_routes_through_router(ctx):
    resp = await ctx.complete([{"role": "user", "content": "hi"}])
    assert resp.provider == "cloud"


@pytest.mark.asyncio
async def test_ctx_tool_call_routes_through_bus(ctx):
    out = await ctx.tool_call("echo.say", {"msg": "hi"})
    assert out["msg"] == "hi"


@pytest.mark.asyncio
async def test_ctx_memory_write_read(ctx):
    await ctx.memory(MemoryOp(action="write", scope="scratch", key="k", value="v"))
    got = await ctx.memory(MemoryOp(action="read", scope="scratch", key="k"))
    assert got == "v"


@pytest.mark.asyncio
async def test_ctx_retrieve_returns_chunks(ctx):
    from hanflow.retrieval.indexing import Document

    sp = ctx._retrieval["docs"]
    await sp.upsert([Document(id="d1", content="hello world")], collection="docs")
    chunks = await ctx.retrieve("docs", "hello world", top_k=3)
    assert chunks


@pytest.mark.asyncio
async def test_ctx_spawn_agent_isolates(ctx):
    from hanflow.isolation.sandbox import AgentSpec

    child = await ctx.spawn_agent(AgentSpec(task="x", sub_agent="a", tools_whitelist=["echo.say"]))
    assert child is not ctx
    assert isinstance(child, RuntimeContextImpl)


@pytest.mark.asyncio
async def test_registry_default_has_13_types():
    reg = NodeExecutorRegistry.default()
    assert len(reg.all_types()) == 13


@pytest.mark.asyncio
async def test_compile_static_two_node_graph():
    dsl = WorkflowDSL(
        name="w",
        nodes=[
            {"id": "a", "type": "LLM", "config": {"template": "hi"}},  # type: ignore[call-arg]
            {"id": "b", "type": "LLM", "depends_on": ["a"], "config": {"template": "bye"}},  # type: ignore[call-arg]
        ],
    )
    compiler = Compiler(NodeExecutorRegistry.default())
    compiled = compiler.compile(dsl)
    assert compiled.entry_node == "a"
    assert "b" in compiled.exit_nodes


@pytest.mark.asyncio
async def test_static_graph_runs_with_attached_ctx(ctx):
    """A 2-node LLM graph runs end-to-end when the ctx is attached to state."""
    dsl = WorkflowDSL(
        name="w",
        nodes=[
            {"id": "a", "type": "LLM", "config": {"template": "hello"}},  # type: ignore[call-arg]
        ],
    )
    compiler = Compiler(NodeExecutorRegistry.default())
    compiled = compiler.compile(dsl, ctx=ctx)
    result = await compiled.graph.ainvoke(ctx.state)
    ns = result["node_states"]["a"]
    status = ns.status if hasattr(ns, "status") else ns["status"]
    assert status == "succeeded"
    outputs = ns.outputs if hasattr(ns, "outputs") else ns["outputs"]
    assert "content" in outputs


@pytest.mark.asyncio
async def test_tool_node_runs(ctx):
    dsl = WorkflowDSL(
        name="w",
        nodes=[
            {"id": "t", "type": "Tool", "config": {"tool": "echo.say", "args": {"msg": "ping"}}},  # type: ignore[call-arg]
        ],
    )
    compiler = Compiler(NodeExecutorRegistry.default())
    compiled = compiler.compile(dsl, ctx=ctx)
    result = await compiled.graph.ainvoke(ctx.state)
    ns = result["node_states"]["t"]
    outputs = ns.outputs if hasattr(ns, "outputs") else ns["outputs"]
    assert outputs["result"] == {"msg": "ping"}


@pytest.mark.asyncio
async def test_memory_node_runs(ctx):
    dsl = WorkflowDSL(
        name="w",
        nodes=[
            {"id": "m", "type": "Memory", "config": {"action": "write", "key": "k", "value": "v"}},  # type: ignore[call-arg]
        ],
    )
    compiler = Compiler(NodeExecutorRegistry.default())
    compiled = compiler.compile(dsl, ctx=ctx)
    result = await compiled.graph.ainvoke(ctx.state)
    ns = result["node_states"]["m"]
    status = ns.status if hasattr(ns, "status") else ns["status"]
    assert status == "succeeded"


@pytest.mark.asyncio
async def test_knowledge_node_runs(ctx):
    from hanflow.retrieval.indexing import Document

    await ctx._retrieval["docs"].upsert(
        [Document(id="d1", content="unified search test")], collection="docs"
    )
    dsl = WorkflowDSL(
        name="w",
        nodes=[
            {
                "id": "k",
                "type": "Knowledge",
                "config": {"store": "docs", "query": "unified search"},
            },  # type: ignore[call-arg]
        ],
    )
    compiler = Compiler(NodeExecutorRegistry.default())
    compiled = compiler.compile(dsl, ctx=ctx)
    result = await compiled.graph.ainvoke(ctx.state)
    ns = result["node_states"]["k"]
    outputs = ns.outputs if hasattr(ns, "outputs") else ns["outputs"]
    assert outputs["count"] >= 1


@pytest.mark.asyncio
async def test_coordinator_node_runs(ctx):
    dsl = WorkflowDSL(
        name="w",
        nodes=[
            {
                "id": "c",
                "type": "Coordinator",
                "config": {
                    "sub_agents": ["researcher"],
                    "max_iterations": 1,
                    "replan": False,
                    "success_criteria": "summarize",
                },
            },  # type: ignore[call-arg]
        ],
    )
    compiler = Compiler(NodeExecutorRegistry.default())
    compiled = compiler.compile(dsl, ctx=ctx)
    ctx.state.inputs = {"task": "write a haiku"}
    result = await compiled.graph.ainvoke(ctx.state)
    ns = result["node_states"]["c"]
    status = ns.status if hasattr(ns, "status") else ns["status"]
    assert status == "succeeded"
