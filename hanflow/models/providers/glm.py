"""GLM (Zhipu) ModelProvider — wraps the native zhipuai SDK."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from typing import Any

from hanflow.core.errors import ModelTimeoutError
from hanflow.models.providers.base import ModelResponse, StreamChunk, TokenUsage

_PRICING = {
    "glm-4-plus": (0.005, 0.005),
    "glm-4-flash": (0.0001, 0.0001),
}


class GLMProvider:
    name = "glm"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key

    @property
    def is_local(self) -> bool:
        return False

    def supported_models(self) -> list[str]:
        return list(_PRICING.keys())

    def estimate_cost(self, model: str, usage: TokenUsage) -> float:
        in_p, out_p = _PRICING.get(model, (0.005, 0.005))
        return (usage.input_tokens / 1000) * in_p + (usage.output_tokens / 1000) * out_p

    async def complete(self, model: str, messages: list[Any], **kwargs: Any) -> ModelResponse:
        from zhipuai import ZhipuAI  # type: ignore[import-not-found]

        client = ZhipuAI(api_key=self.api_key)
        t0 = time.monotonic()
        resp = await client.chat.completions.create(model=model, messages=messages, **kwargs)
        latency = (time.monotonic() - t0) * 1000
        choice = resp.choices[0]
        usage = getattr(resp, "usage", None)
        in_tok = usage.prompt_tokens if usage else 0
        out_tok = usage.completion_tokens if usage else 0
        return ModelResponse(
            content=choice.message.content or "",
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
        """Stream chunks (§design §6 glm). Async direct iteration, no list().

        Connection-phase failures keep ``retryable=True`` (class default);
        mid-flight failures set ``retryable=False`` on the raised instance.
        """
        from zhipuai import ZhipuAI  # type: ignore[import-not-found]

        try:
            client = ZhipuAI(api_key=self.api_key)
            s = await client.chat.completions.create(
                model=model, messages=messages, stream=True, **kwargs
            )
        except Exception as e:
            raise ModelTimeoutError(f"glm stream connect failed: {e}") from e
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
                    )
                else:
                    yield StreamChunk(delta=delta or "", finish_reason=finish)
        except Exception as e:
            err = ModelTimeoutError(f"glm stream mid-flight failed: {e}")
            err.retryable = False  # P4b: retryable is a class attr; override on the instance
            raise err from e
