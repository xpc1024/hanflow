"""Runtime state shared across the whole LangGraph StateGraph.

``NexusState`` is a Pydantic v2 ``BaseModel`` whose ``messages`` field uses
LangGraph's ``add_messages`` reducer — so it works as a ``StateGraph`` schema
(the role ``MessagesState`` plays) while remaining fully serializable for
Checkpoints via ``model_dump()``. Every primitive node reads/writes this single
structure, which is what makes Checkpoint / resume / time-travel possible.

Key fields:
- ``node_states[node_id]`` isolates per-node I/O.
- ``pending_hitl`` non-None means the graph is paused at a HITL gate.
- ``memory_ops`` are deferred (executed by the engine, not the emitter).

Note on LangGraph 1.2.0: the stock ``MessagesState`` is a ``dict`` subclass
(not Pydantic), so inheriting from it would break ``model_dump()``. We instead
replicate its contract (a ``messages`` field annotated with ``add_messages``)
on a Pydantic model — equivalent for StateGraph use, serializable for us.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal

from langgraph.graph.message import add_messages
from pydantic import BaseModel

from hanflow.core.result import Artifact, HITLPayload, HITLRecord, MemoryOp


class RunMeta(BaseModel):
    run_id: str
    workflow_name: str
    workflow_version: str
    started_at: datetime
    mode: Literal["static", "dynamic", "hybrid"]
    trigger: Literal["cli", "sdk", "web", "api"]


class NodeState(BaseModel):
    node_id: str
    node_type: str
    status: Literal["pending", "running", "paused", "succeeded", "failed", "skipped"] = "pending"
    started_at: datetime | None = None
    ended_at: datetime | None = None
    inputs: dict[str, Any] = {}
    outputs: dict[str, Any] = {}
    error: str | None = None
    attempts: int = 0
    hitl: HITLRecord | None = None


class NexusState(BaseModel):
    """Shared graph state.

    ``messages`` carries LangGraph's ``add_messages`` reducer (the contract
    ``MessagesState`` provides); the rest are plain serializable fields. This
    model is a valid ``StateGraph`` schema and round-trips through
    ``model_dump()`` / ``model_validate()`` for checkpoints.
    """

    meta: RunMeta
    inputs: dict[str, Any]
    outputs: dict[str, Any]
    node_states: dict[str, NodeState]
    artifacts: list[Artifact]
    memory_ops: list[MemoryOp]
    pending_hitl: HITLPayload | None = None
    variables: dict[str, Any]
    messages: Annotated[list[Any], add_messages] = []
