"""RuntimeContext.stream + emit_run_event tests (§design §4/§5a).

``ctx.stream`` delegates to ``ModelRouter.stream`` (resolving the named-model
``prefer`` string to a (provider, model) tuple exactly like ``complete`` does).
``ctx.emit_run_event`` pushes a ``RunEvent`` onto the optional ``RunHandle``
queue, so the host can stream ``llm_token`` events back to the SDK caller; when
no queue is attached (sub-agent / isolated test) the event is silently dropped.
"""

import asyncio

import pytest

from hanflow.models.providers.base import StreamChunk, TokenUsage
from hanflow.sdk import RunEvent


class _FakeRouter:
    """Fake router exposing only ``stream`` (mirrors ModelRouter.stream)."""

    async def stream(self, messages, *, prefer=None, **kwargs):
        yield StreamChunk(delta="a")
        yield StreamChunk(
            delta="b",
            usage=TokenUsage(
                input_tokens=1, output_tokens=1, total_tokens=2, cost_usd=0.0, latency_ms=1.0
            ),
            finish_reason="stop",
        )


def _make_ctx(run_handle_queue=None):
    """Build a RuntimeContextImpl with minimal stubs.

    Only ``stream``/``emit_run_event`` are exercised, so bus/memory/skills/
    retrieval/workspace/sandbox can be None — they are never called here.
    ``make_state`` (shared from tests/conftest.py) provides a fully-populated
    ``NexusState`` (the real model has many required fields).
    """
    from hanflow.observability.trace import NullTraceExporter
    from hanflow.orchestration.context_impl import RuntimeContextImpl
    from tests.conftest import make_state

    return RuntimeContextImpl(
        state=make_state(),
        router=_FakeRouter(),
        bus=None,
        memory=None,
        skills=None,
        retrieval={},
        trace=NullTraceExporter(),
        workspace_mgr=None,
        sandbox=None,
        named_models={"strong": ("primary", "gpt-4o")},
        run_handle_queue=run_handle_queue,
    )


@pytest.mark.asyncio
async def test_ctx_stream_delegates_to_router():
    ctx = _make_ctx()
    out = [c async for c in ctx.stream([{"role": "user", "content": "hi"}], prefer="strong")]
    assert [c.delta for c in out] == ["a", "b"]


@pytest.mark.asyncio
async def test_emit_run_event_pushes_to_queue():
    q: asyncio.Queue = asyncio.Queue()
    ctx = _make_ctx(run_handle_queue=q)
    await ctx.emit_run_event(RunEvent(kind="llm_token", node_id="n1", data={"delta": "x"}))
    ev = q.get_nowait()
    assert ev.kind == "llm_token"
    assert ev.data == {"delta": "x"}


@pytest.mark.asyncio
async def test_emit_run_event_silent_when_no_queue():
    ctx = _make_ctx(run_handle_queue=None)
    # Must not raise when no RunHandle queue is attached.
    await ctx.emit_run_event(RunEvent(kind="llm_token", node_id="n1", data={}))
