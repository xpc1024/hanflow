import pytest

from hanflow.core.errors import ModelTimeoutError
from hanflow.models.providers.base import ModelProvider
from hanflow.models.providers.fake import FakeProvider


@pytest.mark.asyncio
async def test_fake_returns_canned_response():
    p = FakeProvider("cloud", responses={"strong": "hello"})
    resp = await p.complete("strong", [{"role": "user", "content": "hi"}])
    assert resp.content == "hello"
    assert resp.provider == "cloud"
    assert resp.usage.total_tokens >= 0


@pytest.mark.asyncio
async def test_fake_can_simulate_failure():
    p = FakeProvider("cloud", fail_with=ModelTimeoutError("timeout"))
    with pytest.raises(ModelTimeoutError):
        await p.complete("m", [])


@pytest.mark.asyncio
async def test_fake_streams_tokens():
    p = FakeProvider("cloud", stream_tokens=["a", "b", "c"])
    chunks = []
    async for ch in p.stream("m", []):
        chunks.append(ch)
    assert chunks == ["a", "b", "c"]


def test_fake_satisfies_protocol():
    assert isinstance(FakeProvider("cloud"), ModelProvider)
