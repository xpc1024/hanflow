"""Sandbox contract layer (L0 core): types + Protocol + data models (§13.6, §5.3).

Cycle 2026-W30-1.1.1 — moves ``SandboxMode`` / ``SandboxResources`` / ``RunSandbox``
up from ``hanflow/isolation/sandbox.py`` to ``hanflow/core/``, and adds three new
contract types: ``SandboxProvisioner`` Protocol, ``ProvisionedSandbox`` data model,
``ExecInterface`` Protocol. ``hanflow/isolation/sandbox.py`` becomes a re-export
shim for backward compatibility.

Design invariants (CHARTER §2):
  - §2.3 Pydantic v2 data models (BaseModel + ConfigDict)
  - §2.5 per-run sandbox (NOT per-agent)
  - §3 dependency matrix: core only depends on itself; this file MUST NOT import
    ``hanflow.isolation.*`` (reverse-dependency guard, charter-check enforced)

Dependency inversion (CHARTER §3): the Protocol lives in core, concrete
implementations live in ``hanflow/isolation/`` (Local/Docker/K8s), and the
composition root ``hanflow/runtime/build_sandbox.py`` injects the chosen
provisioner. ``spawn_agent`` / ``RuntimeContextImpl`` consume the contract via
the Protocol — they never import concrete provisioner classes.
"""
from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict


class SandboxMode(StrEnum):
    """Sandbox isolation level (per-run, NOT per-agent — §2.5)."""

    LOCAL = "local"      # host execution + per-run dir; bash disabled by default
    DOCKER = "docker"    # AioSandbox isolated container (cycle 2026-W30-1.1.1)
    K8S = "k8s"          # provisioner service → pod (Phase 10, placeholder)
    NONE = "none"        # context isolation only (pure-LLM sub-agents)


class SandboxResources(BaseModel):
    """Sandbox resource limits.

    Field-to-Docker mapping (applied by ``DockerProvisioner``):
      - ``cpu_limit`` (str, float as str) → ``--cpus``
      - ``memory_limit_mb`` → ``--memory`` (bytes)
      - ``timeout_seconds`` → container ``Cmd: ["sleep", N]`` (liveness cap)
      - ``disk_limit_mb`` → ``--storage-opt size=...m`` (overlay2 only)
      - ``network_egress``: ``None`` → ``--network=none`` (airtight);
        non-None → ``--network=host`` (explicit opt-in; ACL engine is out of
        scope for this cycle — see direction.md non-goal #7).
    """

    cpu_limit: str = "2.0"
    memory_limit_mb: int = 2048
    timeout_seconds: int = 3600
    disk_limit_mb: int = 5120
    network_egress: list[str] | None = None


class RunSandbox(BaseModel):
    """Per-run sandbox (pure data model, §2.5 per-run invariant).

    Provisioner behaviour does NOT live in this model (§2.3 model-purity);
    DOCKER/K8S provisioning is done by the composition root
    ``runtime.build_sandbox`` via a ``SandboxProvisioner``.
    """

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
        """LOCAL/NONE backward-compatible shortcut (deprecated for DOCKER/K8S).

        DOCKER/K8S modes should go through ``runtime.build_sandbox`` so the
        composition root can inject a provisioner. This method is retained
        only to keep the 5 existing call sites unchanged:
          - ``tests/isolation/test_sandbox.py`` × 4
          - ``tests/conftest.py``
          - ``hanflow/sdk.py``
        """

        ws = workspace_mgr.workspace_for(run_id)
        return cls(
            run_id=run_id,
            mode=mode,
            workspace_root=ws,
            resources=resources or SandboxResources(),
            bash_enabled=False,  # LOCAL default: bash disabled
        )


# Definition order (eliminates forward references, matches core/context.py
# "Protocol before implementation" convention):
#   ExecInterface → ProvisionedSandbox → SandboxProvisioner


class ExecInterface(Protocol):
    """Backend-agnostic code-execution interface (reused by code_exec et al.).

    Implementations:
      - ``LocalProvisioner`` → host subprocess (``_LocalExec``)
      - ``DockerProvisioner`` → ``docker exec`` (``_DockerExec``)

    Returns a dict shaped like the existing ``_exec_local()`` output so call
    sites stay isomorphic. Timeouts are wrapped internally as
    ``SandboxTimeoutError`` — callers never see bare ``TimeoutError``.
    """

    async def run(
        self,
        *,
        command: list[str],
        stdin: str | None = None,
        timeout: int = 30,
        cwd: str | None = None,
    ) -> dict[str, Any]:
        """Execute ``command``, return ``{"stdout": str, "stderr": str, "returncode": int}``.

        Raises:
            SandboxTimeoutError: when ``timeout`` exceeded (retryable=True).
            SandboxError subclass: for other backend failures.
        """
        ...


class ProvisionedSandbox(BaseModel):
    """Artifact of ``SandboxProvisioner.provision``: handle + exec interface.

    ``workspace_root`` is the bind-mount or host path; for DOCKER mode it is
    the in-container view (e.g. ``/workspace``), so sub-agent subdirs land
    inside the container's visible filesystem.

    ``exec_interface`` is typed ``Any`` because Pydantic v2 cannot use a
    ``typing.Protocol`` as a field type (even with ``arbitrary_types_allowed=True``);
    runtime contract is ``ExecInterface`` (callers may isinstance-check against
    the ``@runtime_checkable`` Protocol if needed).
    """

    run_id: str
    mode: SandboxMode
    container_id: str | None = None      # None for LOCAL/NONE; required for DOCKER/K8S
    exec_interface: Any                  # implements ExecInterface (see Protocol above)
    workspace_root: Path                 # bind mount or host path
    model_config = ConfigDict(arbitrary_types_allowed=True)


@runtime_checkable
class SandboxProvisioner(Protocol):
    """L0 contract: provision a ``RunSandbox`` (data) into a ``ProvisionedSandbox``.

    Implementations live in L4 ``hanflow/isolation/`` (Local/Docker/K8s); the
    composition root ``runtime/build_sandbox.py`` injects the chosen one.

    §2.5 per-run invariant: ``provision`` accepts a run-level ``RunSandbox``
    only — NEVER a per-agent spec. ``spawn_agent(dedicated_sandbox=True)``
    reuses the run container and allocates an in-container subdir; it does
    NOT call ``provision`` again.
    """

    name: str

    async def provision(self, run_sandbox: RunSandbox) -> ProvisionedSandbox: ...

    async def destroy(self, provisioned: ProvisionedSandbox) -> None: ...
