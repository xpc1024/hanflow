"""Fallback strategy — NOT a routing strategy; resilience chain used on failure (§4.3).

``candidates()`` returns [] — fallback only activates when the primary
provider fails, driven by ModelRouter._invoke_with_fallback().
"""

from __future__ import annotations

from typing import Any

from hanflow.models.strategies.base import ModelCandidate, RoutingRequest


class FallbackStrategy:
    name = "fallback"

    def __init__(self, chain: list[tuple[str, str]]) -> None:
        self.chain = [
            ModelCandidate(provider=p, model=m, score=0.0, reason="fallback") for p, m in chain
        ]

    def candidates(
        self, request: RoutingRequest, providers: dict[str, Any]
    ) -> list[ModelCandidate]:
        return []
