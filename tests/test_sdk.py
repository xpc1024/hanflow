from pathlib import Path

import pytest

from hanflow.config import HanflowConfig
from hanflow.sdk import Hanflow, RunHandle


@pytest.fixture
def hf(tmp_path: Path) -> Hanflow:
    cfg = HanflowConfig(workspace_root=str(tmp_path / "ws"))
    return Hanflow(cfg)


def test_static_helper_builds_dsl(hf):
    dsl = hf.static(nodes=[{"id": "a", "type": "LLM", "config": {"template": "hi"}}])
    assert dsl.name == "static"
    assert dsl.nodes[0].id == "a"


def test_dynamic_helper_builds_coordinator_dsl(hf):
    dsl = hf.dynamic(goal="research X", agents=["researcher", "writer"], plan_hitl=True)
    assert dsl.nodes[0].type == "Coordinator"
    assert (dsl.nodes[0].config.__pydantic_extra__ or {}).get("plan_hitl") is True


def test_runmode_auto_detects_static_vs_dynamic(hf):
    static_dsl = hf.static(nodes=[{"id": "a", "type": "LLM", "config": {}}])
    assert hf._auto_mode(static_dsl) == "static"
    dynamic_dsl = hf.dynamic(goal="x", agents=["a"])
    assert hf._auto_mode(dynamic_dsl) == "dynamic"


@pytest.mark.asyncio
async def test_run_static_workflow_end_to_end(hf):
    dsl = hf.static(nodes=[{"id": "a", "type": "LLM", "config": {"template": "hi"}}])
    handle = await hf.run(dsl, inputs={}, mode="static")
    assert isinstance(handle, RunHandle)
    assert handle.run_id
    result = await handle.wait()
    assert result.status == "succeeded"


@pytest.mark.asyncio
async def test_run_tool_node_end_to_end(hf):
    dsl = hf.static(
        nodes=[{"id": "t", "type": "Tool", "config": {"tool": "echo.say", "args": {"msg": "ping"}}}]
    )
    handle = await hf.run(dsl)
    result = await handle.wait()
    assert result.status == "succeeded"
