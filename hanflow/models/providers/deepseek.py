"""DeepSeek ModelProvider — openai-compatible API (is_local=False).

Streaming is inherited verbatim from :class:`OpenAIProvider` (DeepSeek's API is
OpenAI-compatible; the base adapter reads ``self.base_url`` which points at the
DeepSeek endpoint via ``__init__``).
"""

from __future__ import annotations

from typing import Any

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
