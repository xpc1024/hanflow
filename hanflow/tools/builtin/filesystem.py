"""Filesystem builtin server — read/write/list within a workspace jail (§5.3).

All paths are resolved relative to ``root`` and rejected if they escape it
(``..`` traversal). This is the DeerFlow-style shared run FS that sub-agents
operate on via their sandbox subdirs.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hanflow.core.errors import HanflowError
from hanflow.tools.builtin.base import BuiltinMCPServer, ToolDescriptor

_PATH_SCHEMA = {
    "type": "object",
    "properties": {"path": {"type": "string"}},
    "required": ["path"],
}


class FilesystemServer(BuiltinMCPServer):
    name = "filesystem"

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()

    def tools(self) -> list[ToolDescriptor]:
        return [
            ToolDescriptor(
                name="read",
                server=self.name,
                description="read a file",
                input_schema=_PATH_SCHEMA,
                annotations={},
            ),
            ToolDescriptor(
                name="write",
                server=self.name,
                description="write a file",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                    },
                    "required": ["path", "content"],
                },
                annotations={},
            ),
            ToolDescriptor(
                name="list",
                server=self.name,
                description="list a directory",
                input_schema=_PATH_SCHEMA,
                annotations={},
            ),
        ]

    def _resolve(self, rel: str) -> Path:
        p = (self.root / rel).resolve()
        try:
            p.relative_to(self.root)
        except ValueError as exc:
            raise HanflowError(f"path escapes workspace root: {rel!r}") from exc
        return p

    async def call(self, tool: str, args: dict[str, Any]) -> Any:
        if tool == "read":
            return self._resolve(args["path"]).read_text(encoding="utf-8")
        if tool == "write":
            p = self._resolve(args["path"])
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(args["content"], encoding="utf-8")
            return str(p.relative_to(self.root))
        if tool == "list":
            d = self._resolve(args["path"])
            return sorted(p.name for p in d.iterdir())
        raise HanflowError(f"unknown filesystem tool: {tool!r}")
