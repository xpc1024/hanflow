"""WS subscription registry: run_id → set of subscriber queues (§11.7).

``subscribe`` returns a queue that receives every RunEvent dict for a run;
``publish`` is called by the runs router's background driver. This is an
in-process pub/sub (v1 single-process; multi-worker needs Redis in Phase 17).
"""

from __future__ import annotations

import asyncio
from typing import Any

_subscribers: dict[str, set[asyncio.Queue[dict[str, Any]]]] = {}


def subscribe(run_id: str) -> asyncio.Queue[dict[str, Any]]:
    q: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
    _subscribers.setdefault(run_id, set()).add(q)
    return q


def unsubscribe(run_id: str, q: asyncio.Queue[dict[str, Any]]) -> None:
    _subscribers.get(run_id, set()).discard(q)


def publish(run_id: str, event: dict[str, Any]) -> None:
    for q in _subscribers.get(run_id, set()):
        q.put_nowait(event)
