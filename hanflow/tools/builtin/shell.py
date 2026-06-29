"""Shell builtin server — runs commands in a workspace (§5.3, §13.6).

``enabled=False`` by default in LOCAL sandbox mode (not a security boundary);
DOCKER/K8s modes enable it. Output is captured stdout/stderr + exit code.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from hanflow.core.errors import HanflowError
from hanflow.tools.builtin.base import BuiltinMCPServer, ToolDescriptor


class ShellServer(BuiltinMCPServer):
    name = "shell"

    def __init__(
        self, workspace: str | Path, enabled: bool = False, timeout_seconds: int = 60
    ) -> None:
        self.workspace = Path(workspace)
        self.enabled = enabled
        self.timeout_seconds = timeout_seconds

    def tools(self) -> list[ToolDescriptor]:
        return [
            ToolDescriptor(
                name="run",
                server=self.name,
                description="run a shell command",
                input_schema={
                    "type": "object",
                    "properties": {
                        "cmd": {"type": "string"},
                        "timeout": {"type": "integer"},
                    },
                    "required": ["cmd"],
                },
                annotations={"destructive": True},
            )
        ]

    async def call(self, tool: str, args: dict[str, Any]) -> Any:
        if not self.enabled:
            raise HanflowError("shell is disabled in this sandbox mode")
        if tool != "run":
            raise HanflowError(f"unknown shell tool: {tool!r}")
        timeout = args.get("timeout", self.timeout_seconds)
        proc = await asyncio.create_subprocess_shell(
            args["cmd"],
            cwd=str(self.workspace),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except TimeoutError as exc:
            proc.kill()
            raise HanflowError(f"shell command timed out after {timeout}s") from exc
        return {
            "stdout": stdout.decode(errors="replace"),
            "stderr": stderr.decode(errors="replace"),
            "returncode": proc.returncode,
        }
