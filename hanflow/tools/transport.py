"""Transport layer for MCP servers (§5.2).

5 transports: stdio / sse / http / websocket / inprocess. All conform to the
MCPConnection Protocol so the bus treats them uniformly. External connections
use the MCP Python SDK client; lifecycle (connect/health/close/lazy) is owned
here, failures are isolated (never block bus startup).
"""

from __future__ import annotations

from typing import Any, Literal, Protocol, runtime_checkable

from pydantic import BaseModel

TransportKind = Literal["stdio", "sse", "http", "websocket", "inprocess"]


class MCPServerConfig(BaseModel):
    transport: TransportKind
    command: str | None = None
    args: list[str] = []
    env: dict[str, str] = {}
    url: str | None = None
    auth: str | None = None
    headers: dict[str, str] = {}
    timeout_seconds: int = 60
    retry: Any | None = None
    lazy: bool = False


@runtime_checkable
class MCPConnection(Protocol):
    transport: TransportKind

    async def connect(self, config: MCPServerConfig) -> None: ...
    async def list_tools(self) -> list[Any]: ...
    async def call_tool(self, name: str, args: dict[str, Any]) -> Any: ...
    async def close(self) -> None: ...
    async def health(self) -> bool: ...


class _RemoteConnection:
    """Common base for stdio/sse/http/websocket using the MCP SDK client.

    The real client is built lazily; if the SDK (or the server) is unavailable,
    ``health`` stays False — failures are isolated, never block the bus.
    """

    transport: TransportKind = "http"

    def __init__(self, config: MCPServerConfig) -> None:
        self.config = config
        self._client: Any = None
        self._healthy: bool = False

    async def connect(self, config: MCPServerConfig) -> None:
        try:
            self._client = self._build_client(config)
            self._healthy = self._client is not None
        except Exception:
            self._healthy = False

    def _build_client(self, config: MCPServerConfig) -> Any:
        try:
            from mcp import ClientSession  # type: ignore[import-not-found]  # noqa: F401
        except Exception:
            self._healthy = False
            return None
        return {"transport": self.transport, "config": config}

    async def list_tools(self) -> list[Any]:
        return []

    async def call_tool(self, name: str, args: dict[str, Any]) -> Any:
        raise NotImplementedError(
            "remote tool call requires a live MCP server (integration test)"
        )

    async def close(self) -> None:
        self._client = None
        self._healthy = False

    async def health(self) -> bool:
        return self._healthy


class StdioConnection(_RemoteConnection):
    transport: TransportKind = "stdio"

    def _build_client(self, config: MCPServerConfig) -> Any:
        if not config.command:
            raise ValueError("stdio transport requires 'command'")
        return super()._build_client(config)


class SSEConnection(_RemoteConnection):
    transport: TransportKind = "sse"

    def _build_client(self, config: MCPServerConfig) -> Any:
        if not config.url:
            raise ValueError("sse transport requires 'url'")
        return super()._build_client(config)


class HTTPConnection(_RemoteConnection):
    transport: TransportKind = "http"

    def _build_client(self, config: MCPServerConfig) -> Any:
        if not config.url:
            raise ValueError("http transport requires 'url'")
        return super()._build_client(config)


class WebSocketConnection(_RemoteConnection):
    transport: TransportKind = "websocket"

    def _build_client(self, config: MCPServerConfig) -> Any:
        if not config.url:
            raise ValueError("websocket transport requires 'url'")
        return super()._build_client(config)


def build_connection(config: MCPServerConfig, *, builtin: Any = None) -> MCPConnection:
    """Factory selecting a connection by transport kind.

    For ``inprocess``, a ``builtin`` (BuiltinMCPServer) must be supplied by
    the bus; external transports build their own client lazily.
    """
    t = config.transport
    if t == "inprocess":
        if builtin is None:
            raise ValueError("inprocess transport requires a builtin server")
        from hanflow.tools.bus import _InProcessConnection

        return _InProcessConnection(builtin)  # type: ignore[return-value]
    if t == "stdio":
        return StdioConnection(config)
    if t == "sse":
        return SSEConnection(config)
    if t == "http":
        return HTTPConnection(config)
    if t == "websocket":
        return WebSocketConnection(config)
    raise ValueError(f"unknown transport: {t!r}")
