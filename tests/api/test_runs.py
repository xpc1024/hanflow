import time

from hanflow.api.routes import runs as runs_module

_DSL_YAML = """
name: w
nodes:
  - id: a
    type: LLM
    config:
      template: hi
"""


def _wait_done(run_id: str, timeout: float = 5.0) -> None:
    """Wait for the background _drive task to finish (status leaves 'running')."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        e = runs_module._runs.get(run_id)
        if e and e["status"] != "running":
            return
        time.sleep(0.05)


def test_post_run(client):
    r = client.post("/api/runs", json={"yaml": _DSL_YAML, "inputs": {}})
    assert r.status_code == 200
    body = r.json()
    assert "run_id" in body
    assert body["status"] == "running"


def test_get_run(client):
    run_id = client.post("/api/runs", json={"yaml": _DSL_YAML}).json()["run_id"]
    _wait_done(run_id)
    r = client.get(f"/api/runs/{run_id}")
    assert r.status_code == 200
    assert r.json()["run_id"] == run_id
    assert r.json()["status"] == "succeeded"


def test_list_runs(client):
    client.post("/api/runs", json={"yaml": _DSL_YAML})
    r = client.get("/api/runs")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    assert len(r.json()) >= 1


def test_cancel_run(client):
    run_id = client.post("/api/runs", json={"yaml": _DSL_YAML}).json()["run_id"]
    r = client.delete(f"/api/runs/{run_id}")
    assert r.status_code == 200


def test_get_run_404(client):
    r = client.get("/api/runs/nonexistent")
    assert r.status_code == 404
