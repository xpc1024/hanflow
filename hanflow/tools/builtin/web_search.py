"""Web search builtin — multi-backend (Tavily/Bing/SerpAPI/self-hosted) (§5.3)."""

from __future__ import annotations

from typing import Any

from hanflow.core.errors import HanflowError
from hanflow.tools.builtin.base import BuiltinMCPServer, ToolDescriptor


class WebSearchServer(BuiltinMCPServer):
    name = "web_search"

    def __init__(self, backend: str = "tavily", api_key: str | None = None) -> None:
        self.backend = backend
        self.api_key = api_key

    def tools(self) -> list[ToolDescriptor]:
        return [
            ToolDescriptor(
                name="search",
                server=self.name,
                description="web search",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "max_results": {"type": "integer"},
                    },
                    "required": ["query"],
                },
                annotations={},
            )
        ]

    async def call(self, tool: str, args: dict[str, Any]) -> Any:
        if tool != "search":
            raise HanflowError(f"unknown web_search tool: {tool!r}")
        return await self._search(args["query"], args.get("max_results", 5))

    async def _search(self, query: str, max_results: int) -> list[dict[str, Any]]:
        # Backend-specific implementation wired in Phase 9 (Research atom) /
        # integration. Default: return empty (unit tests don't hit network).
        return []
