import pytest

from hanflow.observability.provider import (
    ObservabilityProvider,
    create_trace_exporter,
)
from hanflow.observability.trace import NullTraceExporter, TraceExporter


def test_null_provider_by_default():
    exp = create_trace_exporter({"backend": "null"})
    assert isinstance(exp, NullTraceExporter)


def test_unknown_backend_raises():
    with pytest.raises(ValueError):
        create_trace_exporter({"backend": "ghost"})


def test_provider_protocol_has_name():
    class Dummy(ObservabilityProvider):
        name = "dummy"

        def create_trace_exporter(self, config: dict) -> TraceExporter:
            return NullTraceExporter()

        def create_eval_harness(self, config: dict):  # type: ignore[no-untyped-def]
            raise NotImplementedError

        def create_monitor_collector(self, config: dict):  # type: ignore[no-untyped-def]
            raise NotImplementedError

        async def health(self) -> bool:
            return True

    assert Dummy().name == "dummy"


def test_trace_exporter_is_subclassable():
    assert issubclass(NullTraceExporter, TraceExporter)
