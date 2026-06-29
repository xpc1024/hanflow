"""RoutingStrategy Protocol + request/candidate models (full version in Task 6)."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel

from hanflow.core.result import SensitivityLevel


class RoutingRequest(BaseModel):
    messages: list[Any]
    role: str | None = None
    task_type: str | None = None
    sensitivity: SensitivityLevel = "public"
    prefer: tuple[str, str] | None = None
    run_budget_remaining: float = 1.0


class ModelCandidate(BaseModel):
    provider: str
    model: str
    score: float
    reason: str


@runtime_checkable
class RoutingStrategy(Protocol):
    name: str

    def candidates(
        self, request: RoutingRequest, providers: dict[str, Any]
    ) -> list[ModelCandidate]: ...
