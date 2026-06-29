from datetime import UTC, datetime

import pytest

from hanflow.core.context import FakeContext
from hanflow.core.errors import HanflowError
from hanflow.core.state import NexusState, RunMeta
from hanflow.isolation.sandbox import (
    AgentSpec,
    RunSandbox,
    SandboxMode,
    SubAgentIsolation,
    enforce_tool_whitelist,
    spawn_agent,
)


def _state(run_id: str = "r1") -> NexusState:
    return NexusState(
        meta=RunMeta(
            run_id=run_id,
            workflow_name="w",
            workflow_version="0.1.0",
            started_at=datetime.now(UTC),
            mode="dynamic",
            trigger="api",
        ),
        inputs={},
        outputs={},
        node_states={},
        artifacts=[],
        memory_ops=[],
        variables={},
    )


@pytest.mark.asyncio
async def test_run_sandbox_local_creates_workspace(workspace_mgr):
    sb = RunSandbox.create(run_id="r1", mode=SandboxMode.LOCAL, workspace_mgr=workspace_mgr)
    assert sb.workspace_root.exists()
    assert sb.bash_enabled is False  # LOCAL default disabled


@pytest.mark.asyncio
async def test_run_sandbox_none_mode_no_container(workspace_mgr):
    sb = RunSandbox.create(run_id="r1", mode=SandboxMode.NONE, workspace_mgr=workspace_mgr)
    assert sb.container_id is None


@pytest.mark.asyncio
async def test_spawn_agent_isolates_context(workspace_mgr, trace):
    parent_state = _state()
    parent_state.messages = [{"role": "user", "content": "parent secret"}]
    parent = FakeContext(state=parent_state)

    spec = AgentSpec(
        task="do thing",
        sub_agent="researcher",
        role="researcher",
        tools_whitelist=["web_search.search"],
    )
    child = await spawn_agent(
        parent=parent,
        spec=spec,
        run_sandbox=RunSandbox.create(
            run_id="r1", mode=SandboxMode.LOCAL, workspace_mgr=workspace_mgr
        ),
        trace=trace,
    )

    # Context isolation: child messages are independent of parent's
    assert child.state.messages == []
    assert parent.state.messages == [{"role": "user", "content": "parent secret"}]
    # Workspace subdir allocated
    assert spec.workspace_subdir  # set by spawn
    # Tool whitelist enforced on child
    assert child._tool_whitelist == ["web_search.search"]  # type: ignore[attr-defined]


def test_subagent_isolation_contract_defaults():
    iso = SubAgentIsolation(workspace_subdir="r1/workspace/agent-1")
    assert iso.context_isolated is True
    assert iso.share_run_sandbox is True


@pytest.mark.asyncio
async def test_dedicated_sandbox_flag_honored(workspace_mgr, trace):
    parent = FakeContext(state=_state("r2"))
    spec = AgentSpec(
        task="x",
        sub_agent="a",
        dedicated_sandbox=True,
        sandbox_mode=SandboxMode.NONE,
    )
    child = await spawn_agent(
        parent=parent,
        spec=spec,
        run_sandbox=RunSandbox.create(
            run_id="r2", mode=SandboxMode.LOCAL, workspace_mgr=workspace_mgr
        ),
        trace=trace,
    )
    assert isinstance(child, FakeContext)


def test_enforce_tool_whitelist_allows_and_blocks():
    enforce_tool_whitelist("a.b", ["a.b"])  # ok
    with pytest.raises(HanflowError):
        enforce_tool_whitelist("c.d", ["a.b"])
    enforce_tool_whitelist("any", None)  # no whitelist = allow all
