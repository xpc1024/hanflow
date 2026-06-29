"""MCPBus — the single gateway for all tool calls (§5.1).

Flow: resolve ``server.tool`` → route to connection → validate args via the
tool's input_schema → per-server rate limit → trace span → call → on failure
retry UNLESS the tool is annotated destructive.
"""

from __future__ import annotations

import time
from typing import Any, cast

import jsonschema
from pydantic import BaseModel

from hanflow.core.errors import HanflowError, ToolTimeoutError
from hanflow.observability.trace import TraceExporter
from hanflow.tools.builtin.base import BuiltinMCPServer, ToolDescriptor
from hanflow.tools.transport import MCPServerConfig


class ToolCallResult(BaseModel):
    ok: bool
    output: Any
    error: str | None = None
    duration_ms: float


class _InProcessConnection:
    """Wraps a BuiltinMCPServer so the bus can treat it like any connection."""

    transport = "inprocess"

    def __init__(self, server: BuiltinMCPServer) -> None:
        self.server = server

    async def connect(self, config: MCPServerConfig) -> None:
        return None

    async def list_tools(self) -> list[ToolDescriptor]:
        return self.server.tools()

    async def call_tool(self, name: str, args: dict[str, Any]) -> Any:
        return await self.server.call(name, args)

    async def close(self) -> None:
        return None

    async def health(self) -> bool:
        return True


class MCPBus:
    def __init__(
        self,
        servers: dict[str, MCPServerConfig],
        trace: TraceExporter,
        *,
        rate_limit_rpm: int = 0,
    ) -> None:
        self.trace = trace
        self.rate_limit_rpm = rate_limit_rpm
        self._server_configs: dict[str, MCPServerConfig] = dict(servers)
        self._builtin: dict[str, _InProcessConnection] = {}
        self._external: dict[str, Any] = {}  # filled by real transports (Task 2)
        self._calls: dict[str, list[float]] = {}

    def register_builtin(self, name: str, server: BuiltinMCPServer) -> None:
        self._builtin[name] = _InProcessConnection(server)
        self._server_configs.setdefault(name, MCPServerConfig(transport="inprocess"))

    async def start(self) -> None:
        # InProcess connections are ready immediately; external ones connect here
        # (Task 2 wires real stdio/http connections with retry + lazy).
        return None

    async def stop(self) -> None:
        for conn in list(self._builtin.values()):
            await conn.close()
        self._builtin.clear()

    # --- list / call ------------------------------------------------------- #
    async def list_tools(self, server: str | None = None) -> list[ToolDescriptor]:
        out: list[ToolDescriptor] = []
        targets = [server] if server else list(self._builtin.keys()) + list(self._external.keys())
        for name in targets:
            conn = self._get_connection(name)
            if conn is None:
                continue
            for t in await conn.list_tools():
                out.append(t)
        return out

    async def tool_call(
        self, name: str, args: dict[str, Any], *, timeout_seconds: int = 60
    ) -> ToolCallResult:
        server_name, tool_name = self._split(name)
        conn = self._get_connection(server_name)
        if conn is None:
            raise HanflowError(f"unknown tool server: {server_name!r}", details={"tool": name})
        descriptor = await self._find_tool(conn, tool_name)
        if descriptor is None:
            raise HanflowError(f"unknown tool {tool_name!r} on server {server_name!r}")
        self._validate_args(descriptor, args)
        self._check_rate_limit(server_name)
        destructive = bool(descriptor.annotations.get("destructive"))

        async with self.trace.span("tool.call", kind="tool", tool=name):
            t0 = time.monotonic()
            try:
                out = await conn.call_tool(tool_name, args)
                return ToolCallResult(
                    ok=True, output=out, duration_ms=(time.monotonic() - t0) * 1000
                )
            except HanflowError:
                raise
            except Exception as exc:
                if destructive:
                    return ToolCallResult(
                        ok=False,
                        output=None,
                        error=str(exc),
                        duration_ms=(time.monotonic() - t0) * 1000,
                    )
                # non-destructive: one retry (full backoff in Phase 8 wrapper)
                try:
                    out = await conn.call_tool(tool_name, args)
                    return ToolCallResult(
                        ok=True, output=out, duration_ms=(time.monotonic() - t0) * 1000
                    )
                except Exception as exc2:
                    return ToolCallResult(
                        ok=False,
                        output=None,
                        error=str(exc2),
                        duration_ms=(time.monotonic() - t0) * 1000,
                    )

    # --- helpers ----------------------------------------------------------- #
    def _split(self, full_name: str) -> tuple[str, str]:
        if "." not in full_name:
            raise HanflowError(f"tool name must be 'server.tool', got {full_name!r}")
        server, tool = full_name.split(".", 1)
        return server, tool

    def _get_connection(self, server: str) -> Any:
        if server in self._builtin:
            return self._builtin[server]
        return self._external.get(server)

    async def _find_tool(self, conn: Any, tool_name: str) -> ToolDescriptor | None:
        for t in await conn.list_tools():
            if t.name == tool_name:
                return cast(ToolDescriptor, t)
        return None

    def _validate_args(self, descriptor: ToolDescriptor, args: dict[str, Any]) -> None:
        schema = descriptor.input_schema
        if not schema:
            return
        try:
            jsonschema.validate(args, schema)
        except jsonschema.ValidationError as exc:
            raise HanflowError(
                f"invalid args for {descriptor.server}.{descriptor.name}: {exc.message}",
                details={
                    "tool": f"{descriptor.server}.{descriptor.name}",
                    "path": list(exc.path),
                },
            ) from exc

    def _check_rate_limit(self, server: str) -> None:
        if self.rate_limit_rpm <= 0:
            return
        now = time.monotonic()
        window = self._calls.setdefault(server, [])
        window[:] = [x for x in window if now - x < 60.0]
        if len(window) >= self.rate_limit_rpm:
            raise ToolTimeoutError(f"rate limit exceeded for tool server {server!r}")
        window.append(now)
