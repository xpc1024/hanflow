"""ModelProvider Protocol — per-vendor LLM adapter (§4.2).

Implementations wrap each vendor's native SDK (NOT LangChain LLM abstractions).
``is_local`` distinguishes local/self-hosted providers (ollama/vllm) — used by
the privacy strategy to route sensitive data. ``estimate_cost`` lets the
governance layer guard budgets.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel

# StreamChunk & TokenUsage are defined in ``hanflow.core.result`` so the core
# layer can reference streaming/usage types without a core → models dependency
# (CHARTER §3). They are re-exported here for back-compat with all existing
# ``from hanflow.models.providers.base import StreamChunk / TokenUsage`` sites.
from hanflow.core.result import StreamChunk, TokenUsage


class ModelResponse(BaseModel):
    content: str
    parsed: Any | None = None
    usage: TokenUsage
    model_used: str
    provider: str
    raw: dict[str, Any] | None = None


@runtime_checkable
class ModelProvider(Protocol):
    name: str

    async def complete(self, model: str, messages: list[Any], **kwargs: Any) -> ModelResponse: ...

    async def stream(
        self, model: str, messages: list[Any], **kwargs: Any
    ) -> AsyncIterator[StreamChunk]: ...

    def estimate_cost(self, model: str, usage: TokenUsage) -> float: ...

    def supported_models(self) -> list[str]: ...

    @property
    def is_local(self) -> bool: ...
