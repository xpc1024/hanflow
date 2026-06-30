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
    deadline = time.time() + timeout
    while time.time() < deadline:
        e = runs_module._runs.get(run_id)
        if e and e["status"] != "running":
            return
        time.sleep(0.05)


def test_trace_endpoint(client):
    runs_module._runs.clear()
    run_id = client.post("/api/runs", json={"yaml": _DSL_YAML}).json()["run_id"]
    _wait_done(run_id)
    r = client.get(f"/api/runs/{run_id}/trace")
    assert r.status_code == 200
    assert r.json()["run_id"] == run_id


def test_artifacts_endpoint(client):
    runs_module._runs.clear()
    run_id = client.post("/api/runs", json={"yaml": _DSL_YAML}).json()["run_id"]
    _wait_done(run_id)
    r = client.get(f"/api/runs/{run_id}/artifacts")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_download_endpoint(client):
    r = client.get("/api/artifacts/r1/a1/download")
    assert r.status_code == 200
    assert r.json()["artifact_id"] == "a1"


def test_trace_404(client):
    r = client.get("/api/runs/ghost/trace")
    assert r.status_code == 404
