"""ModelRouter.stream tests (§design Router.stream + fallback×stream).

Fallback semantics for streaming: providers may be swapped only *before* the
first chunk is yielded. Once a chunk has been delivered to the caller, a
mid-flight failure must surface as a ``HanflowError`` (no transparent retry —
the caller already received partial output).
"""

import pytest

from hanflow.core.errors import HanflowError, ModelTimeoutError
from hanflow.models.providers.base import StreamChunk
from hanflow.models.router import ModelRouter
from hanflow.models.strategies.fallback import FallbackStrategy


@pytest.mark.asyncio
async def test_stream_basic(fake_providers, null_trace):
    """Normal streaming: every chunk is aggregated in order."""
    fake_providers["cloud"].stream_tokens = ["hel", "lo"]
    router = ModelRouter(
        providers=fake_providers,
        strategies=[],
        governance=None,
        trace=null_trace,
        default_model=("cloud", "strong"),
    )
    out = [c async for c in router.stream([{"role": "user", "content": "hi"}])]
    assert "".join(c.delta for c in out) == "hello"


@pytest.mark.asyncio
async def test_stream_fallback_before_first_token(fake_providers, null_trace):
    """Failure before the first chunk -> switch to the fallback provider.

    Setting ``fail_with`` makes ``FakeProvider.stream`` raise before its first
    yield, so the router must move on to the next candidate in the fallback
    chain and surface *its* output instead.
    """
    fake_providers["cloud"].fail_with = ModelTimeoutError("cloud down")
    fake_providers["cloud"].stream_tokens = ["x"]  # unreachable
    fake_providers["local"].stream_tokens = ["ok"]
    router = ModelRouter(
        providers=fake_providers,
        strategies=[FallbackStrategy(chain=[("cloud", "strong"), ("local", "local-m")])],
        governance=None,
        trace=null_trace,
        default_model=("cloud", "strong"),
    )
    out = [c async for c in router.stream([{"role": "user", "content": "hi"}])]
    assert "".join(c.delta for c in out) == "ok"  # from local fallback


@pytest.mark.asyncio
async def test_stream_no_fallback_after_first_token(null_trace):
    """Failure after the first chunk -> raise ``HanflowError`` (no fallback).

    A custom provider yields one chunk then raises mid-flight. The router must
    surface the error rather than silently retrying on a different provider
    (the caller has already received partial output).
    """

    class _MidFailProvider:
        name = "midfail"
        is_local = False

        async def stream(self, model, messages, **kwargs):
            yield StreamChunk(delta="a")
            raise ModelTimeoutError("mid-flight")

        async def complete(self, model, messages, **kwargs):
            raise NotImplementedError

        def estimate_cost(self, model, usage):
            return 0.0

        def supported_models(self):
            return ["x"]

    providers = {"midfail": _MidFailProvider()}
    router = ModelRouter(
        providers=providers,
        strategies=[],
        governance=None,
        trace=null_trace,
        default_model=("midfail", "x"),
    )
    with pytest.raises(HanflowError):
        [c async for c in router.stream([{"role": "user", "content": "hi"}])]
