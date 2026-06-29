"""HTTP request builtin — generic REST client (§5.3)."""

from __future__ import annotations

from typing import Any

from hanflow.core.errors import HanflowError
from hanflow.tools.builtin.base import BuiltinMCPServer, ToolDescriptor


class HTTPRequestServer(BuiltinMCPServer):
    name = "http_request"

    def tools(self) -> list[ToolDescriptor]:
        return [
            ToolDescriptor(
                name="request",
                server=self.name,
                description="make an HTTP request",
                input_schema={
                    "type": "object",
                    "properties": {
                        "url": {"type": "string"},
                        "method": {"type": "string"},
                        "headers": {"type": "object"},
                        "json": {"type": "object"},
                        "params": {"type": "object"},
                    },
                    "required": ["url", "method"],
                },
                annotations={},
            )
        ]

    async def call(self, tool: str, args: dict[str, Any]) -> Any:
        import httpx

        if tool != "request":
            raise HanflowError(f"unknown http_request tool: {tool!r}")
        async with httpx.AsyncClient() as client:
            resp = await client.request(
                method=args["method"],
                url=args["url"],
                headers=args.get("headers"),
                json=args.get("json"),
                params=args.get("params"),
            )
        try:
            body: Any = resp.json()
        except Exception:
            body = resp.text
        return {"status": resp.status_code, "body": body, "headers": dict(resp.headers)}
