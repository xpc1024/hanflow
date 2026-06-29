"""Sub-agent isolation — DeerFlow-style (§13.6, core).

Three guarantees for every spawned sub-agent (Coordinator dispatch / Execution
delegate / Parallel fan-out):
  1. Context isolation — independent messages; parent's context invisible.
  2. Filesystem collaboration — own subdir under the run workspace.
  3. Run-sandbox reuse — share the per-run sandbox unless ``dedicated_sandbox``.

Sandbox levels (per-run, NOT per-agent):
  - LOCAL     : host execution + per-run dir; bash disabled by default.
  - DOCKER    : AioSandbox isolated container (shell/code).
  - K8S       : provisioner service → pod.
  - NONE      : context isolation only (pure-LLM sub-agents).

DOCKER/K8S provisioning is wired in Phase 8/10; Phase 7 ships LOCAL + NONE
and the full isolation *contract* + spawn_agent().
"""

from __future__ import annotations

import uuid
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from hanflow.core.errors import HanflowError
from hanflow.observability.trace import TraceExporter


class SandboxMode(str, Enum):
    LOCAL = "local"
    DOCKER = "docker"
    K8S = "k8s"
    NONE = "none"


class SandboxResources(BaseModel):
    cpu_limit: str = "2.0"
    memory_limit_mb: int = 2048
    timeout_seconds: int = 3600
    disk_limit_mb: int = 5120
    network_egress: list[str] | None = None


class RunSandbox(BaseModel):
    """Per-run sandbox (NOT per-agent). Aligns with DeerFlow per-task mode."""

    run_id: str
    mode: SandboxMode
    workspace_root: Path
    container_id: str | None = None
    resources: SandboxResources = SandboxResources()
    bash_enabled: bool = False

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @classmethod
    def create(
        cls,
        run_id: str,
        mode: SandboxMode,
        workspace_mgr: Any,
        resources: SandboxResources | None = None,
    ) -> RunSandbox:
        ws = workspace_mgr.workspace_for(run_id)
        bash_enabled = False  # LOCAL default disabled; DOCKER/K8S enable later
        container_id: str | None = None
        if mode in (SandboxMode.DOCKER, SandboxMode.K8S):
            # Provisioning wired in Phase 8/10; for now allocate an id placeholder.
            container_id = f"{mode.value}-{uuid.uuid4().hex[:8]}"
        return cls(
            run_id=run_id,
            mode=mode,
            workspace_root=ws,
            container_id=container_id,
            resources=resources or SandboxResources(),
            bash_enabled=bash_enabled,
        )


class SubAgentIsolation(BaseModel):
    """Isolation contract: context isolation primary, file subdir, run-sandbox reuse."""

    context_isolated: bool = True
    workspace_subdir: str
    tool_whitelist: list[str] | None = None
    share_run_sandbox: bool = True


class AgentSpec(BaseModel):
    task: str
    sub_agent: str
    role: str | None = None
    skills: list[str] | None = None
    tools_whitelist: list[str] | None = None
    dedicated_sandbox: bool = False
    sandbox_mode: SandboxMode | None = None
    # Filled in by spawn_agent():
    workspace_subdir: str | None = None


async def spawn_agent(
    *,
    parent: Any,
    spec: AgentSpec,
    run_sandbox: RunSandbox,
    trace: TraceExporter,
) -> Any:
    """The single entry for sub-agent dispatch (§13.6).

    1. Create an isolated context (independent messages; parent invisible).
    2. Allocate a workspace subdir under the run workspace.
    3. Reuse the run sandbox unless ``dedicated_sandbox``.
    4. Apply ``tool_whitelist``.

    Returns a RuntimeContext-shaped object (FakeContext here; Phase 8 ships the
    real RuntimeContext implementation with the same shape).
    """
    async with trace.span("agent.spawn", kind="workflow", sub_agent=spec.sub_agent, role=spec.role):
        from hanflow.core.context import FakeContext

        # 1. isolated state: copy meta, drop messages + per-node state
        parent_state = parent.state
        child_state = parent_state.model_copy(
            update={
                "messages": [],
                "node_states": {},
                "memory_ops": [],
                "pending_hitl": None,
            }
        )

        # 2. workspace subdir
        sandbox_id = f"agent-{uuid.uuid4().hex[:8]}"
        subdir = str(run_sandbox.workspace_root / sandbox_id)
        run_sandbox.workspace_root.mkdir(parents=True, exist_ok=True)
        Path(subdir).mkdir(parents=True, exist_ok=True)
        spec.workspace_subdir = subdir

        # 3. dedicated sandbox? (Phase 8/10 provisions a real container)
        if spec.dedicated_sandbox and spec.sandbox_mode in (
            SandboxMode.DOCKER,
            SandboxMode.K8S,
        ):
            # Placeholder: real provisioning in Phase 8/10.
            pass

        # 4. build child context with whitelist
        child = FakeContext(state=child_state)
        child._tool_whitelist = spec.tools_whitelist  # type: ignore[attr-defined]
        return child


def enforce_tool_whitelist(tool_name: str, whitelist: list[str] | None) -> None:
    """Raise if a tool call is outside the whitelist (used by Phase 8 ctx)."""
    if whitelist is None:
        return
    if tool_name not in whitelist:
        raise HanflowError(
            f"tool {tool_name!r} not in sub-agent whitelist",
            details={"whitelist": whitelist},
        )
