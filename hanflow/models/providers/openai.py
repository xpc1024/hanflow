"""OpenAI ModelProvider — wraps the native openai SDK (chat completions)."""

from __future__ import annotations

import time
from typing import Any

from hanflow.models.providers.base import ModelResponse, TokenUsage

_PRICING = {  # per 1K tokens, USD — kept conservative; override via config in prod
    "gpt-4o": (0.005, 0.015),
    "gpt-4o-mini": (0.00015, 0.0006),
}


class OpenAIProvider:
    name = "openai"

    def __init__(self, api_key: str | None = None, base_url: str | None = None) -> None:
        self.api_key = api_key
        self.base_url = base_url

    @property
    def is_local(self) -> bool:
        return False

    def supported_models(self) -> list[str]:
        return list(_PRICING.keys())

    def estimate_cost(self, model: str, usage: TokenUsage) -> float:
        in_p, out_p = _PRICING.get(model, (0.005, 0.015))
        return (usage.input_tokens / 1000) * in_p + (usage.output_tokens / 1000) * out_p

    async def complete(self, model: str, messages: list[Any], **kwargs: Any) -> ModelResponse:
        from openai import AsyncOpenAI  # type: ignore[import-not-found]

        client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        t0 = time.monotonic()
        resp = await client.chat.completions.create(model=model, messages=messages, **kwargs)
        latency = (time.monotonic() - t0) * 1000
        choice = resp.choices[0]
        usage = resp.usage
        in_tok = usage.prompt_tokens if usage else 0
        out_tok = usage.completion_tokens if usage else 0
        return ModelResponse(
            content=choice.message.content or "",
            usage=TokenUsage(
                input_tokens=in_tok,
                output_tokens=out_tok,
                total_tokens=usage.total_tokens if usage else 0,
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
            raw=resp.model_dump() if hasattr(resp, "model_dump") else None,
        )
