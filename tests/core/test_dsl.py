import pytest
from pydantic import ValidationError

from hanflow.core.dsl import WorkflowDSL, WorkflowNode
from hanflow.core.errors import DSLValidationError


def _node(i: str, t: str = "LLM", depends_on: list[str] | None = None) -> WorkflowNode:
    return WorkflowNode(id=i, type=t, depends_on=depends_on or [])  # type: ignore[arg-type]


def test_minimal_valid_dsl():
    d = WorkflowDSL(name="w", nodes=[_node("a")])
    assert d.version == "0.1.0"
    assert d.nodes[0].id == "a"


def test_duplicate_node_id_rejected():
    with pytest.raises(DSLValidationError) as exc:
        WorkflowDSL(name="w", nodes=[_node("a"), _node("a")])
    assert "duplicate" in str(exc.value).lower()


def test_unknown_dependency_rejected():
    with pytest.raises(DSLValidationError) as exc:
        WorkflowDSL(name="w", nodes=[_node("a", depends_on=["ghost"])])
    assert "ghost" in str(exc.value)


def test_cycle_rejected():
    # a -> b -> a
    with pytest.raises(DSLValidationError) as exc:
        WorkflowDSL(
            name="w",
            nodes=[_node("a", depends_on=["b"]), _node("b", depends_on=["a"])],
        )
    assert "cycle" in str(exc.value).lower() or "loop" in str(exc.value).lower()


def test_entry_node_unique():
    # Two roots (no depends_on) is ambiguous entry → error
    with pytest.raises(DSLValidationError) as exc:
        WorkflowDSL(name="w", nodes=[_node("a"), _node("b", depends_on=[])])
    assert "entry" in str(exc.value).lower()


def test_template_reference_to_unknown_node_rejected():
    with pytest.raises(DSLValidationError) as exc:
        WorkflowDSL(
            name="w",
            nodes=[
                WorkflowNode(
                    id="b",
                    type="LLM",
                    depends_on=["a"],
                    config={"__template__": "{{ghost.output}}"},
                ),
                _node("a"),
            ],
        )
    assert "ghost" in str(exc.value)


def test_template_reference_to_known_node_ok():
    d = WorkflowDSL(
        name="w",
        nodes=[
            _node("a"),
            WorkflowNode(
                id="b",
                type="LLM",
                depends_on=["a"],
                config={"__template__": "{{a.output}}"},
            ),
        ],
    )
    assert len(d.nodes) == 2


def test_invalid_node_type_rejected():
    # Pydantic's Literal enforces the closed NodeType set at construction time
    # (before the model_validator runs), so an invalid type raises ValidationError.
    with pytest.raises((DSLValidationError, ValidationError)):
        WorkflowDSL(name="w", nodes=[_node("a", t="NotARealType")])  # type: ignore[arg-type]


def test_yaml_round_trip():
    import yaml

    d = WorkflowDSL(name="w", nodes=[_node("a")])
    y = yaml.safe_dump(d.model_dump(mode="json"))
    d2 = WorkflowDSL.model_validate(yaml.safe_load(y))
    assert d2 == d


def test_from_yaml_helper():
    text = """
name: 内容审核
nodes:
  - id: draft
    type: LLM
"""
    d = WorkflowDSL.from_yaml(text)
    assert d.name == "内容审核"
    assert d.nodes[0].id == "draft"
