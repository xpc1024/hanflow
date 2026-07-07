"""Result & shared data types flowing through the framework.

Design (see detailed design §2.2/§2.3):
- ``SensitivityLevel`` lives here to keep the import graph acyclic
  (``dsl.py``/``context.py`` both import it from here).
- ``Artifact``/``Source``/``MemoryOp``/``TraceEvent``/``HITL*``/``Chunk``
  are plain Pydantic v2 models with all-serializable fields so checkpoints
  can ``model_dump()`` them verbatim.
- ``AtomResult`` is the universal return of atoms and node executors.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from hanflow.core.errors import HanflowError

SensitivityLevel = Literal["public", "internal", "confidential", "restricted"]


class Artifact(BaseModel):
    """A run product (report / code / image / data / file)."""

    id: str
    kind: Literal["report", "code", "image", "data", "file"]
    content: str | bytes
    mime_type: str
    source_node: str
    meta: dict[str, Any] = {}


class Source(BaseModel):
    """A cited origin for a claim — used end-to-end for provenance."""

    source_id: str
    kind: Literal["web", "private_kb", "tool", "computed"]
    url: str | None = None
    title: str | None = None
    snippet: str | None = None
    fetched_at: datetime | None = None
    credibility: float = 0.5
    extra: dict[str, Any] = {}


class MemoryOp(BaseModel):
    """A deferred, idempotent memory operation emitted by an atom/primitive."""

    action: Literal["read", "write", "update", "delete", "summarize"]
    scope: Literal["scratch", "session", "long_term"]
    key: str
    value: Any | None = None
    ttl_seconds: int | None = None


class TraceEvent(BaseModel):
    """A discrete event attached to a span."""

    span_id: str
    parent_span_id: str | None = None
    name: str
    kind: Literal["span_start", "span_end", "event", "error"]
    timestamp: datetime
    attributes: dict[str, Any] = {}


class HITLPayload(BaseModel):
    """Payload describing a paused human-in-the-loop gate."""

    node_id: str
    title: str
    description: str
    form: dict[str, Any]
    current_value: Any
    actions: list[Literal["approve", "edit", "reject", "reroute"]]
    paused_at: datetime
    timeout_seconds: int | None = None
    approver: str | None = None


class HITLRecord(BaseModel):
    """A human decision resolving a HITL gate."""

    action: Literal["approve", "edit", "reject", "reroute"]
    edited_value: Any | None = None
    reroute_target: str | None = None
    decided_by: str
    decided_at: datetime
    duration_seconds: float
    reason: str | None = None
    form: dict[str, Any] | None = None


class Chunk(BaseModel):
    """A retrieval hit, carrying its source for unified provenance."""

    text: str
    score: float
    source: Source
    metadata: dict[str, Any] = {}


class NextAction(BaseModel):
    """What the engine should do after an executor returns."""

    type: Literal["continue", "branch", "loop", "pause_hitl", "abort"] = "continue"
    branch_label: str | None = None
    loop_continue: bool = False


class ResearchNote(BaseModel):
    """A single research finding with bound source_ids for provenance (§8.2)."""

    id: str
    claim: str
    evidence: str
    source_ids: list[str]
    confidence: float


class AtomResult(BaseModel):
    """Universal return of atoms and node executors."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    output: dict[str, Any]
    artifacts: list[Artifact] = []
    memory_ops: list[MemoryOp] = []
    trace_events: list[TraceEvent] = []
    sources: list[Source] = []
    next_action: NextAction = NextAction()
    error: HanflowError | None = None
