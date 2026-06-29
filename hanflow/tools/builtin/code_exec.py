"""Code execution builtin — docker/firecracker/none sandbox (§5.3, §13.6)."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any

from hanflow.core.errors import HanflowError
from hanflow.tools.builtin.base import BuiltinMCPServer, ToolDescriptor


class CodeExecServer(BuiltinMCPServer):
    name = "code_exec"

    def __init__(self, workspace: str | Path, mode: str = "none") -> None:
        self.workspace = Path(workspace)
        self.mode = mode  # none (dev) / docker / firecracker

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
        if self.mode == "none":
            return await self._exec_local(args["code"], args.get("timeout", 30))
        # docker / firecracker wired in Phase 7 (isolation)
        raise HanflowError(f"code_exec mode {self.mode!r} not yet implemented (Phase 7)")

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
