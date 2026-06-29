"""BuiltinMCPServer Protocol + ToolDescriptor + InProcessConnection.

Builtin servers run in-process (zero overhead) but expose the same
list_tools/call_tool semantics as external MCP servers. The bus wraps them in
an ``InProcessConnection`` so transport differences are hidden.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel


class ToolDescriptor(BaseModel):
    name: str
    server: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any] | None = None
    annotations: dict[str, Any] = {}


@runtime_checkable
class BuiltinMCPServer(Protocol):
    name: str

    def tools(self) -> list[ToolDescriptor]: ...

    async def call(self, tool: str, args: dict[str, Any]) -> Any: ...
