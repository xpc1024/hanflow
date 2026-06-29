"""OpenTelemetry TraceExporter — interchangeable alternative to LangSmith.

Uses the OTel API tracer; spans are created via ``start_as_current_span`` so
the OTel SDK handles parent propagation natively (its own context). On
exception the span records the error. Events become OTel span events.

We still maintain the Hanflow span stack (via ``_BufferedTraceExporter``) so
``_export`` can read each span's status / error and close the matching OTel
span. The ``tracer`` is normally built by ``from_config`` but may be passed
directly in tests.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

from hanflow.observability.trace import Span, SpanEvent, _BufferedTraceExporter, _current_span


class OTelTraceExporter(_BufferedTraceExporter):
    def __init__(self, tracer: Any) -> None:
        super().__init__()
        self.tracer = tracer
        # Map our span id -> the live OTel span, so event() / _export can reach it.
        self._live: dict[str, Any] = {}

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> OTelTraceExporter:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider

        service_name = config.get("service_name", "hanflow")
        provider = TracerProvider(resource=_build_resource(service_name))
        trace.set_tracer_provider(provider)
        return cls(tracer=provider.get_tracer("hanflow"))

    @asynccontextmanager
    async def span(self, name: str, *, kind: str = "node", **attrs: Any) -> AsyncIterator[Span]:
        """Open a Hanflow span + a matching OTel span.

        OTel owns parent propagation in its own context; we mirror the span in
        our stack so ``_export`` can close it and ``event`` can reach it.
        """
        sp = self._open(name, kind, attrs)  # type: ignore[arg-type]
        token = _current_span.set(sp)
        otel_cm = self.tracer.start_as_current_span(
            name, attributes={**attrs, "hanflow.kind": kind}
        )
        otel_span = otel_cm.__enter__()
        self._live[sp.span_id] = otel_span
        try:
            yield sp
            sp.end_time = datetime.now(UTC)
        except BaseException as exc:  # noqa: BLE001
            sp.record_error(exc)
            sp.end_time = datetime.now(UTC)
            raise
        finally:
            _current_span.reset(token)
            self._buffer.append(sp)

    async def event(self, name: str, **attrs: Any) -> None:
        # Record onto the live OTel span for the current Hanflow span.
        sp = _current_span.get()
        if sp is not None and sp.span_id in self._live:
            self._live[sp.span_id].add_event(name, attributes=dict(attrs))
        # Also keep the event on the Hanflow span for parity with other exporters.
        if sp is not None:
            sp.events.append(SpanEvent(name=name, attributes=dict(attrs)))

    async def _export(self, spans: list[Span]) -> None:
        for sp in spans:
            otel_span = self._live.pop(sp.span_id, None)
            if otel_span is None:
                continue
            if sp.status == "error":
                exc_type = sp.attributes.get("error.type", "Error")
                exc_msg = sp.attributes.get("error.message", "")
                otel_span.record_exception(Exception(f"{exc_type}: {exc_msg}"))
                otel_span.set_status(2)  # STATUS_CODE_ERROR
            else:
                otel_span.set_status(1)  # STATUS_CODE_OK
            otel_span.end()


def _build_resource(service_name: str) -> Any:
    from opentelemetry.sdk.resources import Resource

    return Resource.create({"service.name": service_name})
