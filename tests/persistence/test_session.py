import pytest

from hanflow.persistence.backends.sqlite import SqliteKVBackend
from hanflow.persistence.session import Session, SessionStore


@pytest.fixture
async def store(tmp_sqlite_path):
    kv = SqliteKVBackend(path=tmp_sqlite_path)
    await kv.setup()
    return SessionStore(kv)


@pytest.mark.asyncio
async def test_create_and_get_session(store):
    sid = await store.create_session(
        Session(session_id="s1", created_at="2026-06-29T00:00:00", updated_at="2026-06-29T00:00:00")
    )
    assert sid == "s1"
    got = await store.get_session("s1")
    assert got is not None
    assert got.session_id == "s1"
    assert got.status == "active"


@pytest.mark.asyncio
async def test_list_sessions_by_status(store):
    await store.create_session(
        Session(session_id="a", created_at="t", updated_at="t", status="active")
    )
    await store.create_session(
        Session(session_id="b", created_at="t", updated_at="t", status="closed")
    )
    active = await store.list_sessions(status="active")
    assert {s.session_id for s in active} == {"a"}


@pytest.mark.asyncio
async def test_close_session(store):
    await store.create_session(Session(session_id="s", created_at="t", updated_at="t"))
    await store.close_session("s")
    got = await store.get_session("s")
    assert got.status == "closed"


@pytest.mark.asyncio
async def test_long_term_memory_crud(store):
    await store.put_memory("u1", "pref", {"theme": "dark"})
    v = await store.get_memory("u1", "pref")
    assert v == {"theme": "dark"}
    keys = await store.list_memory("u1")
    assert "pref" in keys
    assert await store.delete_memory("u1", "pref") is True
    assert await store.get_memory("u1", "pref") is None


@pytest.mark.asyncio
async def test_update_session_run_ids(store):
    await store.create_session(Session(session_id="s", created_at="t", updated_at="t"))
    await store.update_session("s", run_ids=["r1", "r2"])
    got = await store.get_session("s")
    assert got.run_ids == ["r1", "r2"]


@pytest.mark.asyncio
async def test_list_sessions_by_user(store):
    await store.create_session(
        Session(session_id="a", created_at="t", updated_at="t", user_id="u1")
    )
    await store.create_session(
        Session(session_id="b", created_at="t", updated_at="t", user_id="u2")
    )
    mine = await store.list_sessions(user_id="u1")
    assert {s.session_id for s in mine} == {"a"}
