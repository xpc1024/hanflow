"""TraceExporter — the L6 trace backend injected into RuntimeContext.

Design (detailed design §9.7):
- A ``contextvars`` stack holds the active span for each async task, so
  ``span()`` automatically wires ``parent_span_id`` and shares one ``trace_id``
  per tree without manual plumbing.
- On ``__aexit__`` the span is ended (with ok/error status) and pushed to a
  buffer; ``flush()`` exports the buffer in batch (called at run end and on
  graceful shutdown).
- ``NullTraceExporter`` is the zero-overhead default (drops everything).
  ``_BufferedTraceExporter`` collects spans in-memory for tests / LangSmith /
  OTel subclasses.
"""

from __future__ import annotations

import contextvars
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

SpanKind = Literal[
    "workflow",
    "node",
    "atom",
    "llm",
    "tool",
    "retrieval",
    "memory",
    "hitl",
]
SpanStatus = Literal["ok", "error", "paused"]


def _now() -> datetime:
    """Timezone-aware UTC now (avoids the deprecated datetime.utcnow())."""
    return datetime.now(UTC)


class SpanEvent(BaseModel):
    name: str
    timestamp: datetime = Field(default_factory=_now)
    attributes: dict[str, Any] = {}


class Span(BaseModel):
    span_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:16])
    parent_span_id: str | None = None
    trace_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:32])
    name: str
    kind: SpanKind = "node"
    start_time: datetime = Field(default_factory=_now)
    end_time: datetime | None = None
    status: SpanStatus = "ok"
    attributes: dict[str, Any] = {}
    events: list[SpanEvent] = []

    def record_error(self, exc: BaseException) -> None:
        self.status = "error"
        self.attributes["error.type"] = type(exc).__name__
        self.attributes["error.message"] = str(exc)


# Per-task stack of active spans. Each async task gets its own copy.
_current_span: contextvars.ContextVar[Span | None] = contextvars.ContextVar(
    "hanflow_current_span", default=None
)


class TraceExporter:
    """Abstract base. Subclasses implement ``_export(spans)`` and override
    ``span()`` (an async context manager, conventionally built with
    ``@asynccontextmanager``)."""

    @asynccontextmanager
    async def span(
        self, name: str, *, kind: SpanKind = "node", **attrs: Any
    ) -> AsyncIterator[Span]:
        """Open/close a span. Subclasses must override with their own
        ``@asynccontextmanager``-decorated implementation."""
        raise NotImplementedError
        yield Span(name=name, kind=kind, attributes=dict(attrs))  # pragma: no cover

    async def event(self, name: str, **attrs: Any) -> None:
        sp = _current_span.get()
        if sp is not None:
            sp.events.append(SpanEvent(name=name, attributes=dict(attrs)))

    async def flush(self) -> None:
        raise NotImplementedError

    def _open(self, name: str, kind: SpanKind, attrs: dict[str, Any]) -> Span:
        parent = _current_span.get()
        if parent is not None:
            return Span(
                name=name,
                kind=kind,
                attributes=dict(attrs),
                parent_span_id=parent.span_id,
                trace_id=parent.trace_id,
            )
        return Span(name=name, kind=kind, attributes=dict(attrs))


class _BufferedTraceExporter(TraceExporter):
    """Base for exporters that buffer spans then export them on flush()."""

    def __init__(self) -> None:
        self._buffer: list[Span] = []
        self.exported: list[Span] = []

    @asynccontextmanager
    async def span(
        self, name: str, *, kind: SpanKind = "node", **attrs: Any
    ) -> AsyncIterator[Span]:
        sp = self._open(name, kind, attrs)
        token = _current_span.set(sp)
        try:
            yield sp
            sp.end_time = _now()
        except BaseException as exc:  # noqa: BLE001 — record then re-raise
            sp.record_error(exc)
            sp.end_time = _now()
            raise
        finally:
            _current_span.reset(token)
            self._buffer.append(sp)

    async def flush(self) -> None:
        if not self._buffer:
            return
        batch = self._buffer
        self._buffer = []
        await self._export(batch)

    async def _export(self, spans: list[Span]) -> None:
        self.exported.extend(spans)


class NullTraceExporter(_BufferedTraceExporter):
    """Default zero-overhead exporter: drops everything on flush."""

    async def _export(self, spans: list[Span]) -> None:
        # Intentionally drop — this is the "tracing off" default.
        return None
