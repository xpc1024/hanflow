"""Tests for build_sandbox composition root (cycle 2026-W30-1.1.1).

Verifies that build_sandbox dispatches to the right provisioner per mode and
returns a (RunSandbox, ProvisionedSandbox) tuple. K8S dispatch raises
NotImplementedError (placeholder for Phase 10).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from hanflow.core.errors import SandboxProvisionFailedError
from hanflow.core.sandbox_contract import (
    ProvisionedSandbox,
    RunSandbox,
    SandboxMode,
)
from hanflow.runtime.build_sandbox import build_sandbox


class _FakeMgr:
    def workspace_for(self, run_id: str) -> Path:
        return Path(f"/tmp/{run_id}")


@pytest.mark.asyncio
async def test_build_sandbox_local_returns_both():
    sb, provisioned = await build_sandbox(
        run_id="r1", mode=SandboxMode.LOCAL, workspace_mgr=_FakeMgr(),
    )
    assert isinstance(sb, RunSandbox)
    assert isinstance(provisioned, ProvisionedSandbox)
    assert provisioned.mode == SandboxMode.LOCAL
    assert provisioned.container_id is None


@pytest.mark.asyncio
async def test_build_sandbox_none_reuses_local_provisioner():
    """NONE mode reuses LocalProvisioner (context isolation handled elsewhere)."""
    sb, provisioned = await build_sandbox(
        run_id="r1", mode=SandboxMode.NONE, workspace_mgr=_FakeMgr(),
    )
    assert provisioned.container_id is None
    assert sb.mode == SandboxMode.NONE


@pytest.mark.asyncio
async def test_build_sandbox_k8s_raises_not_implemented():
    """K8S mode raises NotImplementedError (Phase 10 placeholder)."""
    with pytest.raises(NotImplementedError, match="Phase 10"):
        await build_sandbox(
            run_id="r1", mode=SandboxMode.K8S, workspace_mgr=_FakeMgr(),
        )


@pytest.mark.asyncio
async def test_build_sandbox_docker_with_fake_provisioner(monkeypatch):
    """DOCKER dispatch picks DockerProvisioner; we monkeypatch to avoid daemon."""
    from hanflow.isolation import docker_provisioner as dp_mod

    captured: dict[str, Any] = {}

    class _FakeDocker:
        name = "docker"

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            captured["init_kwargs"] = kwargs

        async def provision(self, sb: RunSandbox) -> ProvisionedSandbox:
            captured["provisioned_run_id"] = sb.run_id
            return ProvisionedSandbox(
                run_id=sb.run_id, mode=SandboxMode.DOCKER, container_id="fake-cid",
                exec_interface=object(),  # tests only care about dispatch
                workspace_root=Path("/workspace"),
            )

        async def destroy(self, p: ProvisionedSandbox) -> None:
            pass

    monkeypatch.setattr(dp_mod, "DockerProvisioner", _FakeDocker)

    sb, provisioned = await build_sandbox(
        run_id="r1", mode=SandboxMode.DOCKER, workspace_mgr=_FakeMgr(),
        docker_image="python:3.12-slim",
    )
    assert provisioned.container_id == "fake-cid"
    assert provisioned.mode == SandboxMode.DOCKER
    assert captured["init_kwargs"] == {"base_image": "python:3.12-slim"}
    assert captured["provisioned_run_id"] == "r1"


@pytest.mark.asyncio
async def test_build_sandbox_docker_default_image(monkeypatch):
    """Default base_image is python:3.11-slim."""
    from hanflow.isolation import docker_provisioner as dp_mod

    captured: dict[str, Any] = {}

    class _FakeDocker:
        name = "docker"

        def __init__(self, base_image: str = "default") -> None:
            captured["base_image"] = base_image

        async def provision(self, sb: RunSandbox) -> ProvisionedSandbox:
            return ProvisionedSandbox(
                run_id=sb.run_id, mode=SandboxMode.DOCKER, container_id="x",
                exec_interface=None, workspace_root=Path("/workspace"),
            )

        async def destroy(self, p: ProvisionedSandbox) -> None:
            pass

    monkeypatch.setattr(dp_mod, "DockerProvisioner", _FakeDocker)

    await build_sandbox(
        run_id="r1", mode=SandboxMode.DOCKER, workspace_mgr=_FakeMgr(),
    )
    assert captured["base_image"] == "python:3.11-slim"


@pytest.mark.asyncio
async def test_build_sandbox_returns_workspace_root_set():
    """RunSandbox.workspace_root comes from workspace_mgr.workspace_for."""
    sb, _ = await build_sandbox(
        run_id="r42", mode=SandboxMode.LOCAL, workspace_mgr=_FakeMgr(),
    )
    assert sb.workspace_root == Path("/tmp/r42")
