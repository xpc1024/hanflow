import pytest

from hanflow.core.result import HITLPayload
from hanflow.persistence.resume import ResumeCommand, ResumeManager


@pytest.fixture
def mgr(tmp_sqlite_path):
    from hanflow.persistence.backends.sqlite import SqliteKVBackend

    return ResumeManager(SqliteKVBackend(path=tmp_sqlite_path))


@pytest.mark.asyncio
async def test_store_and_list_paused(mgr):
    from datetime import datetime

    p = HITLPayload(
        node_id="h",
        title="t",
        description="d",
        form={},
        current_value=None,
        actions=["approve"],
        paused_at=datetime.now(),
    )
    await mgr.record_paused("r1", p)
    paused = await mgr.list_paused()
    assert len(paused) == 1
    assert paused[0].node_id == "h"


@pytest.mark.asyncio
async def test_list_paused_filter_by_user(mgr):
    from datetime import datetime

    p = HITLPayload(
        node_id="h",
        title="t",
        description="d",
        form={},
        current_value=None,
        actions=["approve"],
        paused_at=datetime.now(),
    )
    await mgr.record_paused("r1", p, user_id="u1")
    assert len(await mgr.list_paused(user_id="u1")) == 1
    assert len(await mgr.list_paused(user_id="u2")) == 0


@pytest.mark.asyncio
async def test_clear_paused_on_cancel(mgr):
    from datetime import datetime

    p = HITLPayload(
        node_id="h",
        title="t",
        description="d",
        form={},
        current_value=None,
        actions=["approve"],
        paused_at=datetime.now(),
    )
    await mgr.record_paused("r1", p)
    await mgr.cancel("r1", reason="user cancel")
    assert await mgr.list_paused() == []


def test_resume_command_kinds():
    c = ResumeCommand(kind="hitl_approve", payload={})
    assert c.kind == "hitl_approve"
    assert c.payload == {}


def test_resume_command_invalid_kind_rejected():
    with pytest.raises(Exception):
        ResumeCommand(kind="bogus", payload={})  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_resume_graph_not_yet_wired(mgr):
    # Graph-driving resume is wired in Phase 8 (orchestration); raises for now.
    with pytest.raises(NotImplementedError):
        await mgr.resume("r1", ResumeCommand(kind="hitl_approve"))
