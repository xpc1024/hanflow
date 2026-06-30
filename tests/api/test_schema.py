def test_dsl_schema(client):
    r = client.get("/api/schema/dsl")
    assert r.status_code == 200
    schema = r.json()
    assert schema["title"] == "WorkflowDSL"
    assert "nodes" in schema["properties"]


def test_node_schema_for_each_primitive(client):
    from typing import get_args

    from hanflow.core.dsl import NodeType

    for nt in get_args(NodeType):
        r = client.get(f"/api/schema/node/{nt}")
        assert r.status_code == 200, f"{nt}: {r.status_code}"
        body = r.json()
        assert body["node_type"] == nt
        assert "config_schema" in body


def test_node_schema_unknown_type_404(client):
    r = client.get("/api/schema/node/NotARealType")
    assert r.status_code == 404


def test_node_schema_has_visual_hints(client):
    r = client.get("/api/schema/node/LLM")
    body = r.json()
    assert body["visual"]["color"] == "#3b82f6"  # LLM = blue
    assert body["default_config"] == {"template": ""}
