"""Anthropic ModelProvider — wraps the native anthropic SDK."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from typing import Any

from hanflow.core.errors import ModelTimeoutError
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
        """Stream chunks (§design §6 anthropic). Wraps SDK errors as ModelTimeoutError.

        Connection-phase failures keep ``retryable=True`` (class default);
        mid-flight failures set ``retryable=False`` on the raised instance.

        Anthropic streams via an async context manager yielding typed events:
        - ``message_start``: ``event.message.usage.input_tokens`` (cached)
        - ``content_block_delta`` with a ``text_delta``: ``delta.text``
        - ``message_delta``: ``usage.output_tokens`` (output accumulator) +
          ``delta.stop_reason``

        ``input_tokens`` lives ONLY on ``message_start``; ``message_delta.usage``
        carries only ``output_tokens``. We cache input_tokens and emit the
        complete TokenUsage on the terminal ``message_delta``.
        """
        from anthropic import AsyncAnthropic

        try:
            client = AsyncAnthropic(api_key=self.api_key)
            stream_ctx = client.messages.stream(
                model=model, messages=messages, max_tokens=kwargs.pop("max_tokens", 1024), **kwargs
            )
            input_tokens = 0
            async with stream_ctx as stream:
                try:
                    async for event in stream:
                        etype = getattr(event, "type", "")
                        if etype == "message_start":
                            msg = getattr(event, "message", None)
                            usage = getattr(msg, "usage", None) if msg else None
                            input_tokens = getattr(usage, "input_tokens", 0) if usage else 0
                        elif etype == "content_block_delta":
                            delta = getattr(event, "delta", None)
                            text = getattr(delta, "text", "") if delta else ""
                            yield StreamChunk(delta=text or "")
                        elif etype == "message_delta":
                            usage = getattr(event, "usage", None)
                            delta = getattr(event, "delta", None)
                            stop_reason = getattr(delta, "stop_reason", None) if delta else None
                            output_tokens = getattr(usage, "output_tokens", 0) if usage else 0
                            yield StreamChunk(
                                delta="",
                                usage=TokenUsage(
                                    input_tokens=input_tokens,
                                    output_tokens=output_tokens,
                                    total_tokens=input_tokens + output_tokens,
                                    cost_usd=self.estimate_cost(
                                        model,
                                        TokenUsage(
                                            input_tokens=input_tokens,
                                            output_tokens=output_tokens,
                                            total_tokens=0,
                                            cost_usd=0.0,
                                            latency_ms=0.0,
                                        ),
                                    ),
                                    latency_ms=0.0,
                                ),
                                finish_reason=stop_reason,
                            )
                except Exception as e:
                    err = ModelTimeoutError(f"anthropic stream mid-flight failed: {e}")
                    err.retryable = False  # retryable is a class attr; override on the instance
                    raise err from e
        except ModelTimeoutError:
            raise
        except Exception as e:
            raise ModelTimeoutError(f"anthropic stream connect failed: {e}") from e
