from hanflow.api.routes import runs as runs_module
from hanflow.core.result import HITLPayload


def _make_paused_entry(run_id: str = "r-hitl") -> None:
    """Inject a paused run into _runs with a fake resume hook for endpoint tests."""
    from datetime import UTC, datetime

    resumed: list = []

    async def _resume(cmd):
        resumed.append(cmd)

    class FakeHandle:
        def __init__(self):
            self.run_id = run_id
            self._resume = _resume
            self._pending_payload = HITLPayload(
                node_id="gate",
                title="approve?",
                description="",
                form={},
                current_value=None,
                actions=["approve"],
                paused_at=datetime.now(UTC),
            )

    runs_module._runs[run_id] = {
        "run_id": run_id,
        "status": "paused",
        "result": None,
        "handle": FakeHandle(),
    }


def test_pending_lists_paused_run(client):
    runs_module._runs.clear()
    _make_paused_entry("r1")
    r = client.get("/api/hitl/pending")
    assert r.status_code == 200
    ids = {p["run_id"] for p in r.json()}
    assert "r1" in ids
    assert r.json()[0]["payload"]["node_id"] == "gate"


def test_approve_resumes_paused_run(client):
    runs_module._runs.clear()
    _make_paused_entry("r2")
    r = client.post("/api/runs/r2/approve", json={"decided_by": "tester"})
    assert r.status_code == 200
    assert r.json()["status"] == "resumed"
    assert runs_module._runs["r2"]["status"] == "running"


def test_edit_requires_edited_value(client):
    runs_module._runs.clear()
    _make_paused_entry("r3")
    r = client.post("/api/runs/r3/edit", json={"decided_by": "tester"})
    assert r.status_code == 422


def test_reject_requires_reason(client):
    runs_module._runs.clear()
    _make_paused_entry("r4")
    r = client.post("/api/runs/r4/reject", json={"decided_by": "tester"})
    assert r.status_code == 422


def test_reroute_requires_target(client):
    runs_module._runs.clear()
    _make_paused_entry("r5")
    r = client.post("/api/runs/r5/reroute", json={"decided_by": "tester"})
    assert r.status_code == 422


def test_approve_404_unknown_run(client):
    runs_module._runs.clear()
    r = client.post("/api/runs/ghost/approve", json={"decided_by": "tester"})
    assert r.status_code == 404


def test_approve_409_not_paused(client):
    runs_module._runs.clear()
    runs_module._runs["r6"] = {
        "run_id": "r6",
        "status": "succeeded",
        "result": None,
        "handle": None,
    }
    r = client.post("/api/runs/r6/approve", json={"decided_by": "tester"})
    assert r.status_code == 409
