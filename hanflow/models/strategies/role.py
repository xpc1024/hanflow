"""Role strategy — map a role (planner/researcher/coder) to a model (§4.3)."""

from __future__ import annotations

from typing import Any

from hanflow.models.strategies.base import ModelCandidate, RoutingRequest


class RoleStrategy:
    name = "role"

    def __init__(self, roles: dict[str, tuple[str, str]]) -> None:
        self.roles = roles

    def candidates(
        self, request: RoutingRequest, providers: dict[str, Any]
    ) -> list[ModelCandidate]:
        if request.role is None or request.role not in self.roles:
            return []
        provider, model = self.roles[request.role]
        return [ModelCandidate(provider=provider, model=model, score=50.0, reason="role")]
