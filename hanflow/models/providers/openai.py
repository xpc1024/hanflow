"""OpenAI ModelProvider — wraps the native openai SDK (chat completions)."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from typing import Any

from hanflow.core.errors import ModelTimeoutError
from hanflow.models.providers.base import ModelResponse, StreamChunk, TokenUsage

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
        from openai import AsyncOpenAI

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

    async def stream(
        self, model: str, messages: list[Any], **kwargs: Any
    ) -> AsyncIterator[StreamChunk]:
        """Stream chunks (§design §6). Wraps SDK errors as ModelTimeoutError.

        Connection-phase failures keep ``retryable=True`` (class default);
        mid-flight failures set ``retryable=False`` on the raised instance.
        """
        from openai import AsyncOpenAI

        try:
            client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
            s = await client.chat.completions.create(
                model=model,
                messages=messages,
                stream=True,
                stream_options={"include_usage": True},
                **kwargs,
            )
        except Exception as e:
            raise ModelTimeoutError(f"openai stream connect failed: {e}") from e
        try:
            async for chunk in s:
                choices = getattr(chunk, "choices", None) or []
                delta = choices[0].delta.content if choices else ""
                usage = getattr(chunk, "usage", None)
                finish = choices[0].finish_reason if choices else None
                if usage:
                    yield StreamChunk(
                        delta=delta or "",
                        usage=TokenUsage(
                            input_tokens=getattr(usage, "prompt_tokens", 0),
                            output_tokens=getattr(usage, "completion_tokens", 0),
                            total_tokens=getattr(usage, "total_tokens", 0),
                            cost_usd=0.0,
                            latency_ms=0.0,
                        ),
                        finish_reason=finish,
                        raw=chunk.model_dump() if hasattr(chunk, "model_dump") else None,
                    )
                else:
                    yield StreamChunk(delta=delta or "", finish_reason=finish)
        except Exception as e:
            err = ModelTimeoutError(f"openai stream mid-flight failed: {e}")
            err.retryable = False  # P4b: retryable is a class attr; override on the instance
            raise err from e
