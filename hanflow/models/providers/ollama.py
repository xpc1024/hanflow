"""Ollama ModelProvider — local/self-hosted, is_local=True (privacy-friendly)."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from typing import Any

from hanflow.core.errors import ModelTimeoutError
from hanflow.models.providers.base import ModelResponse, StreamChunk, TokenUsage


class OllamaProvider:
    name = "ollama"

    def __init__(self, base_url: str = "http://localhost:11434") -> None:
        self.base_url = base_url

    @property
    def is_local(self) -> bool:
        return True

    def supported_models(self) -> list[str]:
        return ["qwen2.5:32b", "qwen2.5:7b", "llama3.1:8b"]

    def estimate_cost(self, model: str, usage: TokenUsage) -> float:
        return 0.0  # local

    async def complete(self, model: str, messages: list[Any], **kwargs: Any) -> ModelResponse:
        import ollama

        client = ollama.AsyncClient(host=self.base_url)
        t0 = time.monotonic()
        resp = await client.chat(model=model, messages=messages, **kwargs)
        latency = (time.monotonic() - t0) * 1000
        in_tok = resp.get("prompt_eval_count", 0)
        out_tok = resp.get("eval_count", 0)
        return ModelResponse(
            content=resp["message"]["content"],
            usage=TokenUsage(
                input_tokens=in_tok,
                output_tokens=out_tok,
                total_tokens=in_tok + out_tok,
                cost_usd=0.0,
                latency_ms=latency,
            ),
            model_used=model,
            provider=self.name,
        )

    async def stream(
        self, model: str, messages: list[Any], **kwargs: Any
    ) -> AsyncIterator[StreamChunk]:
        """Stream chunks (§design §6 ollama). Wraps SDK errors as ModelTimeoutError.

        Connection-phase failures keep ``retryable=True`` (class default);
        mid-flight failures set ``retryable=False`` on the raised instance.
        Ollama's SDK returns an async iterator of dicts (not objects): each
        carries ``message.content``; the final dict carries ``done`` + usage
        (``prompt_eval_count`` / ``eval_count``) and ``done_reason``.
        """
        import ollama

        try:
            client = ollama.AsyncClient(host=self.base_url)
            resp = await client.chat(model=model, messages=messages, stream=True, **kwargs)
        except Exception as e:
            raise ModelTimeoutError(f"ollama stream connect failed: {e}") from e
        try:
            async for chunk in resp:
                message = chunk.get("message") or {}
                delta = message.get("content", "") or ""
                done = bool(chunk.get("done"))
                if done:
                    yield StreamChunk(
                        delta=delta,
                        usage=TokenUsage(
                            input_tokens=int(chunk.get("prompt_eval_count") or 0),
                            output_tokens=int(chunk.get("eval_count") or 0),
                            total_tokens=int(chunk.get("prompt_eval_count") or 0)
                            + int(chunk.get("eval_count") or 0),
                            cost_usd=0.0,
                            latency_ms=0.0,
                        ),
                        finish_reason=chunk.get("done_reason"),
                    )
                else:
                    yield StreamChunk(delta=delta)
        except Exception as e:
            err = ModelTimeoutError(f"ollama stream mid-flight failed: {e}")
            err.retryable = False  # retryable is a class attr; override on the instance
            raise err from e
