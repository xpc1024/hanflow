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

import importlib
import inspect
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


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "modname,clsname",
    [
        ("anthropic", "AnthropicProvider"),
        ("ollama", "OllamaProvider"),
        ("deepseek", "DeepSeekProvider"),
        ("vllm", "VLLMProvider"),
    ],
)
async def test_placeholder_providers_raise_not_implemented(modname, clsname):
    mod = importlib.import_module(f"hanflow.models.providers.{modname}")
    cls = getattr(mod, clsname, None)
    if cls is None:
        # fall back to first *Provider type in the module
        cls = next(v for k, v in vars(mod).items() if isinstance(v, type) and "Provider" in k)
    params = inspect.signature(cls.__init__).parameters
    kwargs: dict = {}
    if "api_key" in params:
        kwargs["api_key"] = "x"
    provider = cls(**kwargs)
    with pytest.raises(NotImplementedError):
        _ = [c async for c in provider.stream("m", [])]


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
        {"message": {"content": "lo"}, "done": True, "done_reason": "stop",
         "prompt_eval_count": 5, "eval_count": 2},
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
        {"message": {"content": ""}, "done": True, "done_reason": "stop",
         "prompt_eval_count": 10, "eval_count": 4},
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
