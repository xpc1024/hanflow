import pytest

from hanflow.runtime.scheduler import RunAffinityScheduler


@pytest.mark.asyncio
async def test_scheduler_disabled_is_passthrough():
    s = RunAffinityScheduler(enabled=False)
    # enqueue is a no-op (the inline worker handles dispatch); reclaim returns []
    await s.enqueue("r1", {"task": "x"})
    tasks = await s.reclaim("worker-1")
    assert tasks == []


@pytest.mark.asyncio
async def test_scheduler_hash_is_deterministic_when_enabled():
    s = RunAffinityScheduler(enabled=True, node_count=4)
    a = s.pick_node("r1")
    b = s.pick_node("r1")
    assert a == b
    assert 0 <= a < 4


def test_scheduler_disabled_pick_node_returns_none():
    s = RunAffinityScheduler(enabled=False)
    assert s.pick_node("r1") is None
