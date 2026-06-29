from unittest.mock import MagicMock

import pytest

from hanflow.observability.providers.otel import OTelTraceExporter


def _make_tracer():
    tracer = MagicMock()
    started: list[MagicMock] = []

    def start_as_current_span(name, **kwargs):  # type: ignore[no-untyped-def]
        span = MagicMock()
        span.is_recording.return_value = True
        started.append(span)
        cm = MagicMock()
        cm.__enter__ = MagicMock(return_value=span)
        cm.__exit__ = MagicMock(return_value=False)
        return cm

    tracer.start_as_current_span.side_effect = start_as_current_span
    return tracer, started


@pytest.mark.asyncio
async def test_otel_uses_tracer_provider():
    tracer, started = _make_tracer()
    exp = OTelTraceExporter(tracer=tracer)
    async with exp.span("workflow.run"):
        pass
    await exp.flush()
    assert len(started) == 1


@pytest.mark.asyncio
async def test_otel_records_error_on_exception():
    tracer, started = _make_tracer()
    exp = OTelTraceExporter(tracer=tracer)
    with pytest.raises(ValueError):
        async with exp.span("bad"):
            raise ValueError("boom")
    await exp.flush()
    started[0].record_exception.assert_called()


@pytest.mark.asyncio
async def test_otel_from_config_builds_tracer():
    exp = OTelTraceExporter.from_config({"backend": "otel", "service_name": "hanflow"})
    assert exp.tracer is not None


@pytest.mark.asyncio
async def test_otel_event_records_on_current_span():
    tracer, started = _make_tracer()
    exp = OTelTraceExporter(tracer=tracer)
    async with exp.span("workflow.run"):
        await exp.event("checkpoint.saved", run_id="r1")
    await exp.flush()
    # span.add_event should have been called with the event name
    started[0].add_event.assert_called()
