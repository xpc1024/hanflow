"""Cost strategy — pick model by budget tier (§4.3)."""

from __future__ import annotations

from typing import Any

from hanflow.models.strategies.base import ModelCandidate, RoutingRequest


class CostStrategy:
    name = "cost"

    def __init__(self, tiers: list[dict[str, Any]]) -> None:
        # tiers sorted high→low budget_above; first matching tier wins
        self.tiers = sorted(tiers, key=lambda t: t["budget_above"], reverse=True)

    def candidates(
        self, request: RoutingRequest, providers: dict[str, Any]
    ) -> list[ModelCandidate]:
        for tier in self.tiers:
            if request.run_budget_remaining >= tier["budget_above"]:
                provider, model = tier["use"]
                return [ModelCandidate(provider=provider, model=model, score=30.0, reason="cost")]
        return []
