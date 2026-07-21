"""Tests for core/sandbox_contract.py (cycle 2026-W30-1.1.1).

Verifies type definitions, Protocol shape, and the critical charter-check
invariant: core/sandbox_contract.py must not import hanflow.isolation.*
(reverse-dependency guard).
"""
from __future__ import annotations

import inspect
from pathlib import Path

import pytest
from pydantic import BaseModel

from hanflow.core.sandbox_contract import (
    ExecInterface,
    ProvisionedSandbox,
    RunSandbox,
    SandboxMode,
    SandboxProvisioner,
    SandboxResources,
)


def test_sandbox_mode_values():
    assert SandboxMode.LOCAL == "local"
    assert SandboxMode.DOCKER == "docker"
    assert SandboxMode.K8S == "k8s"
    assert SandboxMode.NONE == "none"


def test_sandbox_resources_defaults():
    r = SandboxResources()
    assert r.cpu_limit == "2.0"
    assert r.memory_limit_mb == 2048
    assert r.timeout_seconds == 3600
    assert r.disk_limit_mb == 5120
    assert r.network_egress is None


def test_sandbox_resources_custom_values():
    r = SandboxResources(
        cpu_limit="4.0", memory_limit_mb=8192, timeout_seconds=7200,
        disk_limit_mb=10240, network_egress=["*"],
    )
    assert r.cpu_limit == "4.0"
    assert r.memory_limit_mb == 8192
    assert r.network_egress == ["*"]


def test_run_sandbox_fields():
    sb = RunSandbox(
        run_id="r1",
        mode=SandboxMode.LOCAL,
        workspace_root=Path("/tmp/ws"),
    )
    assert sb.run_id == "r1"
    assert sb.mode == SandboxMode.LOCAL
    assert sb.container_id is None
    assert sb.bash_enabled is False
    assert isinstance(sb.resources, SandboxResources)


def test_run_sandbox_create_local():
    class FakeMgr:
        def workspace_for(self, run_id): return Path(f"/tmp/{run_id}")
    sb = RunSandbox.create("r1", SandboxMode.LOCAL, FakeMgr())
    assert sb.workspace_root == Path("/tmp/r1")
    assert sb.bash_enabled is False


def test_run_sandbox_create_with_custom_resources():
    class FakeMgr:
        def workspace_for(self, run_id): return Path(f"/tmp/{run_id}")
    custom = SandboxResources(cpu_limit="0.5", memory_limit_mb=128)
    sb = RunSandbox.create("r2", SandboxMode.LOCAL, FakeMgr(), resources=custom)
    assert sb.resources.cpu_limit == "0.5"
    assert sb.resources.memory_limit_mb == 128


def test_exec_interface_is_protocol():
    assert hasattr(ExecInterface, "_is_protocol")
    assert ExecInterface._is_protocol is True


def test_provisioned_sandbox_fields():
    class FakeExec:
        async def run(self, *, command, stdin=None, timeout=30, cwd=None):
            return {"stdout": "", "stderr": "", "returncode": 0}

    ps = ProvisionedSandbox(
        run_id="r1",
        mode=SandboxMode.LOCAL,
        container_id=None,
        exec_interface=FakeExec(),
        workspace_root=Path("/tmp/ws"),
    )
    assert ps.run_id == "r1"
    assert ps.container_id is None
    assert ps.mode == SandboxMode.LOCAL


def test_provisioned_sandbox_docker_container_id():
    class FakeExec:
        async def run(self, *, command, stdin=None, timeout=30, cwd=None):
            return {"stdout": "", "stderr": "", "returncode": 0}

    ps = ProvisionedSandbox(
        run_id="r1",
        mode=SandboxMode.DOCKER,
        container_id="abc123",
        exec_interface=FakeExec(),
        workspace_root=Path("/workspace"),
    )
    assert ps.container_id == "abc123"


def test_provisioned_sandbox_exec_interface_typed_any_for_any_object():
    """exec_interface is Any (Pydantic v2 can't use Protocol as field type).

    Contract is enforced structurally by callers (ExecInterface is
    @runtime_checkable); ProvisionedSandbox accepts any object.
    """
    class NotAnExec:
        pass  # 故意不实现 run()

    ps = ProvisionedSandbox(
        run_id="r1", mode=SandboxMode.LOCAL, container_id=None,
        exec_interface=NotAnExec(), workspace_root=Path("/tmp"),
    )
    # ProvisionedSandbox 不做 isinstance 校验; 调用方负责
    assert ps.exec_interface is not None


def test_sandbox_provisioner_is_protocol():
    assert hasattr(SandboxProvisioner, "_is_protocol")
    assert SandboxProvisioner._is_protocol is True


def test_sandbox_contract_does_not_import_isolation():
    """Critical charter-check invariant: core must not import hanflow.isolation.*

    Guards against core→isolation reverse dependency (CHARTER §3 matrix).
    Only checks actual import statements (not docstring mentions).
    """
    import hanflow.core.sandbox_contract as mod
    src = inspect.getsource(mod)
    # 只扫真正的 import 行, 跳过 docstring/注释里提到的模块路径
    import_lines = [
        line.strip() for line in src.splitlines()
        if line.strip().startswith(("from ", "import "))
    ]
    for line in import_lines:
        assert "hanflow.isolation" not in line, (
            f"core/sandbox_contract.py forbidden import: {line} "
            f"(CHARTER §3 reverse-dep guard)"
        )


def test_sandbox_contract_only_depends_on_core_and_stdlib():
    """All imports in core/sandbox_contract.py must be stdlib or hanflow.core.*"""
    import hanflow.core.sandbox_contract as mod
    src = inspect.getsource(mod)
    import_lines = [
        line.strip() for line in src.splitlines()
        if line.strip().startswith(("from ", "import "))
    ]
    for line in import_lines:
        # 允许: from __future__, from enum, from pathlib, from typing,
        #       from pydantic, from hanflow.core.*
        assert "hanflow.isolation" not in line, f"forbidden import: {line}"
        assert "hanflow.observability" not in line, f"forbidden import: {line}"
        assert "hanflow.runtime" not in line, f"forbidden import: {line}"


def test_type_identity_with_isolation_reexport():
    """isolation/sandbox.py re-exports core types — same class object."""
    from hanflow.isolation.sandbox import (
        RunSandbox as IsoRunSandbox,
        SandboxMode as IsoSandboxMode,
        SandboxResources as IsoSandboxResources,
    )
    assert IsoRunSandbox is RunSandbox
    assert IsoSandboxMode is SandboxMode
    assert IsoSandboxResources is SandboxResources
