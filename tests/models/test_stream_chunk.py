"""StreamChunk model tests (§design StreamChunk)."""
import pytest
from hanflow.models.providers.base import StreamChunk, TokenUsage


def test_stream_chunk_minimal():
    """中间 chunk：只有 delta，usage/finish_reason 为 None。"""
    c = StreamChunk(delta="hello")
    assert c.delta == "hello"
    assert c.usage is None
    assert c.finish_reason is None


def test_stream_chunk_final():
    """末尾 chunk：带 usage + finish_reason。"""
    u = TokenUsage(input_tokens=10, output_tokens=20, total_tokens=30, cost_usd=0.01, latency_ms=100.0)
    c = StreamChunk(delta="", usage=u, finish_reason="stop")
    assert c.usage == u
    assert c.finish_reason == "stop"


def test_stream_chunk_empty_delta_allowed():
    """空 delta 合法（纯 usage chunk）。"""
    c = StreamChunk(delta="")
    assert c.delta == ""
