"""FakeProvider — in-memory provider for tests and dry-run mode.

Records calls and returns canned responses; optionally streams tokens and/or
simulates failures. Drop-in for ModelProvider in unit tests across phases.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from hanflow.core.errors import HanflowError
from hanflow.models.providers.base import ModelResponse, TokenUsage


class FakeProvider:
    def __init__(
        self,
        name: str,
        *,
        is_local: bool = False,
        models: list[str] | None = None,
        responses: dict[str, str] | None = None,
        stream_tokens: list[str] | None = None,
        fail_with: HanflowError | None = None,
    ) -> None:
        self.name = name
        self._is_local = is_local
        self._models = models or ["m1"]
        self.responses = responses or {}
        self.stream_tokens = stream_tokens
        self.fail_with = fail_with
        self.calls: list[tuple[str, list[Any]]] = []

    @property
    def is_local(self) -> bool:
        return self._is_local

    def supported_models(self) -> list[str]:
        return list(self._models)

    def estimate_cost(self, model: str, usage: TokenUsage) -> float:
        return usage.cost_usd

    async def complete(self, model: str, messages: list[Any], **kwargs: Any) -> ModelResponse:
        if self.fail_with is not None:
            raise self.fail_with
        self.calls.append((model, messages))
        content = self.responses.get(model, f"[{self.name}/{model}] ok")
        return ModelResponse(
            content=content,
            usage=TokenUsage(
                input_tokens=1, output_tokens=1, total_tokens=2, cost_usd=0.001, latency_ms=5
            ),
            model_used=model,
            provider=self.name,
        )

    async def stream(self, model: str, messages: list[Any], **kwargs: Any) -> AsyncIterator[str]:
        if self.fail_with is not None:
            raise self.fail_with
        for tok in self.stream_tokens or []:
            yield tok
