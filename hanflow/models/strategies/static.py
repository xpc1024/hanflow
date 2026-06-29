"""Static strategy — honor an explicit ``prefer=(provider, model)`` (§4.3)."""

from __future__ import annotations

from typing import Any

from hanflow.models.strategies.base import ModelCandidate, RoutingRequest


class StaticStrategy:
    name = "static"

    def candidates(
        self, request: RoutingRequest, providers: dict[str, Any]
    ) -> list[ModelCandidate]:
        if request.prefer is None:
            return []
        provider, model = request.prefer
        return [ModelCandidate(provider=provider, model=model, score=100.0, reason="static")]
