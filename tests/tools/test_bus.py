from typing import Any

import pytest

from hanflow.core.errors import HanflowError
from hanflow.tools.builtin.base import BuiltinMCPServer, ToolDescriptor
from hanflow.tools.bus import MCPBus
from tests.tools.conftest import EchoServer


@pytest.fixture
async def bus(trace):
    b = MCPBus(servers={}, trace=trace)
    b.register_builtin("echo", EchoServer())
    await b.start()
    yield b
    await b.stop()


@pytest.mark.asyncio
async def test_list_tools(bus):
    tools = await bus.list_tools()
    assert any(t.name == "say" and t.server == "echo" for t in tools)


@pytest.mark.asyncio
async def test_list_tools_filter_by_server(bus):
    tools = await bus.list_tools(server="echo")
    assert all(t.server == "echo" for t in tools)


@pytest.mark.asyncio
async def test_tool_call_full_name(bus):
    out = await bus.tool_call("echo.say", {"msg": "hi"})
    assert out.ok is True
    assert out.output == "hi"
    assert out.duration_ms >= 0


@pytest.mark.asyncio
async def test_tool_call_unknown_server_raises(bus):
    with pytest.raises(HanflowError):
        await bus.tool_call("ghost.tool", {})


@pytest.mark.asyncio
async def test_tool_call_invalid_args_validates(bus):
    with pytest.raises(HanflowError):
        await bus.tool_call("echo.say", {"msg": 123})  # wrong type


@pytest.mark.asyncio
async def test_tool_call_trace_span(bus, trace):
    await bus.tool_call("echo.say", {"msg": "hi"})
    assert any(s.name == "tool.call" for s in trace._buffer)


@pytest.mark.asyncio
async def test_destructive_tool_not_retried(trace):
    """A tool marked destructive should fail fast, not retry, on error."""

    class FailServer(BuiltinMCPServer):
        name = "fail"
        calls = 0

        def tools(self) -> list[ToolDescriptor]:
            return [
                ToolDescriptor(
                    name="rm",
                    server="fail",
                    description="d",
                    input_schema={"type": "object"},
                    annotations={"destructive": True},
                )
            ]

        async def call(self, tool: str, args: dict) -> Any:
            FailServer.calls += 1
            raise RuntimeError("boom")

    b = MCPBus(servers={}, trace=trace)
    b.register_builtin("fail", FailServer())
    await b.start()
    try:
        out = await b.tool_call("fail.rm", {})
        assert out.ok is False
        assert FailServer.calls == 1  # not retried
    finally:
        await b.stop()
