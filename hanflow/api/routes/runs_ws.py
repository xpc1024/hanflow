"""WS endpoint: GET /api/runs/{id}/stream (§11.7).

Streams RunEvents for a run to the connected browser. Events arrive via the
in-process pub/sub (``ws.subscribe``); the ``__done__`` marker closes the socket.
"""

from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["runs"])


@router.websocket("/api/runs/{run_id}/stream")
async def run_stream(ws: WebSocket, run_id: str) -> None:
    from hanflow.api.ws import subscribe, unsubscribe

    await ws.accept()
    q = subscribe(run_id)
    try:
        while True:
            event = await q.get()
            await ws.send_json(event)
            if event.get("__done__"):
                break
    except WebSocketDisconnect:
        pass
    finally:
        unsubscribe(run_id, q)
