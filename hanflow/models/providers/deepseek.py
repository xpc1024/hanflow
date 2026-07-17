"""DeepSeek ModelProvider — openai-compatible API (is_local=False)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from hanflow.models.providers.base import StreamChunk
from hanflow.models.providers.openai import OpenAIProvider


class DeepSeekProvider(OpenAIProvider):
    """DeepSeek uses an OpenAI-compatible API; reuse the OpenAI adapter."""

    name = "deepseek"

    _DEEPSEEK_BASE = "https://api.deepseek.com"

    def __init__(self, api_key: str | None = None) -> None:
        super().__init__(api_key=api_key, base_url=self._DEEPSEEK_BASE)

    @property
    def is_local(self) -> bool:
        return False

    def supported_models(self) -> list[str]:
        return ["deepseek-chat", "deepseek-coder", "deepseek-reasoner"]

    async def stream(
        self, model: str, messages: list[Any], **kwargs: Any
    ) -> AsyncIterator[StreamChunk]:
        raise NotImplementedError("stream() for deepseek lands in next cycle (2026-W30+)")
        yield  # pragma: no cover — satisfy async generator signature
