from datetime import datetime

from langgraph.graph.message import add_messages

from hanflow.core.state import NodeState, NexusState, RunMeta


def test_runmeta_defaults():
    m = RunMeta(
        run_id="r1",
        workflow_name="w",
        workflow_version="0.1.0",
        started_at=datetime.now(),
        mode="static",
        trigger="cli",
    )
    assert m.mode == "static"


def test_nodestate_defaults():
    n = NodeState(node_id="n1", node_type="LLM")
    assert n.status == "pending"
    assert n.inputs == {}
    assert n.attempts == 0
    assert n.hitl is None


def test_nexusstate_messages_field_uses_add_messages_reducer():
    """NexusState fulfills the MessagesState contract: a messages field whose
    annotation carries LangGraph's add_messages reducer, so it is a valid
    StateGraph schema. (LangGraph 1.2.0's stock MessagesState is a dict
    subclass, not Pydantic; NexusState replicates its contract on a Pydantic
    model to stay serializable for checkpoints.)"""
    import typing

    hints = typing.get_type_hints(NexusState, include_extras=True)
    msg_meta = next(m for m in hints["messages"].__metadata__ if m is add_messages)
    assert msg_meta is add_messages


def test_nexusstate_round_trip():
    s = NexusState(
        meta=RunMeta(
            run_id="r1",
            workflow_name="w",
            workflow_version="0.1.0",
            started_at=datetime.now(),
            mode="hybrid",
            trigger="api",
        ),
        inputs={"q": "hello"},
        outputs={},
        node_states={},
        artifacts=[],
        memory_ops=[],
        variables={"x": 1},
        messages=[],
    )
    d = s.model_dump()
    s2 = NexusState.model_validate(d)
    assert s2.meta.run_id == "r1"
    assert s2.variables == {"x": 1}
    assert s2.pending_hitl is None

