from datetime import datetime

import pytest

from hanflow.core.context import FakeContext
from hanflow.core.result import HITLPayload, MemoryOp
from hanflow.core.state import NexusState, RunMeta


def _ctx() -> FakeContext:
    state = NexusState(
        meta=RunMeta(
            run_id="r1",
            workflow_name="w",
            workflow_version="0.1.0",
            started_at=datetime.now(),
            mode="static",
            trigger="cli",
        ),
        inputs={},
        outputs={},
        node_states={},
        artifacts=[],
        memory_ops=[],
        variables={},
    )
    return FakeContext(state=state)


def test_fake_context_records_hitl():
    ctx = _ctx()
    p = HITLPayload(
        node_id="h",
        title="t",
        description="d",
        form={},
        current_value=None,
        actions=["approve"],
        paused_at=datetime.now(),
    )
    ctx.emit_hitl(p)
    assert ctx.emitted_hitl is p


@pytest.mark.asyncio
async def test_fake_context_tool_call_stub():
    ctx = _ctx()
    out = await ctx.tool_call("my.tool", {"x": 1})
    assert out == {"name": "my.tool", "args": {"x": 1}}


@pytest.mark.asyncio
async def test_fake_context_memory_records_ops():
    ctx = _ctx()
    op = MemoryOp(action="write", scope="scratch", key="k", value=1)
    await ctx.memory(op)
    assert op in ctx.memory_ops


@pytest.mark.asyncio
async def test_fake_context_span_is_async_cm():
    ctx = _ctx()
    async with ctx.span("test.span", attr="v") as sp:
        assert sp.name == "test.span"
        assert sp.attributes == {"attr": "v"}


@pytest.mark.asyncio
async def test_fake_context_retrieve_default_empty():
    ctx = _ctx()
    chunks = await ctx.retrieve("store", "q")
    assert chunks == []


@pytest.mark.asyncio
async def test_fake_context_spawn_agent_returns_child():
    ctx = _ctx()
    child = await ctx.spawn_agent({"task": "do thing"})
    assert isinstance(child, FakeContext)
    assert child is not ctx
