_DSL = """
name: w1
nodes:
  - id: a
    type: LLM
    config:
      template: hi
"""


def test_create_and_get_workflow(client):
    r = client.post("/api/workflows", json={"id": "w1", "yaml": _DSL})
    assert r.status_code == 200
    r = client.get("/api/workflows/w1")
    assert r.status_code == 200
    assert r.json()["id"] == "w1"
    assert "name: w1" in r.json()["yaml"]


def test_list_workflows(client):
    client.post("/api/workflows", json={"id": "w1", "yaml": _DSL})
    client.post("/api/workflows", json={"id": "w2", "yaml": _DSL.replace("w1", "w2")})
    r = client.get("/api/workflows")
    assert r.status_code == 200
    ids = {w["id"] for w in r.json()}
    assert {"w1", "w2"} <= ids


def test_update_workflow(client):
    client.post("/api/workflows", json={"id": "w1", "yaml": _DSL})
    r = client.put("/api/workflows/w1", json={"id": "w1", "yaml": _DSL.replace("hi", "bye")})
    assert r.status_code == 200
    got = client.get("/api/workflows/w1").json()
    assert "bye" in got["yaml"]


def test_delete_workflow(client):
    client.post("/api/workflows", json={"id": "w1", "yaml": _DSL})
    r = client.delete("/api/workflows/w1")
    assert r.status_code == 200
    assert client.get("/api/workflows/w1").status_code == 404


def test_validate_endpoint_ok(client):
    r = client.post("/api/workflows/validate", json={"yaml": _DSL})
    assert r.status_code == 200
    assert r.json()["valid"] is True


def test_validate_endpoint_invalid(client):
    bad = """
name: w
nodes:
  - id: a
    type: LLM
  - id: a
    type: LLM
"""
    r = client.post("/api/workflows/validate", json={"yaml": bad})
    assert r.status_code == 200
    assert r.json()["valid"] is False
    assert "error" in r.json()
