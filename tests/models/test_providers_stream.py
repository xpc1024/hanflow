"""openai/glm provider stream contract tests (§design §6, mock SDK).

Mocks the SDK class itself (``openai.AsyncOpenAI`` / ``zhipuai.ZhipuAI``)
because each provider constructs a fresh client per call via a delayed
function-local import — patching ``self._client`` is not possible.
"""

import importlib
import inspect
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
