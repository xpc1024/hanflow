"""Tests for Phase 14 workflows API: create 409, list meta, validate structured, dry-run SSE."""
from __future__ import annotations


def test_create_returns_409_on_duplicate(client):
    yaml = "name: dup\nnodes:\n  - id: a\n    type: LLM\n    config:\n      template: hi\n"
    r1 = client.post("/api/workflows", json={"id": "dup", "yaml": yaml})
    assert r1.status_code == 200
    r2 = client.post("/api/workflows", json={"id": "dup", "yaml": yaml})
    assert r2.status_code == 409


def test_list_returns_workflow_meta(client):
    yaml = (
        "name: My Flow\ndescription: test\nnodes:\n"
        "  - id: a\n    type: LLM\n  - id: b\n    type: Tool\n    depends_on: [a]\n"
        "metadata:\n  tags: [prod]\n"
    )
    client.post("/api/workflows", json={"id": "mf", "yaml": yaml})
    r = client.get("/api/workflows")
    items = r.json()
    assert len(items) >= 1
    item = next(i for i in items if i["id"] == "mf")
    assert item["name"] == "My Flow"
    assert item["nodeCount"] == 2
    assert "prod" in item.get("tags", [])
    assert "updatedAt" in item


def test_validate_returns_structured_errors(client):
    yaml = (
        "name: bad\nnodes:\n  - id: a\n    type: LLM\n    depends_on: [b]\n"
        "  - id: b\n    type: LLM\n    depends_on: [a]\n"
    )
    r = client.post("/api/workflows/validate", json={"yaml": yaml})
    body = r.json()
    assert body["valid"] is False
    assert isinstance(body.get("errors"), list)
    assert len(body["errors"]) > 0
    assert "error" in body


def test_dry_run_returns_sse_stream(client):
    yaml = "name: dr\nnodes:\n  - id: a\n    type: LLM\n    config:\n      template: hello\n"
    with client.stream("POST", "/api/workflows/dr/dry-run", json={"yaml": yaml, "inputs": {}}) as resp:
        assert resp.status_code == 200
        lines = []
        for line in resp.iter_lines():
            lines.append(line)
        assert any("data:" in l for l in lines)
