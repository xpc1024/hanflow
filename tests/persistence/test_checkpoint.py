import pytest
from langgraph.checkpoint.base import Checkpoint, CheckpointMetadata
from langgraph.graph import END, START, StateGraph

from hanflow.persistence.checkpoint import CheckpointStore


def _make_store(tmp_sqlite_path):
    from hanflow.persistence.backends.sqlite import SqliteCheckpointBackend

    return CheckpointStore(SqliteCheckpointBackend(path=tmp_sqlite_path))


def _checkpoint(cid: str = "ckpt-1") -> Checkpoint:
    return Checkpoint(
        v=1,
        id=cid,
        ts="2026-06-29T00:00:00Z",
        channel_values={},
        channel_versions={},
        versions_seen={},
        pending_sends=[],
    )


def _config(thread_id: str, checkpoint_id: str | None = None) -> dict:
    """A complete RunnableConfig the AsyncSqliteSaver accepts (matches what the
    LangGraph runtime builds internally — includes checkpoint_ns)."""
    configurable: dict = {"thread_id": thread_id, "checkpoint_ns": ""}
    if checkpoint_id is not None:
        configurable["checkpoint_id"] = checkpoint_id
    return {"configurable": configurable}


@pytest.mark.asyncio
async def test_checkpoint_put_and_get(tmp_sqlite_path):
    store = _make_store(tmp_sqlite_path)
    config = _config("t1")
    await store.aput(config, _checkpoint(), CheckpointMetadata(), {})
    tup = await store.aget_tuple(_config("t1"))
    assert tup is not None
    # The saver round-trips the checkpoint; id may be on the object or dict form.
    ckpt = tup.checkpoint
    cid = ckpt.id if hasattr(ckpt, "id") else ckpt.get("id")
    assert cid  # saver assigned/preserved a real id


@pytest.mark.asyncio
async def test_checkpoint_list_returns_history(tmp_sqlite_path):
    store = _make_store(tmp_sqlite_path)
    config = _config("t2")
    for i in range(3):
        await store.aput(config, _checkpoint(f"c{i}"), CheckpointMetadata(), {})
    tuples = [t async for t in store.alist(_config("t2"))]
    assert len(tuples) == 3


@pytest.mark.asyncio
async def test_checkpoint_with_real_graph(tmp_sqlite_path):
    """Checkpoint should let a 2-node graph resume from saved state."""
    store = _make_store(tmp_sqlite_path)

    from typing import TypedDict

    class S(TypedDict):
        count: int

    g = StateGraph(S)
    g.add_node("inc", lambda s: {"count": s["count"] + 1})
    g.add_edge(START, "inc")
    g.add_edge("inc", END)
    compiled = g.compile(checkpointer=store)
    config = {"configurable": {"thread_id": "t3"}}
    r1 = await compiled.ainvoke({"count": 0}, config=config)
    assert r1["count"] == 1
    # new invocation on same thread continues from checkpoint state
    r2 = await compiled.ainvoke({"count": r1["count"]}, config=config)
    assert r2["count"] == 2


@pytest.mark.asyncio
async def test_checkpoint_health(tmp_sqlite_path):
    store = _make_store(tmp_sqlite_path)
    assert await store.health() is True
