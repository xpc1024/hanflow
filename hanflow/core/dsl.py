"""WorkflowDSL — the single source of truth for workflow definitions.

YAML <-> Pydantic bidirectional. CLI / Web / Compiler all depend on this.
The TS types of Web Studio are generated from it.

Compile-time validation (run in a model_validator):
  - node ids unique
  - every depends_on target exists
  - the dependency graph is acyclic (no cycles)
  - exactly one entry node (a node with no depends_on)
  - node types are from the closed ``NodeType`` set
  - ``{{node_id.field}}`` template references point to existing node ids

See detailed design §2.4.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from typing import Any, Literal, get_args

import yaml
from pydantic import BaseModel, ConfigDict, model_validator

from hanflow.core.errors import DSLValidationError
from hanflow.core.result import SensitivityLevel

NodeType = Literal[
    "Sequential",
    "Parallel",
    "Loop",
    "Branch",
    "HITL",
    "LLM",
    "Tool",
    "Research",
    "Execution",
    "Coordinator",
    "Memory",
    "Subworkflow",
    "Knowledge",
]

_VALID_NODE_TYPES: set[str] = set(get_args(NodeType))

# Matches {{ node_id.anything }} (captures the node_id, non-greedy up to first '.')
_TEMPLATE_REF = re.compile(r"\{\{\s*([A-Za-z_][\w-]*)\.")


class NodeConfig(BaseModel):
    """Per-node config bag. ``extra="allow"`` so each primitive defines its own keys."""

    model_config = ConfigDict(extra="allow")


class ErrorPolicy(BaseModel):
    type: Literal["abort", "retry", "skip", "fallback_branch", "delegate_replan"] = "abort"
    fallback_branch: str | None = None
    max_retries: int = 0
    backoff_seconds: float = 1.0
    backoff_factor: float = 2.0


class RetryPolicy(BaseModel):
    max_attempts: int = 3
    backoff_seconds: float = 1.0
    backoff_factor: float = 2.0
    retryable_errors: list[str] = []


class WorkflowNode(BaseModel):
    id: str
    type: NodeType
    depends_on: list[str] = []
    config: NodeConfig = NodeConfig()
    condition: str | None = None
    on_error: ErrorPolicy = ErrorPolicy()
    retry: RetryPolicy | None = None
    timeout_seconds: int | None = None
    sensitivity: SensitivityLevel = "public"


class WorkflowDSL(BaseModel):
    name: str
    version: str = "0.1.0"
    description: str = ""
    inputs: dict[str, Any] = {}
    nodes: list[WorkflowNode]
    outputs: dict[str, Any] = {}
    metadata: dict[str, Any] = {}

    @classmethod
    def from_yaml(cls, text: str) -> WorkflowDSL:
        """Load from a YAML string. Top-level may be under a ``workflow:`` key."""
        data = yaml.safe_load(text)
        if isinstance(data, dict) and "workflow" in data and isinstance(data["workflow"], dict):
            data = data["workflow"]
        return cls.model_validate(data)

    @model_validator(mode="after")
    def _validate(self) -> WorkflowDSL:
        ids = [n.id for n in self.nodes]

        # node type validity (Pydantic already enforces the Literal, but be explicit
        # so the error surface is uniform via DSLValidationError)
        for n in self.nodes:
            if n.type not in _VALID_NODE_TYPES:
                raise DSLValidationError(f"invalid node type: {n.type!r} (node {n.id!r})")

        # unique ids
        if len(ids) != len(set(ids)):
            seen: set[str] = set()
            dup = next(x for x in ids if x in seen or seen.add(x))  # type: ignore[func-returns-value]
            raise DSLValidationError(f"duplicate node id: {dup}")

        id_set = set(ids)

        # depends_on targets exist
        for n in self.nodes:
            for dep in n.depends_on:
                if dep not in id_set:
                    raise DSLValidationError(f"node '{n.id}' depends on unknown node '{dep}'")

        # acyclic (DFS with coloring)
        adj = {n.id: list(n.depends_on) for n in self.nodes}
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {i: WHITE for i in ids}

        def dfs(u: str) -> bool:
            color[u] = GRAY
            for v in adj[u]:
                if color[v] == GRAY:
                    return True
                if color[v] == WHITE and dfs(v):
                    return True
            color[u] = BLACK
            return False

        for i in ids:
            if color[i] == WHITE and dfs(i):
                raise DSLValidationError(f"dependency cycle detected involving '{i}'")

        # unique entry (exactly one node with no depends_on)
        entries = [n.id for n in self.nodes if not n.depends_on]
        if len(entries) != 1:
            raise DSLValidationError(
                f"expected exactly one entry node (no depends_on), got {len(entries)}: {entries}"
            )

        # template references point to existing nodes
        for n in self.nodes:
            for raw_value in _walk_config_values(n.config):
                if isinstance(raw_value, str):
                    for ref in _TEMPLATE_REF.findall(raw_value):
                        if ref not in id_set:
                            raise DSLValidationError(
                                f"node '{n.id}' references unknown node '{ref}' in template"
                            )

        return self


def _walk_config_values(config: NodeConfig) -> Iterator[Any]:
    """Yield every value in a NodeConfig (recursing into dicts/lists)."""
    for v in config.model_dump().values():
        yield from _walk(v)


def _walk(v: Any) -> Iterator[Any]:
    if isinstance(v, dict):
        for sub in v.values():
            yield from _walk(sub)
    elif isinstance(v, list):
        for sub in v:
            yield from _walk(sub)
    else:
        yield v
