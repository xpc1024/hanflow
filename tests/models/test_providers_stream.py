"""openai/glm provider stream contract tests (§design §6, mock SDK).

Mocks the SDK class itself (``openai.AsyncOpenAI`` / ``zhipuai.ZhipuAI``)
because each provider constructs a fresh client per call via a delayed
function-local import — patching ``self._client`` is not possible.

For anthropic / ollama the optional SDK is typically not installed, so
``patch("anthropic.AsyncAnthropic")`` itself would raise ``ModuleNotFoundError``
when mock resolves the target (same root cause that currently breaks the glm
tests). We instead inject a fake SDK module into ``sys.modules`` before
importing the provider, which exercises the real ``stream()`` parsing logic
without the SDK installed.
"""

import sys
import types
from unittest.mock import AsyncMock, patch

import pytest

from hanflow.core.errors import ModelTimeoutError


class _FakeDelta:
    def __init__(self, content) -> None:
        self.content = content


class _FakeChoice:
    def __init__(self, delta, finish=None) -> None:
        self.delta = delta
        self.finish_reason = finish


class _FakeUsage:
    def __init__(self, prompt_tokens=5, completion_tokens=3, total_tokens=8) -> None:
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = total_tokens


class _FakeChunk:
    def __init__(self, choices, usage=None) -> None:
        self.choices = choices
        self.usage = usage

    def model_dump(self) -> dict:
        return {"fake": True}


async def _async_iter(items):
    for x in items:
        yield x


@pytest.mark.asyncio
async def test_openai_stream_parses_chunks():
    from hanflow.models.providers.openai import OpenAIProvider

    provider = OpenAIProvider(api_key="sk-test")
    fake_chunks = [
        _FakeChunk([_FakeChoice(_FakeDelta("hel"))]),
        _FakeChunk([_FakeChoice(_FakeDelta("lo"), finish="stop")]),
    ]
    with patch("openai.AsyncOpenAI") as MockClient:
        mock_client = MockClient.return_value
        mock_client.chat.completions.create = AsyncMock(return_value=_async_iter(fake_chunks))
        out = [c async for c in provider.stream("gpt-4o", [{"role": "user", "content": "hi"}])]
    assert "".join(c.delta for c in out) == "hello"
    assert out[-1].finish_reason == "stop"


@pytest.mark.asyncio
async def test_openai_stream_includes_usage():
    from hanflow.models.providers.openai import OpenAIProvider

    provider = OpenAIProvider(api_key="sk-test")
    fake_chunks = [
        _FakeChunk([_FakeChoice(_FakeDelta("hi"))]),
        _FakeChunk([], usage=_FakeUsage(prompt_tokens=10, completion_tokens=4, total_tokens=14)),
    ]
    with patch("openai.AsyncOpenAI") as MockClient:
        mock_client = MockClient.return_value
        mock_client.chat.completions.create = AsyncMock(return_value=_async_iter(fake_chunks))
        out = [c async for c in provider.stream("gpt-4o", [])]
    usage_chunk = next(c for c in out if c.usage is not None)
    assert usage_chunk.usage.input_tokens == 10
    assert usage_chunk.usage.output_tokens == 4
    assert usage_chunk.usage.total_tokens == 14


@pytest.mark.asyncio
async def test_openai_stream_wraps_connection_error():
    from hanflow.models.providers.openai import OpenAIProvider

    provider = OpenAIProvider(api_key="sk-test")
    with patch("openai.AsyncOpenAI") as MockClient:
        mock_client = MockClient.return_value
        mock_client.chat.completions.create = AsyncMock(side_effect=Exception("connect refused"))
        with pytest.raises(ModelTimeoutError) as exc_info:
            _ = [c async for c in provider.stream("gpt-4o", [])]
        assert exc_info.value.retryable is True  # connection failure is retryable


@pytest.mark.asyncio
async def test_openai_stream_midflight_error_not_retryable():
    from hanflow.models.providers.openai import OpenAIProvider

    provider = OpenAIProvider(api_key="sk-test")

    async def _boom(*a, **kw):
        # yields one chunk then fails mid-stream
        yield _FakeChunk([_FakeChoice(_FakeDelta("partial"))])
        raise Exception("server dropped connection")

    with patch("openai.AsyncOpenAI") as MockClient:
        mock_client = MockClient.return_value
        mock_client.chat.completions.create = AsyncMock(return_value=_boom())
        with pytest.raises(ModelTimeoutError) as exc_info:
            _ = [c async for c in provider.stream("gpt-4o", [])]
        assert exc_info.value.retryable is False  # mid-flight failure not retryable


@pytest.mark.asyncio
async def test_glm_stream_parses_chunks():
    from hanflow.models.providers.glm import GLMProvider

    provider = GLMProvider(api_key="x")
    fake_chunks = [
        _FakeChunk([_FakeChoice(_FakeDelta("你"))]),
        _FakeChunk([_FakeChoice(_FakeDelta("好"), finish="stop")]),
    ]
    with patch("zhipuai.ZhipuAI") as MockClient:
        mock_client = MockClient.return_value
        mock_client.chat.completions.create = AsyncMock(return_value=_async_iter(fake_chunks))
        out = [c async for c in provider.stream("glm-4-flash", [])]
    assert "".join(c.delta for c in out) == "你好"


@pytest.mark.asyncio
async def test_glm_stream_wraps_connection_error():
    from hanflow.models.providers.glm import GLMProvider

    provider = GLMProvider(api_key="x")
    with patch("zhipuai.ZhipuAI") as MockClient:
        mock_client = MockClient.return_value
        mock_client.chat.completions.create = AsyncMock(side_effect=Exception("connect refused"))
        with pytest.raises(ModelTimeoutError) as exc_info:
            _ = [c async for c in provider.stream("glm-4-flash", [])]
        assert exc_info.value.retryable is True


# --- deepseek / vllm: streaming is inherited from OpenAIProvider (no override) ---
# These providers are OpenAI-compatible; their `stream()` is the inherited base
# impl, routed to the correct base_url via __init__. No SDK call is made here.


def test_deepseek_inherits_openai_stream_and_routes_base_url():
    from hanflow.models.providers.deepseek import DeepSeekProvider
    from hanflow.models.providers.openai import OpenAIProvider

    provider = DeepSeekProvider(api_key="k")
    # class-attribute identity: stream is the inherited OpenAIProvider.stream
    assert type(provider).stream is OpenAIProvider.stream
    assert provider.base_url == "https://api.deepseek.com"


def test_vllm_inherits_openai_stream_and_routes_base_url():
    from hanflow.models.providers.openai import OpenAIProvider
    from hanflow.models.providers.vllm import VLLMProvider

    provider = VLLMProvider()
    assert type(provider).stream is OpenAIProvider.stream
    assert provider.base_url == "http://localhost:8000/v1"


# --- ollama: stream() implemented (dict-based async iterator) ---
# Optional `ollama` SDK may be absent; inject a fake module into sys.modules so
# the provider's delayed `import ollama` resolves to our stub without installing.


class _FakeOllamaClient:
    """Mimics ollama.AsyncClient.chat(stream=True) returning an async iterator."""

    def __init__(self, chunks, *, connect_error=None, midflight_after=None):
        self._chunks = chunks
        self._connect_error = connect_error
        self._midflight_after = midflight_after

    async def chat(self, *args, **kwargs):
        if self._connect_error is not None:
            raise self._connect_error

        chunks = list(self._chunks)
        midflight_after = self._midflight_after

        class _Iter:
            def __init__(self, items):
                self._items = items
                self._i = 0

            def __aiter__(self):
                return self

            async def __anext__(self):
                if midflight_after is not None and self._i == midflight_after:
                    raise Exception("server dropped connection")
                if self._i >= len(self._items):
                    raise StopAsyncIteration
                item = self._items[self._i]
                self._i += 1
                return item

        return _Iter(chunks)


def _install_fake_ollama(client):
    """Register a fake `ollama` module whose AsyncClient() returns `client`."""
    fake = types.ModuleType("ollama")

    class _AsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        # tests set .chat via attribute on the instance? No — client is created
        # fresh each call. Instead store the per-test client factory.

    # Simpler: AsyncClient is a callable returning our prebuilt client.
    fake.AsyncClient = lambda *a, **kw: client
    sys.modules["ollama"] = fake


@pytest.fixture
def ollama_module_clean():
    """Remove cached provider + ollama modules so each test re-imports fresh."""
    for mod in list(sys.modules):
        if mod == "ollama" or mod.endswith("models.providers.ollama"):
            sys.modules.pop(mod, None)
    yield
    sys.modules.pop("ollama", None)
    sys.modules.pop("hanflow.models.providers.ollama", None)


@pytest.mark.asyncio
async def test_ollama_stream_parses_chunks(ollama_module_clean):
    chunks = [
        {"message": {"content": "hel"}, "done": False},
        {
            "message": {"content": "lo"},
            "done": True,
            "done_reason": "stop",
            "prompt_eval_count": 5,
            "eval_count": 2,
        },
    ]
    _install_fake_ollama(_FakeOllamaClient(chunks))

    from hanflow.models.providers.ollama import OllamaProvider

    provider = OllamaProvider()
    out = [c async for c in provider.stream("qwen2.5:7b", [{"role": "user", "content": "hi"}])]
    assert "".join(c.delta for c in out) == "hello"
    assert out[-1].finish_reason == "stop"


@pytest.mark.asyncio
async def test_ollama_stream_includes_usage(ollama_module_clean):
    chunks = [
        {"message": {"content": "hi"}, "done": False},
        {
            "message": {"content": ""},
            "done": True,
            "done_reason": "stop",
            "prompt_eval_count": 10,
            "eval_count": 4,
        },
    ]
    _install_fake_ollama(_FakeOllamaClient(chunks))

    from hanflow.models.providers.ollama import OllamaProvider

    provider = OllamaProvider()
    out = [c async for c in provider.stream("qwen2.5:7b", [])]
    usage_chunk = next(c for c in out if c.usage is not None)
    assert usage_chunk.usage.input_tokens == 10
    assert usage_chunk.usage.output_tokens == 4
    assert usage_chunk.usage.total_tokens == 14


@pytest.mark.asyncio
async def test_ollama_stream_wraps_connection_error(ollama_module_clean):
    _install_fake_ollama(_FakeOllamaClient([], connect_error=Exception("connect refused")))

    from hanflow.models.providers.ollama import OllamaProvider

    provider = OllamaProvider()
    with pytest.raises(ModelTimeoutError) as exc_info:
        _ = [c async for c in provider.stream("qwen2.5:7b", [])]
    assert exc_info.value.retryable is True  # connection failure is retryable


@pytest.mark.asyncio
async def test_ollama_stream_midflight_error_not_retryable(ollama_module_clean):
    chunks = [{"message": {"content": "partial"}, "done": False}]
    # fail after yielding 1 chunk
    _install_fake_ollama(_FakeOllamaClient(chunks, midflight_after=1))

    from hanflow.models.providers.ollama import OllamaProvider

    provider = OllamaProvider()
    with pytest.raises(ModelTimeoutError) as exc_info:
        _ = [c async for c in provider.stream("qwen2.5:7b", [])]
    assert exc_info.value.retryable is False  # mid-flight failure not retryable


# --- anthropic: stream() implemented (event-based async context manager) ---
# Optional `anthropic` SDK may be absent; inject a fake module. Anthropic streams
# typed events: message_start (input_tokens) / content_block_delta (text) /
# message_delta (output_tokens + stop_reason). input_tokens is cached from
# message_start and combined with output_tokens on the terminal message_delta.


class _FakeAnthropicUsage:
    def __init__(self, input_tokens=0, output_tokens=0):
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


class _FakeMessage:
    def __init__(self, input_tokens=0):
        self.usage = _FakeAnthropicUsage(input_tokens=input_tokens)


class _FakeAnthropicDelta:
    def __init__(self, text="", stop_reason=None):
        self.text = text
        self.stop_reason = stop_reason


class _FakeAnthropicEvent:
    """A typed Anthropic stream event."""

    def __init__(self, etype, **kw):
        self.type = etype
        for k, v in kw.items():
            setattr(self, k, v)


class _FakeAnthropicStream:
    """Async context manager yielding events; supports connect/midflight errors."""

    def __init__(self, events, *, midflight_after=None):
        self._events = events
        self._midflight_after = midflight_after

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._midflight_after is not None:
            # count how many already consumed via a cursor on the instance
            cur = getattr(self, "_cursor", 0)
            if cur == self._midflight_after:
                raise Exception("server dropped connection")
        cur = getattr(self, "_cursor", 0)
        if cur >= len(self._events):
            raise StopAsyncIteration
        ev = self._events[cur]
        self._cursor = cur + 1
        return ev


class _FakeAnthropicMessages:
    def __init__(self, events, *, connect_error=None, midflight_after=None):
        self._events = events
        self._connect_error = connect_error
        self._midflight_after = midflight_after

    def stream(self, **kwargs):
        if self._connect_error is not None:
            raise self._connect_error
        return _FakeAnthropicStream(self._events, midflight_after=self._midflight_after)


class _FakeAnthropicClient:
    def __init__(self, messages):
        self.messages = messages


def _install_fake_anthropic(messages):
    """Register a fake `anthropic` module whose AsyncAnthropic() returns a client."""
    fake = types.ModuleType("anthropic")
    fake.AsyncAnthropic = lambda *a, **kw: _FakeAnthropicClient(messages)
    sys.modules["anthropic"] = fake


@pytest.fixture
def anthropic_module_clean():
    for mod in list(sys.modules):
        if mod == "anthropic" or mod.endswith("models.providers.anthropic"):
            sys.modules.pop(mod, None)
    yield
    sys.modules.pop("anthropic", None)
    sys.modules.pop("hanflow.models.providers.anthropic", None)


def _anthropic_events(deltas, *, input_tokens=5, output_tokens=3, stop="end_turn"):
    """Build a canonical event stream: message_start + deltas + message_delta."""
    events = [_FakeAnthropicEvent("message_start", message=_FakeMessage(input_tokens))]
    for d in deltas:
        events.append(_FakeAnthropicEvent("content_block_delta", delta=_FakeAnthropicDelta(text=d)))
    events.append(
        _FakeAnthropicEvent(
            "message_delta",
            usage=_FakeAnthropicUsage(output_tokens=output_tokens),
            delta=_FakeAnthropicDelta(stop_reason=stop),
        )
    )
    return events


@pytest.mark.asyncio
async def test_anthropic_stream_parses_chunks(anthropic_module_clean):
    events = _anthropic_events(["你", "好"], stop="end_turn")
    _install_fake_anthropic(_FakeAnthropicMessages(events))

    from hanflow.models.providers.anthropic import AnthropicProvider

    provider = AnthropicProvider(api_key="x")
    out = [c async for c in provider.stream("claude-3-5-sonnet", [])]
    deltas = "".join(c.delta for c in out)
    assert deltas == "你好"
    assert out[-1].finish_reason == "end_turn"


@pytest.mark.asyncio
async def test_anthropic_stream_combines_usage_from_message_start_and_delta(anthropic_module_clean):
    # input_tokens on message_start=10, output_tokens on message_delta=4
    events = _anthropic_events(["hi"], input_tokens=10, output_tokens=4)
    _install_fake_anthropic(_FakeAnthropicMessages(events))

    from hanflow.models.providers.anthropic import AnthropicProvider

    provider = AnthropicProvider(api_key="x")
    out = [c async for c in provider.stream("claude-3-5-sonnet", [])]
    usage_chunk = next(c for c in out if c.usage is not None)
    assert usage_chunk.usage.input_tokens == 10  # from message_start
    assert usage_chunk.usage.output_tokens == 4  # from message_delta
    assert usage_chunk.usage.total_tokens == 14


@pytest.mark.asyncio
async def test_anthropic_stream_wraps_connection_error(anthropic_module_clean):
    # messages.stream(...) itself raises (the async-with __aenter__ path)
    _install_fake_anthropic(_FakeAnthropicMessages([], connect_error=Exception("connect refused")))

    from hanflow.models.providers.anthropic import AnthropicProvider

    provider = AnthropicProvider(api_key="x")
    with pytest.raises(ModelTimeoutError) as exc_info:
        _ = [c async for c in provider.stream("claude-3-5-sonnet", [])]
    assert exc_info.value.retryable is True  # connection failure is retryable


@pytest.mark.asyncio
async def test_anthropic_stream_midflight_error_not_retryable(anthropic_module_clean):
    # message_start + one delta, then fail mid-iteration (cursor==1)
    events = _anthropic_events(["partial"])
    _install_fake_anthropic(_FakeAnthropicMessages(events, midflight_after=1))

    from hanflow.models.providers.anthropic import AnthropicProvider

    provider = AnthropicProvider(api_key="x")
    with pytest.raises(ModelTimeoutError) as exc_info:
        _ = [c async for c in provider.stream("claude-3-5-sonnet", [])]
    assert exc_info.value.retryable is False  # mid-flight failure not retryable
