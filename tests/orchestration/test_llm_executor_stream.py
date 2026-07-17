"""LLMExecutor streaming branch tests (§design §5)."""

import pytest

from hanflow.core.dsl import NodeConfig, WorkflowNode
from hanflow.models.providers.base import ModelResponse, StreamChunk, TokenUsage
from hanflow.orchestration.nodes.leaf import LLMExecutor


class _StreamCtx:
    """Fake ctx: records emit_run_event calls, stream returns fixed chunks."""

    def __init__(self, chunks):
        self._chunks = chunks
        self.events = []

    async def stream(self, messages, **kwargs):
        for c in self._chunks:
            yield c

    async def emit_run_event(self, event):
        self.events.append(event)


class _CompleteCtx:
    """Fake ctx for non-stream regression: returns ModelResponse."""

    async def complete(self, messages, **kwargs):
        return ModelResponse(
            content="full",
            usage=TokenUsage(
                input_tokens=1, output_tokens=1, total_tokens=2, cost_usd=0.0, latency_ms=1.0
            ),
            model_used="m",
            provider="p",
        )


def _make_node(stream=False):
    """Build a WorkflowNode with prompt/model (+stream) in NodeConfig extra."""
    extras = {"prompt": "hi", "model": "strong"}
    if stream:
        extras["stream"] = True
    return WorkflowNode(
        id="n1",
        type="LLM",
        sensitivity="public",
        config=NodeConfig(**extras),
    )


@pytest.mark.asyncio
async def test_llm_stream_branch_emits_tokens_and_aggregates():
    chunks = [
        StreamChunk(delta="hel", model_used="gpt-4o"),
        StreamChunk(
            delta="lo",
            usage=TokenUsage(
                input_tokens=1, output_tokens=1, total_tokens=2, cost_usd=0.0, latency_ms=1.0
            ),
            finish_reason="stop",
        ),
    ]
    ctx = _StreamCtx(chunks)
    node = _make_node(stream=True)
    result = await LLMExecutor().run(ctx, node, {})
    assert result.output["content"] == "hello"
    assert result.output["model"] == "gpt-4o"
    assert len(ctx.events) == 2
    assert all(e.kind == "llm_token" for e in ctx.events)
    assert ctx.events[0].data["delta"] == "hel"


@pytest.mark.asyncio
async def test_llm_non_stream_branch_unchanged():
    """No stream config -> original complete branch."""
    ctx = _CompleteCtx()
    node = _make_node(stream=False)
    result = await LLMExecutor().run(ctx, node, {})
    assert result.output["content"] == "full"
