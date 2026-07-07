"""Tests for Phase 13 schema endpoint: standard JSON Schema + validation_rules + output_schema."""
from __future__ import annotations


def test_dsl_schema(client):
    r = client.get("/api/schema/dsl")
    assert r.status_code == 200
    schema = r.json()
    assert schema["title"] == "WorkflowDSL"
    assert "nodes" in schema["properties"]


def test_node_schema_returns_standard_json_schema_for_all_types(client):
    from typing import get_args
    from hanflow.core.dsl import NodeType

    for nt in get_args(NodeType):
        r = client.get(f"/api/schema/node/{nt}")
        assert r.status_code == 200
        body = r.json()
        assert body["node_type"] == nt
        cs = body["config_schema"]
        assert cs["type"] == "object"
        assert "properties" in cs
        assert "validation_rules" in body
        assert "output_schema" in body
        assert "default_config" in body


def test_llm_config_schema_has_template_prompt(client):
    r = client.get("/api/schema/node/LLM")
    cs = r.json()["config_schema"]
    assert "template" in cs["properties"]
    assert "prompt" in cs["properties"]
    assert r.json()["validation_rules"]["alternatives"] == [["template", "prompt"]]


def test_tool_required(client):
    r = client.get("/api/schema/node/Tool")
    assert "tool" in r.json()["validation_rules"]["required"]


def test_hitl_actions_non_empty_if_set(client):
    r = client.get("/api/schema/node/HITL")
    vr = r.json()["validation_rules"]
    assert "non_empty_if_set" in vr
    assert "actions" in vr["non_empty_if_set"]


def test_memory_output_has_value(client):
    r = client.get("/api/schema/node/Memory")
    assert "value" in r.json()["output_schema"]["fields"]


def test_subworkflow_output_has_ref_depth(client):
    r = client.get("/api/schema/node/Subworkflow")
    fields = r.json()["output_schema"]["fields"]
    assert "ref" in fields
    assert "depth" in fields


def test_loop_max_iterations_range(client):
    r = client.get("/api/schema/node/Loop")
    vr = r.json()["validation_rules"]
    assert vr["ranges"]["max_iterations"] == {"min": 1, "max": 1000}


def test_node_schema_unknown_type_404(client):
    r = client.get("/api/schema/node/NotARealType")
    assert r.status_code == 404


def test_node_schema_has_visual_hints(client):
    r = client.get("/api/schema/node/LLM")
    body = r.json()
    assert body["visual"]["color"] == "#3b82f6"
    assert "icon" in body["visual"]


def test_all_node_types_have_icon(client):
    from typing import get_args
    from hanflow.core.dsl import NodeType

    for nt in get_args(NodeType):
        r = client.get(f"/api/schema/node/{nt}")
        assert "icon" in r.json()["visual"], f"{nt} missing icon"
