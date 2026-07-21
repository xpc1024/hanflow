"""Sub-agent isolation — DeerFlow-style (§13.6, core).

Three guarantees for every spawned sub-agent (Coordinator dispatch / Execution
delegate / Parallel fan-out):
  1. Context isolation — independent messages; parent's context invisible.
  2. Filesystem collaboration — own subdir under the run workspace.
  3. Run-sandbox reuse — share the per-run sandbox; ``dedicated_sandbox=True``
     still reuses the run container and only allocates an in-container subdir
     (per §2.5 invariant; no per-agent provisioning).

Sandbox levels (per-run, NOT per-agent):
  - LOCAL     : host execution + per-run dir; bash disabled by default.
  - DOCKER    : AioSandbox isolated container (shell/code). Landed in cycle
                2026-W30-1.1.1 via hanflow/isolation/docker_provisioner.py.
  - K8S       : provisioner service → pod. Placeholder, lands in Phase 10.
  - NONE      : context isolation only (pure-LLM sub-agents).

Cycle 2026-W30-1.1.1 refactor:
  SandboxMode/SandboxResources/RunSandbox moved up to
  ``hanflow/core/sandbox_contract.py`` (L0). This module re-exports them for
  backward compatibility (``from hanflow.isolation.sandbox import RunSandbox``
  still works, returns the same class object).

The full isolation *contract* + ``spawn_agent()`` remain here. Provisioner
implementations live in sibling files (``local_provisioner.py``,
``docker_provisioner.py``) plus the ``K8sProvisioner`` placeholder at the
bottom of this file.
"""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from hanflow.core.errors import (
    SandboxError,
    SandboxProvisionFailedError,
    ToolWhitelistError,
)
from hanflow.core.sandbox_contract import (
    ExecInterface,  # re-export
    ProvisionedSandbox,  # re-export
    RunSandbox,  # re-export (definition moved to core)
    SandboxMode,  # re-export
    SandboxProvisioner,  # re-export
    SandboxResources,  # re-export
)
from hanflow.observability.trace import TraceExporter

__all__ = [
    # re-exported from core (backward compat for downstream imports)
    "SandboxMode",
    "SandboxResources",
    "RunSandbox",
    "SandboxProvisioner",
    "ProvisionedSandbox",
    "ExecInterface",
    # defined here
    "SubAgentIsolation",
    "AgentSpec",
    "spawn_agent",
    "enforce_tool_whitelist",
    "K8sProvisioner",
]


class SubAgentIsolation(BaseModel):
    """Isolation contract: context isolation primary, file subdir, run-sandbox reuse."""

    context_isolated: bool = True
    workspace_subdir: str
    tool_whitelist: list[str] | None = None
    share_run_sandbox: bool = True


class AgentSpec(BaseModel):
    """Spec for a sub-agent to be spawned via ``spawn_agent``."""

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
    provisioned: ProvisionedSandbox | None = None,
) -> Any:
    """The single entry for sub-agent dispatch (§13.6).

    Cycle 2026-W30-1.1.1: adds optional ``provisioned`` (from build_sandbox).
    All sub-agents — ``dedicated_sandbox`` True or False — **reuse the run
    sandbox** (§2.5 per-run invariant). DOCKER mode allocates an in-container
    subdir via ``provisioned.exec_interface`` so sub-agent writes are visible
    inside the container (audit round 1 severe #2 fix).

    Returns a RuntimeContext-shaped object (FakeContext here; Phase 8 ships the
    real RuntimeContext implementation with the same shape).
    """
    async with trace.span(
        "agent.spawn", kind="workflow", sub_agent=spec.sub_agent, role=spec.role,
    ) as sp:  # round 1 audit cleanup: use the yielded Span
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

        # 2. workspace subdir.
        # Round 1 audit severe #2 fix: DOCKER mode subdir MUST land inside
        # provisioned.workspace_root (container view). Falling back to
        # run_sandbox.workspace_root (host path) would put sub-agent writes
        # outside the container's bind-mount and silently break data flow.
        subdir_name = f"agent-{uuid.uuid4().hex[:8]}"
        if provisioned is not None and provisioned.mode == SandboxMode.DOCKER:
            # §2.5: reuse run container; just allocate an in-container subdir.
            # dedicated_sandbox is honoured by *not* provisioning a new
            # container here (only build_sandbox provisions, once per run).
            #
            # Container-internal paths are always POSIX (Linux); avoid Path /
            # which on Windows host would produce backslashes ("\workspace\agent-x").
            workspace_str = str(provisioned.workspace_root).replace("\\", "/")
            # normalize trailing slash so we don't get "//agent-x"
            workspace_str = workspace_str.rstrip("/")
            subdir = f"{workspace_str}/{subdir_name}"
            try:
                await provisioned.exec_interface.run(
                    command=["mkdir", "-p", subdir], timeout=5,
                )
            except SandboxError:
                # propagate专用 subclass — preserves code + retryable (§5).
                raise
            except Exception as exc:
                # Non-Sandbox exceptions get wrapped; Sandbox subclass errors
                # above pass through unchanged.
                raise SandboxProvisionFailedError(
                    f"failed to allocate subdir in container: {exc}",
                    run_id=run_sandbox.run_id,
                    details={"subdir": subdir},
                ) from exc
        else:
            # LOCAL/NONE (or no provisioned wired): subdir on host workspace.
            subdir = str(run_sandbox.workspace_root / subdir_name)
            run_sandbox.workspace_root.mkdir(parents=True, exist_ok=True)
            Path(subdir).mkdir(parents=True, exist_ok=True)
        spec.workspace_subdir = subdir

        # 3. dedicated_sandbox: NO per-agent provisioning (§2.5). The legacy
        # branch that *would* have provisioned per-agent is now a no-op; the
        # in-container subdir above is the dedicated semantics.

        # 4. build child context with whitelist
        child = FakeContext(state=child_state)
        child._tool_whitelist = spec.tools_whitelist  # type: ignore[attr-defined]
        await trace.event(
            "agent.spawned", sub_agent=spec.sub_agent, span_id=sp.span_id,
        )
        return child


def enforce_tool_whitelist(tool_name: str, whitelist: list[str] | None) -> None:
    """Raise if a tool call is outside the whitelist (used by ctx.tool_call).

    Cycle 2026-W30-1.1.1: uses专用 ``ToolWhitelistError`` instead of base
    ``HanflowError`` (matches the rest of the error hierarchy).
    """
    if whitelist is None:
        return
    if tool_name not in whitelist:
        raise ToolWhitelistError(
            f"tool {tool_name!r} not in sub-agent whitelist",
            details={"whitelist": whitelist},
        )


class K8sProvisioner:
    """K8S sandbox provisioner placeholder (Phase 10, cycle 2026-W30-1.1.1).

    Why a class instead of just letting ``SandboxMode.K8S`` raise at the
    composition root: ``SandboxProvisioner`` is a ``@runtime_checkable``
    Protocol and K8S is one of its declared implementations. Giving it an
    explicit placeholder class lets ``build_sandbox`` dispatch uniformly and
    surface a clear NotImplementedError (CHARTER §4 placeholder convention).
    """

    name = "k8s"

    async def provision(self, run_sandbox: RunSandbox) -> ProvisionedSandbox:
        raise NotImplementedError(
            f"K8S sandbox provisioning lands in Phase 10 "
            f"(got run_id={run_sandbox.run_id})"
        )

    async def destroy(self, provisioned: ProvisionedSandbox) -> None:
        raise NotImplementedError(
            f"K8S sandbox destroy lands in Phase 10 "
            f"(got run_id={provisioned.run_id})"
        )
