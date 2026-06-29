import pytest

from hanflow.models.router import ModelRouter
from hanflow.models.strategies.base import RoutingRequest


@pytest.mark.asyncio
async def test_router_picks_default_when_no_strategy(fake_providers, null_trace):
    router = ModelRouter(
        providers=fake_providers,
        strategies=[],
        governance=None,
        trace=null_trace,
        default_model=("cloud", "strong"),
    )
    resp = await router.complete([{"role": "user", "content": "hi"}])
    assert resp.provider == "cloud"
    assert resp.model_used == "strong"


@pytest.mark.asyncio
async def test_router_static_prefer_overrides(fake_providers, null_trace):
    from hanflow.models.strategies.static import StaticStrategy

    router = ModelRouter(
        providers=fake_providers,
        strategies=[StaticStrategy()],
        governance=None,
        trace=null_trace,
        default_model=("cloud", "strong"),
    )
    resp = await router.complete([{"role": "user", "content": "hi"}], prefer=("cloud", "fast"))
    assert resp.model_used == "fast"


@pytest.mark.asyncio
async def test_router_falls_back_on_provider_failure(fake_providers, null_trace):
    from hanflow.models.strategies.fallback import FallbackStrategy

    fake_providers["cloud"].fail_with = __import__(
        "hanflow.core.errors", fromlist=["ModelTimeoutError"]
    ).ModelTimeoutError("down")
    router = ModelRouter(
        providers=fake_providers,
        strategies=[FallbackStrategy(chain=[("cloud", "strong"), ("local", "local-m")])],
        governance=None,
        trace=null_trace,
        default_model=("cloud", "strong"),
    )
    resp = await router.complete([{"role": "user", "content": "hi"}])
    assert resp.provider == "local"


@pytest.mark.asyncio
async def test_router_trace_span_produced(fake_providers):
    # NullTraceExporter drops spans on export; use _BufferedTraceExporter to observe.
    from hanflow.observability.trace import _BufferedTraceExporter

    trace = _BufferedTraceExporter()
    router = ModelRouter(
        providers=fake_providers,
        strategies=[],
        governance=None,
        trace=trace,
        default_model=("cloud", "strong"),
    )
    await router.complete([{"role": "user", "content": "hi"}])
    await trace.flush()
    assert any(s.name == "llm.complete" for s in trace.exported)


def test_routing_request_defaults():
    req = RoutingRequest(messages=[])
    assert req.sensitivity == "public"
    assert req.run_budget_remaining == 1.0
    assert req.prefer is None
