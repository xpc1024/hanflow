import asyncio

import pytest

from hanflow.observability.trace import (
    NullTraceExporter,
    Span,
    TraceExporter,
    _BufferedTraceExporter,
)


@pytest.mark.asyncio
async def test_span_lifecycle_sets_end_time():
    exp = NullTraceExporter()
    async with exp.span("workflow.run") as sp:
        assert sp.end_time is None
        assert sp.name == "workflow.run"
    assert sp.end_time is not None
    assert sp.status == "ok"


@pytest.mark.asyncio
async def test_nested_span_inherits_parent():
    exp = NullTraceExporter()
    async with exp.span("parent") as parent:
        async with exp.span("child") as child:
            assert child.parent_span_id == parent.span_id
            assert child.trace_id == parent.trace_id


@pytest.mark.asyncio
async def test_attributes_and_events():
    exp = NullTraceExporter()
    async with exp.span("llm.call", model="gpt-4o") as sp:
        await exp.event("token", count=5)
    assert sp.attributes["model"] == "gpt-4o"
    assert sp.events  # has the token event


@pytest.mark.asyncio
async def test_error_status_recorded():
    exp = NullTraceExporter()
    with pytest.raises(ValueError):
        async with exp.span("bad") as sp:
            raise ValueError("boom")
    assert sp.status == "error"


@pytest.mark.asyncio
async def test_concurrent_spans_isolated_per_task():
    """contextvar propagation: two concurrent coroutines each get their own parent stack."""
    exp = NullTraceExporter()

    async def worker(tag: str):
        async with exp.span(f"parent-{tag}") as p:
            await asyncio.sleep(0)
            async with exp.span(f"child-{tag}") as c:
                return c.parent_span_id == p.span_id

    results = await asyncio.gather(worker("a"), worker("b"))
    assert results == [True, True]


@pytest.mark.asyncio
async def test_null_exporter_buffers_and_flush_noops():
    exp = NullTraceExporter()
    async with exp.span("s1"):
        pass
    # NullTraceExporter drops on export; flush must not raise.
    await exp.flush()


@pytest.mark.asyncio
async def test_capture_exporter_collects_spans_for_test():
    exp = _BufferedTraceExporter()
    async with exp.span("a"):
        async with exp.span("b"):
            pass
    await exp.flush()
    assert len(exp.exported) == 2
    names = {s.name for s in exp.exported}
    assert names == {"a", "b"}
    # b is child of a
    b = next(s for s in exp.exported if s.name == "b")
    a = next(s for s in exp.exported if s.name == "a")
    assert b.parent_span_id == a.span_id


@pytest.mark.asyncio
async def test_trace_id_consistent_across_tree():
    exp = NullTraceExporter()
    async with exp.span("root") as root:
        async with exp.span("leaf") as leaf:
            assert leaf.trace_id == root.trace_id


def test_span_model_defaults():
    s = Span(name="x", kind="node")
    assert s.status == "ok"
    assert s.events == []
    assert s.end_time is None


def test_traceexporter_is_base_for_null():
    assert issubclass(NullTraceExporter, TraceExporter)
