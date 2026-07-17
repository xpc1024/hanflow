"""Anthropic ModelProvider — wraps the native anthropic SDK."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from typing import Any

from hanflow.models.providers.base import ModelResponse, StreamChunk, TokenUsage

_PRICING = {
    "claude-3-5-sonnet": (0.003, 0.015),
    "claude-3-opus": (0.015, 0.075),
    "claude-3-haiku": (0.00025, 0.00125),
}


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key

    @property
    def is_local(self) -> bool:
        return False

    def supported_models(self) -> list[str]:
        return list(_PRICING.keys())

    def estimate_cost(self, model: str, usage: TokenUsage) -> float:
        in_p, out_p = _PRICING.get(model, (0.003, 0.015))
        return (usage.input_tokens / 1000) * in_p + (usage.output_tokens / 1000) * out_p

    async def complete(self, model: str, messages: list[Any], **kwargs: Any) -> ModelResponse:
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=self.api_key)
        t0 = time.monotonic()
        resp = await client.messages.create(
            model=model, messages=messages, max_tokens=kwargs.pop("max_tokens", 1024), **kwargs
        )
        latency = (time.monotonic() - t0) * 1000
        content = "".join(b.text for b in resp.content if hasattr(b, "text"))
        usage = resp.usage
        in_tok = usage.input_tokens if usage else 0
        out_tok = usage.output_tokens if usage else 0
        return ModelResponse(
            content=content,
            usage=TokenUsage(
                input_tokens=in_tok,
                output_tokens=out_tok,
                total_tokens=in_tok + out_tok,
                cost_usd=self.estimate_cost(
                    model,
                    TokenUsage(
                        input_tokens=in_tok,
                        output_tokens=out_tok,
                        total_tokens=0,
                        cost_usd=0.0,
                        latency_ms=latency,
                    ),
                ),
                latency_ms=latency,
            ),
            model_used=model,
            provider=self.name,
        )

    async def stream(
        self, model: str, messages: list[Any], **kwargs: Any
    ) -> AsyncIterator[StreamChunk]:
        raise NotImplementedError("stream() for anthropic lands in next cycle (2026-W30+)")
        yield  # pragma: no cover — satisfy async generator signature
