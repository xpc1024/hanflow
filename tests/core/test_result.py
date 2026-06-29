from datetime import datetime

from hanflow.core.result import (
    Artifact,
    AtomResult,
    Chunk,
    HITLPayload,
    HITLRecord,
    MemoryOp,
    NextAction,
    Source,
    TraceEvent,
)


def test_artifact_round_trip():
    a = Artifact(
        id="a1",
        kind="report",
        content="# Title",
        mime_type="text/markdown",
        source_node="report_node",
    )
    d = a.model_dump()
    a2 = Artifact.model_validate(d)
    assert a2 == a


def test_source_defaults():
    s = Source(source_id="s1", kind="web", url="https://x")
    assert s.credibility == 0.5
    assert s.extra == {}


def test_memory_op_write():
    m = MemoryOp(action="write", scope="scratch", key="k", value={"v": 1})
    assert m.ttl_seconds is None


def test_trace_event_kinds():
    e = TraceEvent(
        span_id="sp1",
        name="llm.call",
        kind="event",
        timestamp=datetime.now(),
    )
    assert e.parent_span_id is None
    assert e.attributes == {}


def test_hitl_payload_actions_required():
    p = HITLPayload(
        node_id="h1",
        title="approve?",
        description="d",
        form={},
        current_value=None,
        actions=["approve", "reject"],
        paused_at=datetime.now(),
    )
    assert "approve" in p.actions


def test_hitl_record():
    r = HITLRecord(
        action="edit",
        edited_value={"x": 1},
        decided_by="alice",
        decided_at=datetime.now(),
        duration_seconds=12.3,
    )
    assert r.reroute_target is None


def test_chunk_carries_source():
    s = Source(source_id="s", kind="private_kb")
    c = Chunk(text="hello", score=0.9, source=s)
    assert c.source.kind == "private_kb"
    assert c.metadata == {}


def test_next_action_defaults_to_continue():
    r = AtomResult(output={"k": "v"})
    assert r.next_action.type == "continue"
    assert r.artifacts == []
    assert r.error is None


def test_atom_result_full():
    s = Source(source_id="s", kind="computed")
    a = Artifact(
        id="a", kind="code", content="print(1)", mime_type="text/x-python", source_node="n"
    )
    r = AtomResult(
        output={"answer": 42},
        artifacts=[a],
        sources=[s],
        next_action=NextAction(type="branch", branch_label="yes"),
    )
    assert r.artifacts[0].kind == "code"
    assert r.next_action.branch_label == "yes"
