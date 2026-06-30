import pytest


@pytest.mark.asyncio
async def test_run_emits_node_events(hf):
    dsl = hf.static(nodes=[{"id": "a", "type": "LLM", "config": {"template": "hi"}}])
    handle = await hf.run(dsl, stream=True)
    events = [e async for e in handle.stream()]
    kinds = {e.kind for e in events}
    assert "node_end" in kinds


@pytest.mark.asyncio
async def test_run_hitl_emits_paused_event(hf):
    dsl = hf.static(
        nodes=[
            {"id": "gate", "type": "HITL", "config": {"actions": ["approve"]}},
        ]
    )
    handle = await hf.run(dsl, stream=True)
    events = [e async for e in handle.stream()]
    kinds = {e.kind for e in events}
    assert "hitl_paused" in kinds


@pytest.mark.asyncio
async def test_run_two_nodes_both_emit(hf):
    dsl = hf.static(
        nodes=[
            {"id": "a", "type": "LLM", "config": {"template": "hi"}},
            {"id": "b", "type": "LLM", "depends_on": ["a"], "config": {"template": "bye"}},
        ]
    )
    handle = await hf.run(dsl, stream=True)
    events = [e async for e in handle.stream()]
    node_ends = [e for e in events if e.kind == "node_end"]
    assert {e.node_id for e in node_ends} == {"a", "b"}
