"""L6 observability layer.

Phase 1 ships:
- TraceExporter (contextvar-based parent propagation, async batch export)
- ObservabilityProvider abstraction + factory
- Backends: Null (default) / LangSmith (default configured) / OTel (optional)

EvalHarness and MonitorCollector land in later phases (see roadmap).
"""

from hanflow.observability.provider import ObservabilityProvider, create_trace_exporter
from hanflow.observability.trace import (
    NullTraceExporter,
    Span,
    SpanEvent,
    SpanKind,
    SpanStatus,
    TraceExporter,
)

__all__ = [
    "ObservabilityProvider",
    "create_trace_exporter",
    "NullTraceExporter",
    "Span",
    "SpanEvent",
    "SpanKind",
    "SpanStatus",
    "TraceExporter",
]
