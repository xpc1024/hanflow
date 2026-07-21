"""Tests for DockerProvisioner + _DockerExec (cycle 2026-W30-1.1.1).

Strategy:
  - ``_build_config`` resource mapping: pure unit test, no daemon needed.
  - dep_missing: monkeypatch sys.modules so aiodocker import fails.
  - Full provision/destroy lifecycle: ``pytest.mark.skipif(not HAS_DOCKER)`` —
    runs only when a docker daemon is actually reachable.
"""
from __future__ import annotations

import asyncio
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from hanflow.core.errors import (
    SandboxDependencyMissingError,
)
from hanflow.core.sandbox_contract import RunSandbox, SandboxMode, SandboxResources


def _docker_available() -> bool:
    """Probe docker CLI + running daemon (Linux engine accessible)."""
    if not shutil.which("docker"):
        return False
    try:
        r = subprocess.run(
            ["docker", "info", "--format", "{{.ServerVersion}}"],
            capture_output=True, timeout=5,
        )
        return r.returncode == 0 and bool(r.stdout.decode().strip())
    except Exception:
        return False


HAS_DOCKER = _docker_available()
skip_no_docker = pytest.mark.skipif(not HAS_DOCKER, reason="no docker daemon")


class _FakeMgr:
    def workspace_for(self, run_id: str) -> Path:
        return Path(f"/tmp/{run_id}")


# ---------------------------------------------------------------------------
# _build_config — pure unit tests (no daemon needed)
# ---------------------------------------------------------------------------


def test_build_config_resource_mapping(tmp_path):
    """Resource fields map to Docker HostConfig fields correctly."""
    from hanflow.isolation.docker_provisioner import DockerProvisioner

    p = DockerProvisioner(base_image="python:3.11-slim")
    sb = RunSandbox(
        run_id="r1", mode=SandboxMode.DOCKER, workspace_root=tmp_path,
        resources=SandboxResources(
            cpu_limit="2.0", memory_limit_mb=2048, timeout_seconds=3600,
            disk_limit_mb=5120, network_egress=None,
        ),
    )
    config = p._build_config(sb)

    assert config["Image"] == "python:3.11-slim"
    assert config["Cmd"] == ["sleep", "3600"]
    assert config["WorkingDir"] == "/workspace"
    hc = config["HostConfig"]
    assert hc["CpuQuota"] == 200000  # 2.0 * 100000
    assert hc["Memory"] == 2048 * 1024 * 1024
    assert hc["NetworkMode"] == "none"  # network_egress is None → airtight
    assert hc["StorageOpt"] == {"size": "5120m"}
    assert len(hc["Binds"]) == 1
    assert "/workspace:rw" in hc["Binds"][0]


def test_build_config_network_host_when_egress_set(tmp_path):
    """network_egress non-None → --network=host (ACL engine out of scope)."""
    from hanflow.isolation.docker_provisioner import DockerProvisioner

    p = DockerProvisioner()
    sb = RunSandbox(
        run_id="r1", mode=SandboxMode.DOCKER, workspace_root=tmp_path,
        resources=SandboxResources(network_egress=["*"]),
    )
    config = p._build_config(sb)
    assert config["HostConfig"]["NetworkMode"] == "host"


def test_build_config_cpu_quota_fractional(tmp_path):
    """cpu_limit="0.5" → CpuQuota=50000."""
    from hanflow.isolation.docker_provisioner import DockerProvisioner

    p = DockerProvisioner()
    sb = RunSandbox(
        run_id="r1", mode=SandboxMode.DOCKER, workspace_root=tmp_path,
        resources=SandboxResources(cpu_limit="0.5"),
    )
    config = p._build_config(sb)
    assert config["HostConfig"]["CpuQuota"] == 50000


def test_build_config_no_storage_opt_when_disk_zero(tmp_path):
    """disk_limit_mb=0 → no StorageOpt (don't impose quota)."""
    from hanflow.isolation.docker_provisioner import DockerProvisioner

    p = DockerProvisioner()
    sb = RunSandbox(
        run_id="r1", mode=SandboxMode.DOCKER, workspace_root=tmp_path,
        resources=SandboxResources(disk_limit_mb=0),
    )
    config = p._build_config(sb)
    assert config["HostConfig"]["StorageOpt"] is None


def test_docker_provisioner_name():
    from hanflow.isolation.docker_provisioner import DockerProvisioner
    assert DockerProvisioner.name == "docker"


# ---------------------------------------------------------------------------
# dep_missing — monkeypatch sys.modules
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_provision_raises_dep_missing_when_aiodocker_absent(monkeypatch):
    """aiodocker uninstalled → SandboxDependencyMissingError (non-retryable)."""
    from hanflow.isolation import docker_provisioner as dp_mod

    sb = RunSandbox.create("r1", SandboxMode.DOCKER, _FakeMgr())
    p = dp_mod.DockerProvisioner()

    # Force ImportError on `from aiodocker import Docker`
    monkeypatch.setitem(sys.modules, "aiodocker", None)

    with pytest.raises(SandboxDependencyMissingError) as exc_info:
        await p.provision(sb)
    assert exc_info.value.code == "SANDBOX_DEP_MISSING"
    assert exc_info.value.retryable is False
    assert "aiodocker" in str(exc_info.value).lower() or "pip install" in str(exc_info.value)


@pytest.mark.asyncio
async def test_provision_wrong_mode_raises_value_error():
    """Wrong mode is programmer error → ValueError (not §2.1 territory)."""
    from hanflow.isolation.docker_provisioner import DockerProvisioner

    sb = RunSandbox.create("r1", SandboxMode.LOCAL, _FakeMgr())
    p = DockerProvisioner()
    with pytest.raises(ValueError, match="DockerProvisioner"):
        await p.provision(sb)


# ---------------------------------------------------------------------------
# Full lifecycle — only when daemon is reachable
# ---------------------------------------------------------------------------


@skip_no_docker
@pytest.mark.asyncio
async def test_provision_real_container_lifecycle(tmp_path):
    """Contract: real container provision → exec → destroy."""
    from hanflow.isolation.docker_provisioner import DockerProvisioner

    sb = RunSandbox(
        run_id=f"hanflow-test-{tmp_path.name[:8]}",
        mode=SandboxMode.DOCKER, workspace_root=tmp_path,
        resources=SandboxResources(
            cpu_limit="1.0", memory_limit_mb=512, timeout_seconds=60,
        ),
    )
    p = DockerProvisioner(base_image="python:3.11-slim")
    provisioned = await p.provision(sb)

    try:
        assert provisioned.container_id is not None
        assert provisioned.mode == SandboxMode.DOCKER
        assert str(provisioned.workspace_root) == "/workspace"

        result = await provisioned.exec_interface.run(
            command=["python3", "-c", "print('hello from docker')"], timeout=15,
        )
        assert result["returncode"] == 0
        assert "hello from docker" in result["stdout"]
    finally:
        await p.destroy(provisioned)


@skip_no_docker
@pytest.mark.asyncio
async def test_provision_resource_limits_enforced(tmp_path):
    """Resource limits actually applied to the running container."""
    from hanflow.isolation.docker_provisioner import DockerProvisioner

    sb = RunSandbox(
        run_id=f"hanflow-rl-{tmp_path.name[:8]}",
        mode=SandboxMode.DOCKER, workspace_root=tmp_path,
        resources=SandboxResources(
            cpu_limit="1.5", memory_limit_mb=256, timeout_seconds=30,
        ),
    )
    p = DockerProvisioner(base_image="python:3.11-slim")
    provisioned = await p.provision(sb)

    try:
        proc = await asyncio.create_subprocess_exec(
            "docker", "inspect", "--format", "{{.HostConfig.Memory}}",
            provisioned.container_id,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        # 256 MB = 268435456 bytes
        assert stdout.decode().strip() == "268435456"
    finally:
        await p.destroy(provisioned)


@skip_no_docker
@pytest.mark.asyncio
async def test_destroy_removes_container(tmp_path):
    """After destroy, container no longer exists."""
    from hanflow.isolation.docker_provisioner import DockerProvisioner

    sb = RunSandbox(
        run_id=f"hanflow-dest-{tmp_path.name[:8]}",
        mode=SandboxMode.DOCKER, workspace_root=tmp_path,
        resources=SandboxResources(timeout_seconds=30),
    )
    p = DockerProvisioner(base_image="python:3.11-slim")
    provisioned = await p.provision(sb)
    cid = provisioned.container_id
    assert cid is not None

    await p.destroy(provisioned)

    # Container should be gone
    proc = await asyncio.create_subprocess_exec(
        "docker", "inspect", "--format", "{{.Id}}", cid,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    await proc.communicate()
    assert proc.returncode != 0  # docker inspect fails on absent container


@skip_no_docker
@pytest.mark.asyncio
async def test_exec_timeout_wrapped_as_sandbox_timeout(tmp_path):
    """_DockerExec.run wraps timeout internally as SandboxTimeoutError."""
    from hanflow.core.errors import SandboxTimeoutError
    from hanflow.isolation.docker_provisioner import DockerProvisioner

    sb = RunSandbox(
        run_id=f"hanflow-to-{tmp_path.name[:8]}",
        mode=SandboxMode.DOCKER, workspace_root=tmp_path,
        resources=SandboxResources(timeout_seconds=30),
    )
    p = DockerProvisioner(base_image="python:3.11-slim")
    provisioned = await p.provision(sb)

    try:
        with pytest.raises(SandboxTimeoutError) as exc_info:
            await provisioned.exec_interface.run(
                command=["python3", "-c", "import time; time.sleep(10)"],
                timeout=1,
            )
        assert exc_info.value.code == "SANDBOX_TIMEOUT"
        assert exc_info.value.retryable is True
    finally:
        await p.destroy(provisioned)
