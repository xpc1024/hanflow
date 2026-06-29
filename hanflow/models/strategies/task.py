"""Task strategy — map a task_type (reasoning/coding/vision) to a model (§4.3)."""

from __future__ import annotations

from typing import Any

from hanflow.models.strategies.base import ModelCandidate, RoutingRequest


class TaskStrategy:
    name = "task"

    def __init__(self, tasks: dict[str, tuple[str, str]]) -> None:
        self.tasks = tasks

    def candidates(
        self, request: RoutingRequest, providers: dict[str, Any]
    ) -> list[ModelCandidate]:
        if request.task_type is None or request.task_type not in self.tasks:
            return []
        provider, model = self.tasks[request.task_type]
        return [ModelCandidate(provider=provider, model=model, score=40.0, reason="task")]
