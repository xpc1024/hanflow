"""Code execution builtin — docker/firecracker/none sandbox (§5.3, §13.6).

Cycle 2026-W30-1.1.1 — adds optional ``exec_interface`` so DOCKER-provisioned
sandboxes can execute code in the container. Legacy ``mode="none"`` keeps the
old host-subprocess behaviour for backward compat. ``mode="docker"`` without
an injected ``exec_interface`` fails fast with a Phase-8-aligned message
(was Phase 7 before this cycle).
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any

from hanflow.core.errors import HanflowError
from hanflow.core.sandbox_contract import ExecInterface
from hanflow.tools.builtin.base import BuiltinMCPServer, ToolDescriptor


class CodeExecServer(BuiltinMCPServer):
    name = "code_exec"

    def __init__(
        self,
        workspace: str | Path,
        mode: str = "none",
        exec_interface: ExecInterface | None = None,
    ) -> None:
        """Initialize code_exec server.

        Args:
            workspace: host path where ``snippet.py`` is written before exec.
            mode: "none" (host exec, legacy default) / "docker" / "firecracker".
                Note: this is a *string* mode that historically did NOT match
                ``SandboxMode`` enum values ("local"/"docker"/"k8s"/"none").
                Kept as string for backward compat; new code should prefer
                injecting ``exec_interface`` from the provisioner.
            exec_interface: provisioner-injected execution interface (takes
                precedence over mode when provided). Set by the composition
                root (``build_sandbox``) when DOCKER mode is requested.
        """
        self.workspace = Path(workspace)
        self.mode = mode
        self._exec = exec_interface

    def tools(self) -> list[ToolDescriptor]:
        return [
            ToolDescriptor(
                name="run",
                server=self.name,
                description="execute code",
                input_schema={
                    "type": "object",
                    "properties": {
                        "language": {"type": "string"},
                        "code": {"type": "string"},
                        "timeout": {"type": "integer"},
                    },
                    "required": ["language", "code"],
                },
                annotations={"destructive": True},
            )
        ]

    async def call(self, tool: str, args: dict[str, Any]) -> Any:
        if tool != "run":
            raise HanflowError(f"unknown code_exec tool: {tool!r}")
        if args["language"] != "python":
            raise HanflowError(f"unsupported language: {args['language']!r}")
        timeout = args.get("timeout", 30)
        code = args["code"]

        # Preferred path: provisioner-injected exec interface (covers all modes).
        if self._exec is not None:
            snippet = self.workspace / "snippet.py"
            snippet.write_text(code, encoding="utf-8")
            # For host-exec backends, use sys.executable; for container backends
            # the image's python3 is correct. The exec interface is responsible
            # for locating the interpreter given the command list.
            interpreter = sys.executable if self.mode == "none" else "python3"
            return await self._exec.run(
                command=[interpreter, str(snippet)],
                timeout=timeout,
            )

        # Legacy fallback: mode="none" runs on host via asyncio subprocess.
        if self.mode == "none":
            return await self._exec_local(code, timeout)

        # mode=docker/firecracker/k8s without exec_interface: clear error.
        # Cycle 2026-W30-1.1.1: aligned wording from "Phase 7" to "Phase 8"
        # (DOCKER landed this cycle via runtime/build_sandbox wiring).
        raise HanflowError(
            f"code_exec mode {self.mode!r} requires a provisioned sandbox "
            f"(Phase 8 DOCKER landed in cycle 2026-W30-1.1.1; "
            f"wire via build_sandbox or pass exec_interface).",
        )

    async def _exec_local(self, code: str, timeout: int) -> dict[str, Any]:
        script = self.workspace / "snippet.py"
        script.write_text(code, encoding="utf-8")
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            str(script),
            cwd=str(self.workspace),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except TimeoutError:
            proc.kill()
            raise HanflowError(f"code execution timed out after {timeout}s") from None
        return {
            "stdout": stdout.decode(errors="replace"),
            "stderr": stderr.decode(errors="replace"),
            "returncode": proc.returncode,
        }
