"""LocalProvisioner — host subprocess execution (LOCAL sandbox mode).

Cycle 2026-W30-1.1.1 — implements ``SandboxProvisioner`` (§13.6) for LOCAL mode.
There is no container; ``_LocalExec`` wraps ``asyncio.create_subprocess_exec``
to deliver the same ``ExecInterface`` contract that ``_DockerExec`` does for
DOCKER mode. Timeouts are wrapped internally as ``SandboxTimeoutError`` so
callers (e.g. ``code_exec``) never see bare ``TimeoutError`` (§5 no-swallow).
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from hanflow.core.errors import SandboxTimeoutError
from hanflow.core.sandbox_contract import (
    ProvisionedSandbox,
    RunSandbox,
    SandboxMode,
)


class _LocalExec:
    """Host subprocess execution (implements ExecInterface)."""

    def __init__(self, workspace_root: Path, run_id: str) -> None:
        self._ws = workspace_root
        self._run_id = run_id

    async def run(
        self,
        *,
        command: list[str],
        stdin: str | None = None,
        timeout: int = 30,
        cwd: str | None = None,
    ) -> dict[str, Any]:
        proc = await asyncio.create_subprocess_exec(
            *command,
            cwd=cwd or str(self._ws),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.PIPE if stdin is not None else None,
        )
        try:
            data = await asyncio.wait_for(
                proc.communicate(
                    stdin.encode() if stdin is not None else None,
                ),
                timeout=timeout,
            )
        except TimeoutError:
            proc.kill()
            # Internal wrap: callers see SandboxTimeoutError, not bare TimeoutError
            # (§5 no-swallow + §2.1 unified error hierarchy).
            raise SandboxTimeoutError(
                f"local exec timed out after {timeout}s",
                run_id=self._run_id,
                details={"command": command, "timeout": timeout},
            ) from None
        stdout, stderr = data
        return {
            "stdout": stdout.decode(errors="replace"),
            "stderr": stderr.decode(errors="replace"),
            "returncode": proc.returncode if proc.returncode is not None else 0,
        }


class LocalProvisioner:
    """Host execution provisioner (LOCAL mode). No container, no resources."""

    name = "local"

    async def provision(self, run_sandbox: RunSandbox) -> ProvisionedSandbox:
        # LOCAL and NONE both use host execution; the difference (context
        # isolation) is enforced elsewhere, not by the provisioner.
        if run_sandbox.mode not in (SandboxMode.LOCAL, SandboxMode.NONE):
            # Programmer error: build_sandbox should dispatch by mode.
            raise ValueError(
                f"LocalProvisioner requires SandboxMode.LOCAL or NONE, "
                f"got {run_sandbox.mode!r}"
            )
        return ProvisionedSandbox(
            run_id=run_sandbox.run_id,
            mode=run_sandbox.mode,  # preserve user-requested mode in provisioned artifact
            container_id=None,
            exec_interface=_LocalExec(run_sandbox.workspace_root, run_sandbox.run_id),
            workspace_root=run_sandbox.workspace_root,
        )

    async def destroy(self, provisioned: ProvisionedSandbox) -> None:
        # LOCAL has no OS resources to reclaim.
        return
