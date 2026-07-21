"""code_exec DOCKER path + mode vocab tests (cycle 2026-W30-1.1.1).

Verifies:
  - Legacy mode="none" still routes to _exec_local (backward compat).
  - When exec_interface is provided (provisioner-injected), it takes precedence
    over the mode string.
  - mode="docker" without exec_interface raises a clear error (Phase 8 aligned).
  - Unsupported language / unknown tool still raise HanflowError.
"""
from __future__ import annotations

import sys

import pytest

from hanflow.core.errors import HanflowError
from hanflow.tools.builtin.code_exec import CodeExecServer


@pytest.mark.asyncio
async def test_code_exec_none_mode_local_subprocess(tmp_path):
    """Legacy mode='none' → host subprocess (backward compat with pre-cycle)."""
    server = CodeExecServer(workspace=tmp_path, mode="none")
    result = await server.call(
        "run", {"language": "python", "code": "print('hello')"},
    )
    assert result["returncode"] == 0
    assert "hello" in result["stdout"]


@pytest.mark.asyncio
async def test_code_exec_with_exec_interface_takes_precedence(tmp_path):
    """When exec_interface is injected, it overrides mode string."""
    class _FakeExec:
        async def run(self, *, command, stdin=None, timeout=30, cwd=None):
            return {"stdout": "from fake exec", "stderr": "", "returncode": 0}

    server = CodeExecServer(
        workspace=tmp_path, mode="docker", exec_interface=_FakeExec(),
    )
    result = await server.call(
        "run", {"language": "python", "code": "print(1)"},
    )
    assert result["stdout"] == "from fake exec"


@pytest.mark.asyncio
async def test_code_exec_docker_without_exec_interface_raises_phase_8(tmp_path):
    """mode='docker' with no exec_interface → clear error mentioning Phase 8.

    Cycle 2026-W30-1.1.1 aligned the old 'Phase 7' wording to 'Phase 8' so the
    user knows DOCKER is now available via build_sandbox wiring.
    """
    server = CodeExecServer(workspace=tmp_path, mode="docker")
    with pytest.raises(HanflowError) as exc_info:
        await server.call("run", {"language": "python", "code": "print(1)"})
    msg = str(exc_info.value)
    assert "Phase 8" in msg or "provisioned sandbox" in msg


@pytest.mark.asyncio
async def test_code_exec_unsupported_language_raises(tmp_path):
    server = CodeExecServer(workspace=tmp_path, mode="none")
    with pytest.raises(HanflowError, match="language"):
        await server.call("run", {"language": "javascript", "code": "//"})


@pytest.mark.asyncio
async def test_code_exec_unknown_tool_raises(tmp_path):
    server = CodeExecServer(workspace=tmp_path, mode="none")
    with pytest.raises(HanflowError, match="code_exec tool"):
        await server.call("frobnicate", {})


@pytest.mark.asyncio
async def test_code_exec_real_subprocess_with_local_exec(tmp_path):
    """End-to-end: provisioner-injected _LocalExec actually runs Python."""
    from hanflow.isolation.local_provisioner import _LocalExec

    server = CodeExecServer(
        workspace=tmp_path, mode="none",
        exec_interface=_LocalExec(tmp_path, "r1"),
    )
    snippet_code = "import sys; print('via exec interface'); sys.exit(0)"
    result = await server.call("run", {"language": "python", "code": snippet_code})
    assert result["returncode"] == 0
    assert "via exec interface" in result["stdout"]


@pytest.mark.asyncio
async def test_code_exec_tools_descriptor_annotations(tmp_path):
    """Tool descriptor still marks run as destructive (unchanged)."""
    server = CodeExecServer(workspace=tmp_path, mode="none")
    tools = server.tools()
    assert len(tools) == 1
    assert tools[0].name == "run"
    assert tools[0].annotations.get("destructive") is True


@pytest.mark.asyncio
async def test_code_exec_timeout_propagates(tmp_path):
    """Timeout from exec_interface surfaces (would be SandboxTimeoutError in real use)."""
    from hanflow.core.errors import SandboxTimeoutError

    class _SlowExec:
        async def run(self, *, command, stdin=None, timeout=30, cwd=None):
            raise SandboxTimeoutError("slow", run_id="r1")

    server = CodeExecServer(
        workspace=tmp_path, mode="docker", exec_interface=_SlowExec(),
    )
    with pytest.raises(SandboxTimeoutError):
        await server.call(
            "run", {"language": "python", "code": "x", "timeout": 1},
        )
