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


class TokenUsage(BaseModel):
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float
    latency_ms: float


class ModelResponse(BaseModel):
    content: str
    parsed: Any | None = None
    usage: TokenUsage
    model_used: str
    provider: str
    raw: dict[str, Any] | None = None


class StreamChunk(BaseModel):
    """One chunk of a streaming LLM response (§design StreamChunk).

    Intermediate chunks carry only ``delta``; the final chunk carries
    ``usage`` + ``finish_reason``.
    """

    delta: str = ""
    model_used: str = ""
    provider: str = ""
    usage: TokenUsage | None = None
    finish_reason: str | None = None
    raw: dict[str, Any] | None = None


@runtime_checkable
class ModelProvider(Protocol):
    name: str

    async def complete(self, model: str, messages: list[Any], **kwargs: Any) -> ModelResponse: ...

    async def stream(self, model: str, messages: list[Any], **kwargs: Any) -> AsyncIterator[StreamChunk]: ...

    def estimate_cost(self, model: str, usage: TokenUsage) -> float: ...

    def supported_models(self) -> list[str]: ...

    @property
    def is_local(self) -> bool: ...
