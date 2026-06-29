"""Web fetch builtin — fetch a URL and return markdown (§5.3)."""

from __future__ import annotations

import re
from typing import Any

from hanflow.core.errors import HanflowError
from hanflow.tools.builtin.base import BuiltinMCPServer, ToolDescriptor


class WebFetchServer(BuiltinMCPServer):
    name = "web_fetch"

    def tools(self) -> list[ToolDescriptor]:
        return [
            ToolDescriptor(
                name="fetch",
                server=self.name,
                description="fetch a URL as markdown",
                input_schema={
                    "type": "object",
                    "properties": {
                        "url": {"type": "string"},
                        "timeout": {"type": "integer"},
                    },
                    "required": ["url"],
                },
                annotations={},
            )
        ]

    async def _fetch(self, url: str, **kwargs: Any) -> str:
        import httpx

        async with httpx.AsyncClient(timeout=kwargs.get("timeout", 30)) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.text

    async def call(self, tool: str, args: dict[str, Any]) -> Any:
        if tool != "fetch":
            raise HanflowError(f"unknown web_fetch tool: {tool!r}")
        text = await self._fetch(args["url"], timeout=args.get("timeout", 30))
        # Minimal HTML→text; production uses a real parser (Phase 9 research).
        text = re.sub(r"<[^>]+>", "", text)
        return {"markdown": text, "url": args["url"]}
