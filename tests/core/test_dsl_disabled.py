"""Tests for WorkflowNode.disabled field (Phase 12 Task 0)."""
from __future__ import annotations

from hanflow.core.dsl import WorkflowDSL, WorkflowNode


def test_workflow_node_has_disabled_field_default_false():
    n = WorkflowNode(id="a", type="LLM")
    assert n.disabled is False


def test_dsl_accepts_disabled_node():
    dsl = WorkflowDSL(name="w", nodes=[
        WorkflowNode(id="a", type="LLM", disabled=True),
    ])
    assert dsl.nodes[0].disabled is True


def test_old_yaml_without_disabled_still_loads():
    yaml_text = "name: w\nnodes:\n  - id: a\n    type: LLM\n"
    dsl = WorkflowDSL.from_yaml(yaml_text)
    assert dsl.nodes[0].disabled is False
