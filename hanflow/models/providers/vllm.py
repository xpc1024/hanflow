"""vLLM ModelProvider — openai-compatible, self-hosted (is_local=True)."""

from __future__ import annotations

from typing import Any

from hanflow.models.providers.openai import OpenAIProvider


class VLLMProvider(OpenAIProvider):
    """vLLM exposes an OpenAI-compatible API; reuse the OpenAI adapter."""

    name = "vllm"

    def __init__(self, base_url: str = "http://localhost:8000/v1", api_key: str = "EMPTY") -> None:
        super().__init__(api_key=api_key, base_url=base_url)

    @property
    def is_local(self) -> bool:
        return True

    def supported_models(self) -> list[str]:
        return []  # served models are discovered at runtime via /v1/models

    async def stream(self, model: str, messages: list[Any], **kwargs: Any):  # type: ignore[override]
        raise NotImplementedError("stream() for vllm lands in next cycle (2026-W30+)")
        yield  # pragma: no cover — satisfy async generator signature
