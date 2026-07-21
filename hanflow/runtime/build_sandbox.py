"""build_sandbox — composition root for sandbox provisioning (§13.6).

Cycle 2026-W30-1.1.1 — single entry point that picks the right
``SandboxProvisioner`` for the requested ``SandboxMode`` and provisions a
``RunSandbox``. Returns ``(run_sandbox, provisioned)`` so the caller (typically
``Hanflow._ensure_components`` / ``Hanflow.run``) can wire both into a
``RuntimeContextImpl``.

Composition root status (CHARTER §3): this module is allowed to import
concrete provisioners from L4 ``hanflow/isolation/`` because it is the layer
that assembles the runtime. Business logic never reaches down through here.
"""
from __future__ import annotations

from typing import Any

from hanflow.core.errors import SandboxProvisionFailedError
from hanflow.core.sandbox_contract import (
    ProvisionedSandbox,
    RunSandbox,
    SandboxMode,
    SandboxProvisioner,
    SandboxResources,
)

DEFAULT_DOCKER_IMAGE = "python:3.11-slim"


async def build_sandbox(
    *,
    run_id: str,
    mode: SandboxMode,
    workspace_mgr: Any,
    resources: SandboxResources | None = None,
    docker_image: str = DEFAULT_DOCKER_IMAGE,
) -> tuple[RunSandbox, ProvisionedSandbox]:
    """Provision a sandbox for one run.

    Args:
        run_id: unique run identifier (used for container name + workspace dir).
        mode: desired sandbox isolation level.
        workspace_mgr: WorkspaceManager (or duck-typed) providing
            ``workspace_for(run_id) -> Path``.
        resources: optional SandboxResources override (default applies).
        docker_image: base image for DOCKER mode (ignored by other modes).

    Returns:
        ``(run_sandbox, provisioned)`` — run_sandbox is the pure data model,
        provisioned is the live handle (container/subprocess + ExecInterface).

    Raises:
        SandboxProvisionFailedError: if the chosen provisioner fails to
            provision, or mode is unsupported.
        NotImplementedError: K8S mode (Phase 10 placeholder).
    """
    sb = RunSandbox.create(
        run_id=run_id, mode=mode,
        workspace_mgr=workspace_mgr, resources=resources,
    )

    provisioner: SandboxProvisioner
    if mode == SandboxMode.LOCAL:
        from hanflow.isolation.local_provisioner import LocalProvisioner
        provisioner = LocalProvisioner()
    elif mode == SandboxMode.NONE:
        # NONE: context-only isolation, but execution still needs a host path.
        # Reuse LocalProvisioner (no container, host exec).
        from hanflow.isolation.local_provisioner import LocalProvisioner
        provisioner = LocalProvisioner()
    elif mode == SandboxMode.DOCKER:
        from hanflow.isolation.docker_provisioner import DockerProvisioner
        provisioner = DockerProvisioner(base_image=docker_image)
    elif mode == SandboxMode.K8S:
        from hanflow.isolation.sandbox import K8sProvisioner
        provisioner = K8sProvisioner()
    else:  # exhaustive due to SandboxMode StrEnum, but mypy/defensive
        raise SandboxProvisionFailedError(
            f"unsupported sandbox mode: {mode!r}",
            run_id=run_id,
            details={"mode": str(mode)},
        )

    provisioned = await provisioner.provision(sb)
    return sb, provisioned
