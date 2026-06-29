"""ObservabilityProvider — abstraction to avoid lock-in to a single backend.

LangSmith is the default backend; Langfuse/Phoenix/OTel are interchangeable
via the same interface. Phase 1 only exposes ``create_trace_exporter``;
``create_eval_harness`` / ``create_monitor_collector`` are stubbed for later
phases (see detailed design §9.6).
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from hanflow.observability.trace import NullTraceExporter, TraceExporter


@runtime_checkable
class ObservabilityProvider(Protocol):
    name: str

    def create_trace_exporter(self, config: dict[str, Any]) -> TraceExporter: ...

    def create_eval_harness(self, config: dict[str, Any]) -> Any:
        raise NotImplementedError

    def create_monitor_collector(self, config: dict[str, Any]) -> Any:
        raise NotImplementedError

    async def health(self) -> bool: ...


def create_trace_exporter(config: dict[str, Any]) -> TraceExporter:
    """Factory selecting a TraceExporter by ``config['backend']``.

    Backends: ``null`` (default), ``langsmith``, ``otel``.
    Unknown backends raise ValueError.
    """
    backend = (config or {}).get("backend", "null")
    if backend == "null":
        return NullTraceExporter()
    if backend == "langsmith":
        from hanflow.observability.providers.langsmith import LangSmithTraceExporter

        return LangSmithTraceExporter.from_config(config)
    if backend == "otel":
        from hanflow.observability.providers.otel import OTelTraceExporter

        return OTelTraceExporter.from_config(config)
    raise ValueError(f"unknown observability backend: {backend!r}")
