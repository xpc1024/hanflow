"""WS pub/sub mechanism tests (reliable; end-to-end WS over TestClient is racy
with the background _drive task, so we test the subscribe/publish core here
and rely on Phase 15 + Playwright for full end-to-end WS coverage)."""

import asyncio

import pytest

from hanflow.api.ws import publish, subscribe, unsubscribe


@pytest.mark.asyncio
async def test_subscribe_then_publish_delivers():
    q = subscribe("r1")
    publish("r1", {"kind": "node_end", "node_id": "a"})
    publish("r1", {"__done__": True})
    first = await asyncio.wait_for(q.get(), timeout=1.0)
    assert first["kind"] == "node_end"
    second = await asyncio.wait_for(q.get(), timeout=1.0)
    assert second["__done__"] is True
    unsubscribe("r1", q)


@pytest.mark.asyncio
async def test_unsubscribe_stops_delivery():
    q = subscribe("r2")
    unsubscribe("r2", q)
    publish("r2", {"kind": "node_end"})
    # queue should remain empty after unsubscribe
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(q.get(), timeout=0.2)


@pytest.mark.asyncio
async def test_publish_to_no_subscribers_is_noop():
    # no exception when publishing to a run with no subscribers
    publish("ghost-run", {"kind": "node_end"})


@pytest.mark.asyncio
async def test_multiple_subscribers_each_get_events():
    q1 = subscribe("r3")
    q2 = subscribe("r3")
    publish("r3", {"kind": "node_end", "node_id": "x"})
    assert (await asyncio.wait_for(q1.get(), timeout=1.0))["node_id"] == "x"
    assert (await asyncio.wait_for(q2.get(), timeout=1.0))["node_id"] == "x"
    unsubscribe("r3", q1)
    unsubscribe("r3", q2)
