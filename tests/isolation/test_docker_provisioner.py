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

DOCKER_BASE_IMAGE = "python:3.11-slim"


def _docker_available() -> bool:
    """Probe docker CLI + running daemon + the base image being present locally.

    Daemon-reachable alone is insufficient: CI runners (e.g. GitHub Actions)
    expose a docker daemon but don't pre-pull ``python:3.11-slim``, so the
    provisioner's container create fails with ``[404] No such image``. Skip
    unless the image actually exists locally (mirrors what the provisioner
    needs to succeed).
    """
    if not shutil.which("docker"):
        return False
    try:
        info = subprocess.run(
            ["docker", "info", "--format", "{{.ServerVersion}}"],
            capture_output=True,
            timeout=5,
        )
        if info.returncode != 0 or not info.stdout.decode().strip():
            return False
        # Image must exist locally — create() does not auto-pull.
        img = subprocess.run(
            ["docker", "image", "inspect", DOCKER_BASE_IMAGE],
            capture_output=True,
            timeout=10,
        )
        return img.returncode == 0
    except Exception:
        return False


HAS_DOCKER = _docker_available()
skip_no_docker = pytest.mark.skipif(
    not HAS_DOCKER, reason=f"no docker daemon or {DOCKER_BASE_IMAGE} image"
)


class _FakeMgr:
    def workspace_for(self, run_id: str) -> Path:
        return Path(f"/tmp/{run_id}")


# ---------------------------------------------------------------------------
# _build_config — pure unit tests (no daemon needed)
# ---------------------------------------------------------------------------


def test_build_config_resource_mapping(tmp_path):
    """Resource fields map to Docker HostConfig fields correctly."""
    from hanflow.isolation.docker_provisioner import DockerProvisioner

    p = DockerProvisioner(base_image=DOCKER_BASE_IMAGE)
    sb = RunSandbox(
        run_id="r1",
        mode=SandboxMode.DOCKER,
        workspace_root=tmp_path,
        resources=SandboxResources(
            cpu_limit="2.0",
            memory_limit_mb=2048,
            timeout_seconds=3600,
            disk_limit_mb=5120,
            network_egress=None,
        ),
    )
    config = p._build_config(sb)

    assert config["Image"] == DOCKER_BASE_IMAGE
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
        run_id="r1",
        mode=SandboxMode.DOCKER,
        workspace_root=tmp_path,
        resources=SandboxResources(network_egress=["*"]),
    )
    config = p._build_config(sb)
    assert config["HostConfig"]["NetworkMode"] == "host"


def test_build_config_cpu_quota_fractional(tmp_path):
    """cpu_limit="0.5" → CpuQuota=50000."""
    from hanflow.isolation.docker_provisioner import DockerProvisioner

    p = DockerProvisioner()
    sb = RunSandbox(
        run_id="r1",
        mode=SandboxMode.DOCKER,
        workspace_root=tmp_path,
        resources=SandboxResources(cpu_limit="0.5"),
    )
    config = p._build_config(sb)
    assert config["HostConfig"]["CpuQuota"] == 50000


def test_build_config_no_storage_opt_when_disk_zero(tmp_path):
    """disk_limit_mb=0 → no StorageOpt (don't impose quota)."""
    from hanflow.isolation.docker_provisioner import DockerProvisioner

    p = DockerProvisioner()
    sb = RunSandbox(
        run_id="r1",
        mode=SandboxMode.DOCKER,
        workspace_root=tmp_path,
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
# storage-opt graceful degradation (mocked; no daemon needed)
# ---------------------------------------------------------------------------


class _FakeContainer:
    def __init__(self, cid: str = "c-fake") -> None:
        self.id = cid

    async def start(self) -> None:
        return None


class _FakeDockerClient:
    """Fake aiodocker client: first create raises a storage-opt DockerError,
    the second (after the provisioner drops StorageOpt) succeeds."""

    def __init__(self, fail_first: Exception | None) -> None:
        self._fail_first = fail_first
        self.calls: list[dict] = []

    @property
    def containers(self):
        outer = self

        class _Containers:
            async def create_or_replace(self, *, name, config):
                import copy

                outer.calls.append(copy.deepcopy(config))
                if outer._fail_first is not None:
                    # First call fails; subsequent calls succeed (retry path).
                    err = outer._fail_first
                    outer._fail_first = None
                    raise err
                return _FakeContainer()

        return _Containers()

    async def close(self) -> None:
        return None


@pytest.mark.asyncio
async def test_provision_drops_storage_opt_on_unsupported_daemon(monkeypatch):
    """Daemon rejects --storage-opt (e.g. overlay2/ext4 CI runners) → provisioner
    retries once without StorageOpt instead of failing."""
    from hanflow.isolation import docker_provisioner as dp_mod

    class _DockerError(Exception):
        pass

    storage_err = _DockerError(
        "[500] --storage-opt is supported only for overlay over xfs with 'pquota'"
    )
    client = _FakeDockerClient(fail_first=storage_err)

    class _FakeDocker:
        def __call__(self):
            return client

    fake_aiodocker = type("M", (), {"Docker": _FakeDocker(), "DockerError": _DockerError})
    monkeypatch.setitem(sys.modules, "aiodocker", fake_aiodocker)

    sb = RunSandbox(
        run_id="r-degrade",
        mode=SandboxMode.DOCKER,
        workspace_root=Path("."),
        resources=SandboxResources(disk_limit_mb=5120),  # non-zero → StorageOpt set
    )
    p = dp_mod.DockerProvisioner(base_image=DOCKER_BASE_IMAGE)
    provisioned = await p.provision(sb)

    assert provisioned.container_id == "c-fake"
    # First attempt carried StorageOpt; retry dropped it.
    assert len(client.calls) == 2
    assert client.calls[0]["HostConfig"]["StorageOpt"] == {"size": "5120m"}
    assert client.calls[1]["HostConfig"]["StorageOpt"] is None


@pytest.mark.asyncio
async def test_provision_no_retry_when_storage_opt_absent(monkeypatch):
    """No StorageOpt in config → a create error is NOT retried (nothing to drop)."""
    from hanflow.isolation import docker_provisioner as dp_mod

    class _DockerError(Exception):
        pass

    client = _FakeDockerClient(fail_first=_DockerError("[500] something else"))

    class _FakeDocker:
        def __call__(self):
            return client

    fake_aiodocker = type("M", (), {"Docker": _FakeDocker(), "DockerError": _DockerError})
    monkeypatch.setitem(sys.modules, "aiodocker", fake_aiodocker)

    sb = RunSandbox(
        run_id="r-noretry",
        mode=SandboxMode.DOCKER,
        workspace_root=Path("."),
        resources=SandboxResources(disk_limit_mb=0),  # zero → no StorageOpt
    )
    p = dp_mod.DockerProvisioner(base_image=DOCKER_BASE_IMAGE)
    from hanflow.core.errors import SandboxProvisionFailedError

    with pytest.raises(SandboxProvisionFailedError):
        await p.provision(sb)
    assert len(client.calls) == 1  # no retry


# ---------------------------------------------------------------------------
# Full lifecycle — only when daemon is reachable
# ---------------------------------------------------------------------------


@skip_no_docker
@pytest.mark.docker
@pytest.mark.asyncio
async def test_provision_real_container_lifecycle(tmp_path):
    """Contract: real container provision → exec → destroy."""
    from hanflow.isolation.docker_provisioner import DockerProvisioner

    sb = RunSandbox(
        run_id=f"hanflow-test-{tmp_path.name[:8]}",
        mode=SandboxMode.DOCKER,
        workspace_root=tmp_path,
        resources=SandboxResources(
            cpu_limit="1.0",
            memory_limit_mb=512,
            timeout_seconds=60,
        ),
    )
    p = DockerProvisioner(base_image=DOCKER_BASE_IMAGE)
    provisioned = await p.provision(sb)

    try:
        assert provisioned.container_id is not None
        assert provisioned.mode == SandboxMode.DOCKER
        assert str(provisioned.workspace_root) == "/workspace"

        result = await provisioned.exec_interface.run(
            command=["python3", "-c", "print('hello from docker')"],
            timeout=15,
        )
        assert result["returncode"] == 0
        assert "hello from docker" in result["stdout"]
    finally:
        await p.destroy(provisioned)


@skip_no_docker
@pytest.mark.docker
@pytest.mark.asyncio
async def test_provision_resource_limits_enforced(tmp_path):
    """Resource limits actually applied to the running container."""
    from hanflow.isolation.docker_provisioner import DockerProvisioner

    sb = RunSandbox(
        run_id=f"hanflow-rl-{tmp_path.name[:8]}",
        mode=SandboxMode.DOCKER,
        workspace_root=tmp_path,
        resources=SandboxResources(
            cpu_limit="1.5",
            memory_limit_mb=256,
            timeout_seconds=30,
        ),
    )
    p = DockerProvisioner(base_image=DOCKER_BASE_IMAGE)
    provisioned = await p.provision(sb)

    try:
        proc = await asyncio.create_subprocess_exec(
            "docker",
            "inspect",
            "--format",
            "{{.HostConfig.Memory}}",
            provisioned.container_id,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        # 256 MB = 268435456 bytes
        assert stdout.decode().strip() == "268435456"
    finally:
        await p.destroy(provisioned)


@skip_no_docker
@pytest.mark.docker
@pytest.mark.asyncio
async def test_destroy_removes_container(tmp_path):
    """After destroy, container no longer exists."""
    from hanflow.isolation.docker_provisioner import DockerProvisioner

    sb = RunSandbox(
        run_id=f"hanflow-dest-{tmp_path.name[:8]}",
        mode=SandboxMode.DOCKER,
        workspace_root=tmp_path,
        resources=SandboxResources(timeout_seconds=30),
    )
    p = DockerProvisioner(base_image=DOCKER_BASE_IMAGE)
    provisioned = await p.provision(sb)
    cid = provisioned.container_id
    assert cid is not None

    await p.destroy(provisioned)

    # Container should be gone
    proc = await asyncio.create_subprocess_exec(
        "docker",
        "inspect",
        "--format",
        "{{.Id}}",
        cid,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    await proc.communicate()
    assert proc.returncode != 0  # docker inspect fails on absent container


@skip_no_docker
@pytest.mark.docker
@pytest.mark.asyncio
async def test_exec_timeout_wrapped_as_sandbox_timeout(tmp_path):
    """_DockerExec.run wraps timeout internally as SandboxTimeoutError."""
    from hanflow.core.errors import SandboxTimeoutError
    from hanflow.isolation.docker_provisioner import DockerProvisioner

    sb = RunSandbox(
        run_id=f"hanflow-to-{tmp_path.name[:8]}",
        mode=SandboxMode.DOCKER,
        workspace_root=tmp_path,
        resources=SandboxResources(timeout_seconds=30),
    )
    p = DockerProvisioner(base_image=DOCKER_BASE_IMAGE)
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
