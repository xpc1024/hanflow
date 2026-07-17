"""Ollama ModelProvider — local/self-hosted, is_local=True (privacy-friendly)."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from typing import Any

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
        raise NotImplementedError("stream() for ollama lands in next cycle (2026-W30+)")
        yield  # pragma: no cover — satisfy async generator signature
