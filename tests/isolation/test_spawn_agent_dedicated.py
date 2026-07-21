"""dedicated_sandbox contract tests (direction acceptance #8, cycle 2026-W30-1.1.1).

Verifies three things:
  1. dedicated=True/False BOTH reuse the run container; spawn_agent NEVER
     calls provisioner.provision (per-run invariant §2.5).
  2. DOCKER-mode subdir lands inside provisioned.workspace_root (container view);
     LOCAL-mode subdir lands on host workspace_root. This prevents the
     "data-flow break" bug caught in design audit round 1 severe #2.
  3. SandboxError subclasses propagate (code/retryable preserved); other
     exceptions get wrapped as SandboxProvisionFailedError. This enforces
     §5 "no exception swallowing" + §2.1 unified error hierarchy.
"""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from hanflow.core.context import FakeContext
from hanflow.core.errors import SandboxProvisionFailedError, SandboxTimeoutError
from hanflow.core.sandbox_contract import (
    ProvisionedSandbox,
    RunSandbox,
    SandboxMode,
)
from hanflow.core.state import NexusState, RunMeta
from hanflow.isolation.sandbox import AgentSpec, spawn_agent


class _FakeExec:
    """Records mkdir calls; can be configured to raise a specific exception."""

    def __init__(self, fail_with: BaseException | None = None) -> None:
        self.calls: list[list[str]] = []
        self.fail_with = fail_with

    async def run(self, *, command, stdin=None, timeout=30, cwd=None):
        self.calls.append(list(command))
        if self.fail_with is not None:
            raise self.fail_with
        return {"stdout": "", "stderr": "", "returncode": 0}


def _state(run_id: str = "r1") -> NexusState:
    return NexusState(
        meta=RunMeta(
            run_id=run_id, workflow_name="w", workflow_version="0.1.0",
            started_at=datetime.now(UTC), mode="dynamic", trigger="api",
        ),
        inputs={}, outputs={}, node_states={}, artifacts=[], memory_ops=[], variables={},
    )


def _make_provisioned(mode: SandboxMode, fail_with: BaseException | None = None) -> tuple[
    ProvisionedSandbox, _FakeExec
]:
    exec_ = _FakeExec(fail_with)
    ps = ProvisionedSandbox(
        run_id="r1", mode=mode,
        container_id="c1" if mode == SandboxMode.DOCKER else None,
        exec_interface=exec_,
        workspace_root=Path("/workspace"),
    )
    return ps, exec_


@pytest.mark.asyncio
async def test_dedicated_true_docker_mkdir_in_container(workspace_mgr, trace):
    """direction acceptance #8: dedicated=True reuses run container, no new provision.

    FakeExec.records the mkdir call spawn_agent makes inside the run container.
    spawn_agent itself never calls provisioner.provision (that's build_sandbox's job).
    """
    parent = FakeContext(state=_state())
    spec = AgentSpec(
        task="x", sub_agent="a",
        dedicated_sandbox=True, sandbox_mode=SandboxMode.DOCKER,
    )
    run_sb = RunSandbox.create("r1", SandboxMode.DOCKER, workspace_mgr)
    provisioned, fake_exec = _make_provisioned(SandboxMode.DOCKER)

    await spawn_agent(
        parent=parent, spec=spec, run_sandbox=run_sb,
        trace=trace, provisioned=provisioned,
    )

    # mkdir 在 run container 内被调一次(分配 subdir)
    assert len(fake_exec.calls) == 1
    assert fake_exec.calls[0][:2] == ["mkdir", "-p"]
    # subdir 落在容器内 /workspace 下
    assert spec.workspace_subdir is not None
    assert spec.workspace_subdir.startswith("/workspace/agent-")


@pytest.mark.asyncio
async def test_dedicated_false_docker_subdir_also_in_container(workspace_mgr, trace):
    """DOCKER mode: dedicated=False subdir ALSO lands in container view.

    design audit round 1 severe #2: previously the condition
    `spec.dedicated_sandbox and provisioned is not None and mode == DOCKER`
    let dedicated=False fall through to the else branch, putting subdir on
    host path where the container can't see it. Fix: drop `dedicated_sandbox`
    from the condition so ALL DOCKER sub-agents land in container view.
    """
    parent = FakeContext(state=_state())
    spec = AgentSpec(task="x", sub_agent="a", dedicated_sandbox=False)
    run_sb = RunSandbox.create("r1", SandboxMode.DOCKER, workspace_mgr)
    provisioned, fake_exec = _make_provisioned(SandboxMode.DOCKER)

    await spawn_agent(
        parent=parent, spec=spec, run_sandbox=run_sb,
        trace=trace, provisioned=provisioned,
    )

    assert spec.workspace_subdir is not None
    assert spec.workspace_subdir.startswith("/workspace/agent-")
    assert len(fake_exec.calls) == 1


@pytest.mark.asyncio
async def test_dedicated_true_docker_no_new_container_provisioned(workspace_mgr, trace):
    """direction acceptance #8 strict reading: container count must not increase.

    spawn_agent must not invoke any provisioner.provision; we verify by checking
    that spawn_agent returns successfully having only used the existing
    provisioned.exec_interface (mkdir). The provisioner itself is never touched
    here — we only pass `provisioned`, never a `provisioner`.
    """
    parent = FakeContext(state=_state())
    spec = AgentSpec(
        task="x", sub_agent="a",
        dedicated_sandbox=True, sandbox_mode=SandboxMode.DOCKER,
    )
    run_sb = RunSandbox.create("r1", SandboxMode.DOCKER, workspace_mgr)
    provisioned, fake_exec = _make_provisioned(SandboxMode.DOCKER)
    original_container_id = provisioned.container_id

    await spawn_agent(
        parent=parent, spec=spec, run_sandbox=run_sb,
        trace=trace, provisioned=provisioned,
    )

    # container_id 没变(没新 provision)
    assert provisioned.container_id == original_container_id


@pytest.mark.asyncio
async def test_local_mode_subdir_on_host(workspace_mgr, trace):
    """LOCAL mode (provisioned=None or mode=LOCAL) subdir lands on host workspace_root."""
    parent = FakeContext(state=_state())
    spec = AgentSpec(task="x", sub_agent="a")
    run_sb = RunSandbox.create("r1", SandboxMode.LOCAL, workspace_mgr)

    await spawn_agent(
        parent=parent, spec=spec, run_sandbox=run_sb,
        trace=trace, provisioned=None,
    )

    assert spec.workspace_subdir is not None
    # host 路径, 不在 /workspace(容器视角)下
    assert "/workspace/agent-" not in spec.workspace_subdir
    assert "agent-" in spec.workspace_subdir


@pytest.mark.asyncio
async def test_sandbox_error_subclass_propagates(workspace_mgr, trace):
    """§5 no-swallow: SandboxTimeoutError must NOT be downgraded to base HanflowError.

    design audit round 1 severe #3: the old `except Exception as exc: raise
    HanflowError(...)` swallowed the专用 subclass's code/retryable. Fixed by
    `except SandboxError: raise` + `except Exception as exc: raise
    SandboxProvisionFailedError(...) from exc`.
    """
    parent = FakeContext(state=_state())
    spec = AgentSpec(
        task="x", sub_agent="a",
        dedicated_sandbox=True, sandbox_mode=SandboxMode.DOCKER,
    )
    run_sb = RunSandbox.create("r1", SandboxMode.DOCKER, workspace_mgr)
    provisioned, _ = _make_provisioned(
        SandboxMode.DOCKER, fail_with=SandboxTimeoutError("timeout", run_id="r1"),
    )

    with pytest.raises(SandboxTimeoutError) as exc_info:
        await spawn_agent(
            parent=parent, spec=spec, run_sandbox=run_sb,
            trace=trace, provisioned=provisioned,
        )

    # code + retryable 保留(没被吞)
    assert exc_info.value.code == "SANDBOX_TIMEOUT"
    assert exc_info.value.retryable is True


@pytest.mark.asyncio
async def test_non_sandbox_exception_wrapped_as_provision_failed(workspace_mgr, trace):
    """Non-Sandbox exceptions get wrapped as SandboxProvisionFailedError.

    Avoids leaking raw RuntimeError from exec_interface.run out of spawn_agent.
    """
    parent = FakeContext(state=_state())
    spec = AgentSpec(
        task="x", sub_agent="a",
        dedicated_sandbox=True, sandbox_mode=SandboxMode.DOCKER,
    )
    run_sb = RunSandbox.create("r1", SandboxMode.DOCKER, workspace_mgr)
    provisioned, _ = _make_provisioned(
        SandboxMode.DOCKER, fail_with=RuntimeError("docker daemon gone"),
    )

    with pytest.raises(SandboxProvisionFailedError) as exc_info:
        await spawn_agent(
            parent=parent, spec=spec, run_sandbox=run_sb,
            trace=trace, provisioned=provisioned,
        )

    assert exc_info.value.code == "SANDBOX_PROVISION_FAILED"
    assert exc_info.value.retryable is False
    assert "docker daemon gone" in str(exc_info.value)
