import pytest

from hanflow.core.result import Artifact
from hanflow.persistence.artifact import ArtifactStore
from hanflow.persistence.backends.local_fs import LocalFsArtifactBackend


@pytest.fixture
def store(tmp_fs_root):
    return ArtifactStore(LocalFsArtifactBackend(root=tmp_fs_root))


def _art(i: str = "a1", content="hello") -> Artifact:
    return Artifact(id=i, kind="report", content=content, mime_type="text/plain", source_node="n")


@pytest.mark.asyncio
async def test_put_and_get(store):
    await store.put("r1", _art())
    got = await store.get("r1", "a1")
    assert got is not None
    assert got.content == "hello"


@pytest.mark.asyncio
async def test_list_by_kind(store):
    await store.put("r1", _art("a1"))
    await store.put(
        "r1",
        Artifact(
            id="a2", kind="code", content="print(1)", mime_type="text/x-python", source_node="n"
        ),
    )
    reports = await store.list("r1", kind="report")
    assert {a.id for a in reports} == {"a1"}


@pytest.mark.asyncio
async def test_delete(store):
    await store.put("r1", _art())
    assert await store.delete("r1", "a1") is True
    assert await store.get("r1", "a1") is None


@pytest.mark.asyncio
async def test_signed_url_local_fs_returns_file_url(store):
    await store.put("r1", _art())
    url = await store.signed_url("r1", "a1")
    assert "a1" in url or "r1" in url


@pytest.mark.asyncio
async def test_health(store):
    assert await store.health() is True
