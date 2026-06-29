"""NodeExecutorRegistry — registers the 13 primitive executors (§3.2).

``default()`` registers all executors that are currently implemented. Custom
executors can be registered via ``register()``. Unknown types raise on lookup.
"""

from __future__ import annotations

from typing import Any

from hanflow.core.dsl import NodeType
from hanflow.core.errors import CompileError


class NodeExecutorRegistry:
    def __init__(self) -> None:
        self._executors: dict[str, Any] = {}

    def register(self, executor: Any) -> None:
        self._executors[executor.node_type] = executor

    def get(self, node_type: NodeType) -> Any:
        if node_type not in self._executors:
            raise CompileError(
                f"no executor registered for node type {node_type!r}",
                details={"node_type": node_type},
            )
        return self._executors[node_type]

    def all_types(self) -> list[str]:
        return list(self._executors.keys())

    @classmethod
    def default(cls) -> NodeExecutorRegistry:
        """Register every implemented executor.

        Late imports keep registration tolerant of partial implementations
        during the build (each Phase 8 task adds one).
        """
        registry = cls()
        from hanflow.orchestration.nodes.control import (
            BranchExecutor,
            HITLExecutor,
            LoopExecutor,
            ParallelExecutor,
            SequentialExecutor,
        )

        # Coordinator is registered separately (it imports lazily to avoid
        # pulling planner/aggregator deps at module import time).
        from hanflow.orchestration.nodes.coordinator import CoordinatorExecutor
        from hanflow.orchestration.nodes.knowledge import KnowledgeExecutor
        from hanflow.orchestration.nodes.leaf import (
            ExecutionExecutor,
            LLMExecutor,
            ResearchExecutor,
            ToolExecutor,
        )
        from hanflow.orchestration.nodes.state_ops import (
            MemoryExecutor,
            SubworkflowExecutor,
        )

        for exe in (
            SequentialExecutor(),
            ParallelExecutor(),
            LoopExecutor(),
            BranchExecutor(),
            HITLExecutor(),
            LLMExecutor(),
            ToolExecutor(),
            ResearchExecutor(),
            ExecutionExecutor(),
            CoordinatorExecutor(),
            MemoryExecutor(),
            SubworkflowExecutor(),
            KnowledgeExecutor(),
        ):
            registry.register(exe)
        return registry
