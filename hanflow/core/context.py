"""RuntimeContext — the single gateway atoms/primitives use to reach L4+L6.

Atoms and node executors never touch LangGraph / LangChain / concrete stores
directly; they call ``ctx.complete()`` / ``ctx.tool_call()`` / ``ctx.retrieve()``
/ etc. This keeps them mockable and unit-testable in isolation.

``FakeContext`` is a fully in-memory implementation used by unit tests across
all phases — it records calls rather than performing real I/O. Phase 8 ships
the production ``RuntimeContext`` implementation wiring the real L4 providers.

See detailed design §2.5 and §13.6 (spawn_agent isolation contract).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from hanflow.core.result import Chunk, HITLPayload, MemoryOp, SensitivityLevel
from hanflow.core.state import NexusState

if TYPE_CHECKING:
    # Annotations-only imports to avoid a runtime cycle
    # (sdk → ... → core; models.providers.base is harmless but kept here for
    #  symmetry and to keep the module body free of provider deps).
    from hanflow.models.providers.base import StreamChunk
    from hanflow.sdk import RunEvent


@runtime_checkable
class RuntimeContext(Protocol):
    """The contract every L4/L6 capability exposes to atoms/primitives."""

    # --- L4 GraphRuntime -----------------------------------------------------
    state: NexusState

    def emit_hitl(self, payload: HITLPayload) -> None: ...

    # --- L4 ModelRouter ------------------------------------------------------
    async def complete(
        self,
        messages: list[Any],
        *,
        role: str | None = None,
        task_type: str | None = None,
        sensitivity: SensitivityLevel = "public",
        prefer: str | None = None,
        **kwargs: Any,
    ) -> Any: ...

    async def stream(
        self,
        messages: list[Any],
        *,
        role: str | None = None,
        task_type: str | None = None,
        sensitivity: SensitivityLevel = "public",
        prefer: str | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[StreamChunk]: ...

    # --- L4 MCPBus -----------------------------------------------------------
    async def tool_call(
        self, name: str, args: dict[str, Any], *, timeout_seconds: int = 60
    ) -> Any: ...

    # --- L4 FilesystemMemory -------------------------------------------------
    async def memory(self, op: MemoryOp) -> Any: ...
    def workspace(self) -> Any: ...  # Path-like

    # --- L4 SkillsLoader -----------------------------------------------------
    async def load_skill(self, name: str) -> Any: ...
    async def match_skills(self, task: str) -> list[Any]: ...

    # --- L4 RetrievalProvider ------------------------------------------------
    async def retrieve(
        self,
        store: str,
        query: str,
        *,
        top_k: int = 5,
        rerank: str | None = None,
        filter: dict[str, Any] | None = None,
    ) -> list[Chunk]: ...

    # --- L6 TraceExporter ----------------------------------------------------
    def span(self, name: str, **attrs: Any) -> Any: ...  # async cm
    async def event(self, name: str, **attrs: Any) -> None: ...

    # --- L6 RunHandle push (llm_token / node events streamed to the host) ----
    async def emit_run_event(self, event: RunEvent) -> None: ...

    # --- Sub-agent / sub-workflow (single spawn entry, §13.6) ----------------
    async def compile_subgraph(self, dsl: Any) -> Any: ...
    async def spawn_agent(self, spec: Any) -> RuntimeContext: ...


@dataclass
class _FakeSpan:
    """Minimal span record used by FakeContext.span()."""

    name: str
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class FakeContext:
    """In-memory RuntimeContext for unit tests.

    Records every call so tests can assert on side effects without real I/O.
    Override attributes (e.g. ``ctx.complete_fn``) to inject custom behaviour.
    """

    state: NexusState
    # records
    emitted_hitl: HITLPayload | None = None
    memory_ops: list[MemoryOp] = field(default_factory=list)
    tool_calls: list[tuple[str, dict[str, Any]]] = field(default_factory=list)
    spans: list[_FakeSpan] = field(default_factory=list)
    events: list[tuple[str, dict[str, Any]]] = field(default_factory=list)
    spawned: list[FakeContext] = field(default_factory=list)
    retrieve_results: dict[str, list[Chunk]] = field(default_factory=dict)

    def emit_hitl(self, payload: HITLPayload) -> None:
        self.emitted_hitl = payload

    async def complete(self, messages: list[Any], **kwargs: Any) -> Any:
        return {"messages": messages, "kwargs": kwargs}

    async def stream(self, messages: list[Any], **kwargs: Any) -> AsyncIterator[StreamChunk]:
        # FakeContext does not perform real streaming; yield nothing.
        return  # type: ignore[return-value]
        yield  # pragma: no cover

    async def tool_call(self, name: str, args: dict[str, Any], *, timeout_seconds: int = 60) -> Any:
        self.tool_calls.append((name, args))
        return {"name": name, "args": args}

    async def memory(self, op: MemoryOp) -> Any:
        self.memory_ops.append(op)
        return None

    def workspace(self) -> Any:
        return None

    async def load_skill(self, name: str) -> Any:
        return {"name": name}

    async def match_skills(self, task: str) -> list[Any]:
        return []

    async def retrieve(
        self,
        store: str,
        query: str,
        *,
        top_k: int = 5,
        rerank: str | None = None,
        filter: dict[str, Any] | None = None,
    ) -> list[Chunk]:
        return list(self.retrieve_results.get(store, []))

    @asynccontextmanager
    async def span(self, name: str, **attrs: Any) -> AsyncIterator[_FakeSpan]:
        sp = _FakeSpan(name=name, attributes=dict(attrs))
        self.spans.append(sp)
        yield sp

    async def event(self, name: str, **attrs: Any) -> None:
        self.events.append((name, attrs))

    async def emit_run_event(self, event: RunEvent) -> None:
        # No RunHandle queue attached in unit tests; record and drop silently.
        return None

    async def compile_subgraph(self, dsl: Any) -> Any:
        return {"compiled": True, "dsl": dsl}

    async def spawn_agent(self, spec: Any) -> FakeContext:
        child = FakeContext(state=self.state)
        self.spawned.append(child)
        return child
