"""FakeProvider fixture for router tests (no network)."""

from __future__ import annotations

from typing import Any

import pytest

from hanflow.models.providers.base import ModelResponse, TokenUsage
from hanflow.observability.trace import NullTraceExporter


class FakeProvider:
    """Records calls; returns a canned ModelResponse."""

    def __init__(
        self, name: str, *, is_local: bool = False, models: list[str] | None = None
    ) -> None:
        self.name = name
        self._is_local = is_local
        self.supported = models or ["m1"]
        self.calls: list[tuple[str, list]] = []
        self.fail_with: Any = None

    @property
    def is_local(self) -> bool:
        return self._is_local

    async def complete(self, model: str, messages: list, **kwargs: Any) -> ModelResponse:
        if self.fail_with is not None:
            raise self.fail_with
        self.calls.append((model, messages))
        return ModelResponse(
            content=f"[{self.name}/{model}] ok",
            usage=TokenUsage(
                input_tokens=1, output_tokens=1, total_tokens=2, cost_usd=0.001, latency_ms=10
            ),
            model_used=model,
            provider=self.name,
        )

    def estimate_cost(self, model: str, usage: TokenUsage) -> float:
        return 0.001

    def supported_models(self) -> list[str]:
        return list(self.supported)


@pytest.fixture
def fake_providers():
    return {
        "cloud": FakeProvider("cloud", is_local=False, models=["strong", "fast"]),
        "local": FakeProvider("local", is_local=True, models=["local-m"]),
    }


@pytest.fixture
def null_trace():
    return NullTraceExporter()
