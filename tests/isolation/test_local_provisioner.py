"""Tests for LocalProvisioner + _LocalExec (cycle 2026-W30-1.1.1).

Covers:
  - LocalProvisioner.provision returns ProvisionedSandbox with LOCAL mode
  - Wrong mode raises ValueError (programmer error, not a SandboxError)
  - LocalProvisioner.destroy is a no-op (no resources to reclaim)
  - _LocalExec.run launches host subprocess, returns {stdout, stderr, returncode}
  - _LocalExec.run wraps asyncio.TimeoutError internally as SandboxTimeoutError
  - nonzero returncode propagates (not raised, returned in dict)
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

from hanflow.core.errors import SandboxTimeoutError
from hanflow.core.sandbox_contract import RunSandbox, SandboxMode
from hanflow.isolation.local_provisioner import LocalProvisioner, _LocalExec


class _FakeMgr:
    def workspace_for(self, run_id: str) -> Path:
        return Path(f"/tmp/{run_id}")


@pytest.mark.asyncio
async def test_local_provisioner_provision_returns_provisioned_sandbox():
    sb = RunSandbox.create("r1", SandboxMode.LOCAL, _FakeMgr())
    p = LocalProvisioner()
    provisioned = await p.provision(sb)

    assert provisioned.run_id == "r1"
    assert provisioned.mode == SandboxMode.LOCAL
    assert provisioned.container_id is None
    assert isinstance(provisioned.exec_interface, _LocalExec)


@pytest.mark.asyncio
async def test_local_provisioner_provision_wrong_mode_raises_value_error():
    """Wrong-mode is a programmer error → stdlib ValueError (not §2.1 territory)."""
    sb = RunSandbox.create("r1", SandboxMode.DOCKER, _FakeMgr())
    p = LocalProvisioner()
    with pytest.raises(ValueError, match="LocalProvisioner"):
        await p.provision(sb)


@pytest.mark.asyncio
async def test_local_provisioner_destroy_is_noop():
    p = LocalProvisioner()
    sb = RunSandbox.create("r1", SandboxMode.LOCAL, _FakeMgr())
    provisioned = await p.provision(sb)
    # should not raise
    await p.destroy(provisioned)


@pytest.mark.asyncio
async def test_local_provisioner_name():
    assert LocalProvisioner.name == "local"


@pytest.mark.asyncio
async def test_local_exec_run_python_hello_world(tmp_path):
    exec_ = _LocalExec(tmp_path, "r1")
    snippet = tmp_path / "snippet.py"
    snippet.write_text("print('hello from local')", encoding="utf-8")

    result = await exec_.run(command=[sys.executable, str(snippet)], timeout=10)

    assert result["returncode"] == 0
    assert "hello from local" in result["stdout"]
    assert result["stderr"] == ""


@pytest.mark.asyncio
async def test_local_exec_run_timeout_raises_sandbox_timeout(tmp_path):
    """TimeoutError wrapped internally as SandboxTimeoutError (§5 no-swallow)."""
    exec_ = _LocalExec(tmp_path, "r1")
    snippet = tmp_path / "loop.py"
    snippet.write_text("import time; time.sleep(10)", encoding="utf-8")

    with pytest.raises(SandboxTimeoutError) as exc_info:
        await exec_.run(command=[sys.executable, str(snippet)], timeout=1)

    assert exc_info.value.code == "SANDBOX_TIMEOUT"
    assert exc_info.value.retryable is True
    assert exc_info.value.run_id == "r1"
    assert "1s" in str(exc_info.value)


@pytest.mark.asyncio
async def test_local_exec_run_nonzero_returncode(tmp_path):
    """Nonzero returncode is NOT raised — returned in dict (matches _exec_local)."""
    exec_ = _LocalExec(tmp_path, "r1")
    snippet = tmp_path / "fail.py"
    snippet.write_text("import sys; sys.exit(2)", encoding="utf-8")

    result = await exec_.run(command=[sys.executable, str(snippet)], timeout=5)

    assert result["returncode"] == 2


@pytest.mark.asyncio
async def test_local_exec_run_with_stdin(tmp_path):
    """stdin is encoded + piped to subprocess."""
    exec_ = _LocalExec(tmp_path, "r1")
    snippet = tmp_path / "echo.py"
    snippet.write_text(
        "data = input(); print(f'got: {data}')", encoding="utf-8",
    )

    result = await exec_.run(
        command=[sys.executable, str(snippet)], stdin="hello", timeout=5,
    )

    assert result["returncode"] == 0
    assert "got: hello" in result["stdout"]


@pytest.mark.asyncio
async def test_local_exec_run_with_cwd(tmp_path):
    """cwd overrides workspace_root as subprocess working directory."""
    subdir = tmp_path / "sub"
    subdir.mkdir()
    exec_ = _LocalExec(tmp_path, "r1")
    snippet = tmp_path / "snippet.py"
    snippet.write_text(
        "import os; print(os.getcwd())", encoding="utf-8",
    )

    result = await exec_.run(
        command=[sys.executable, str(snippet)], cwd=str(subdir), timeout=5,
    )

    assert result["returncode"] == 0
    # cwd 生效: 打印的是 subdir 而非 workspace_root
    assert str(subdir) in result["stdout"]
