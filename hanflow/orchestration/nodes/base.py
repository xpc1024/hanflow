"""NodeExecutor Protocol + shared types (§3.2).

NodeExecutors are the L2 layer; they read state, render templates, call an
executor's ``run()``, write results back. Protocol-based composition (not
inheritance) — users register custom executors via NodeExecutorRegistry.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from hanflow.core.dsl import NodeConfig, NodeType, WorkflowNode
from hanflow.core.result import AtomResult


@runtime_checkable
class NodeExecutor(Protocol):
    node_type: NodeType

    def validate_config(self, config: NodeConfig) -> None: ...
    async def run(
        self,
        ctx: Any,
        node: WorkflowNode,
        inputs: dict[str, Any],
    ) -> AtomResult: ...
