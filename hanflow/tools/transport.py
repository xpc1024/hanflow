"""Transport layer for MCP servers (full version in Task 2)."""

from __future__ import annotations

from typing import Any, Literal

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
