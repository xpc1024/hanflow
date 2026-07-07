"""Tests for Phase 16 HITL API: reason/form fields, history endpoint, 409 guard."""
from __future__ import annotations


def test_hitl_record_has_reason_and_form():
    from hanflow.core.result import HITLRecord

    r = HITLRecord(
        action="reject",
        decided_by="alice",
        decided_at="2026-07-01T00:00:00",
        duration_seconds=10.0,
        reason="quality issues",
    )
    assert r.reason == "quality issues"

    r2 = HITLRecord(
        action="approve",
        decided_by="bob",
        decided_at="2026-07-01T00:00:00",
        duration_seconds=5.0,
        form={"decision": "ship"},
    )
    assert r2.form == {"decision": "ship"}


def test_history_endpoint(client):
    r = client.get("/api/hitl/history?limit=10")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_decision_body_has_form_and_reason():
    body = {"decided_by": "test", "reason": "bad", "form": {"decision": "reject"}}
    from hanflow.api.routes.hitl import DecisionBody

    parsed = DecisionBody(**body)
    assert parsed.reason == "bad"
    assert parsed.form == {"decision": "reject"}


def test_resume_404_unknown_run(client):
    r = client.post("/api/runs/nonexistent/approve", json={"decided_by": "a"})
    assert r.status_code == 404
