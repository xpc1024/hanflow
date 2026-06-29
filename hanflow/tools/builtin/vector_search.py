"""Vector search builtin — bridges the RetrievalProvider as a tool (§5.3).

Wired to a real RetrievalProvider in Phase 5. Until then ``search`` raises a
clear 'not configured' error.
"""

from __future__ import annotations

from typing import Any

from hanflow.core.errors import HanflowError
from hanflow.tools.builtin.base import BuiltinMCPServer, ToolDescriptor


class VectorSearchServer(BuiltinMCPServer):
    name = "vector_search"

    def __init__(self, provider: Any = None) -> None:
        self.provider = provider  # RetrievalProvider, injected in Phase 5/8

    def tools(self) -> list[ToolDescriptor]:
        return [
            ToolDescriptor(
                name="search",
                server=self.name,
                description="vector search a store",
                input_schema={
                    "type": "object",
                    "properties": {
                        "store": {"type": "string"},
                        "query": {"type": "string"},
                        "top_k": {"type": "integer"},
                    },
                    "required": ["store", "query"],
                },
                annotations={},
            )
        ]

    async def call(self, tool: str, args: dict[str, Any]) -> Any:
        if self.provider is None:
            raise HanflowError("vector_search provider not configured (wired in Phase 5)")
        if tool != "search":
            raise HanflowError(f"unknown vector_search tool: {tool!r}")
        chunks = await self.provider.search(
            args["store"], args["query"], top_k=args.get("top_k", 5)
        )
        return [c.model_dump(mode="json") for c in chunks]
