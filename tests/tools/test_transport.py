import pytest

from hanflow.tools.transport import MCPServerConfig, build_connection


def test_build_connection_inprocess_requires_builtin():
    cfg = MCPServerConfig(transport="inprocess")
    with pytest.raises(ValueError):
        build_connection(cfg)


def test_build_connection_stdio():
    cfg = MCPServerConfig(transport="stdio", command="echo", args=["hi"])
    conn = build_connection(cfg)
    assert conn.transport == "stdio"


def test_build_connection_http():
    cfg = MCPServerConfig(transport="http", url="https://example.invalid/mcp")
    conn = build_connection(cfg)
    assert conn.transport == "http"


def test_build_connection_sse():
    cfg = MCPServerConfig(transport="sse", url="http://x")
    conn = build_connection(cfg)
    assert conn.transport == "sse"


def test_build_connection_websocket():
    cfg = MCPServerConfig(transport="websocket", url="ws://x")
    conn = build_connection(cfg)
    assert conn.transport == "websocket"


@pytest.mark.asyncio
async def test_stdio_connection_health_false_when_command_missing():
    cfg = MCPServerConfig(transport="stdio", command="nonexistent-binary-xyz")
    conn = build_connection(cfg)
    # connect() isolates failures (no crash); health reflects state
    await conn.connect(cfg)
    assert await conn.health() is False
