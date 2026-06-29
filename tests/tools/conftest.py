"""InProcessConnection fixture for bus tests."""

from __future__ import annotations

from typing import Any

import pytest

from hanflow.observability.trace import NullTraceExporter
from hanflow.tools.builtin.base import BuiltinMCPServer, ToolDescriptor


class EchoServer(BuiltinMCPServer):
    name = "echo"

    def tools(self) -> list[ToolDescriptor]:
        return [
            ToolDescriptor(
                name="say",
                server="echo",
                description="echoes input",
                input_schema={
                    "type": "object",
                    "properties": {"msg": {"type": "string"}},
                },
                annotations={},
            )
        ]

    async def call(self, tool: str, args: dict[str, Any]) -> Any:
        return args.get("msg")


@pytest.fixture
def trace():
    return NullTraceExporter()
