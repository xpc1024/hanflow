"""Run endpoints: POST run / GET list / GET one / DELETE cancel (§11.7).

``post_run`` starts the run asynchronously (does not block on completion) and
spawns a background ``_drive`` task that forwards RunEvents to WS subscribers
(via ``ws.publish``) and updates the run entry's status when done. Resume
(HITL) is exposed in routes/hitl.py; streaming is WS (routes/runs_ws.py).
"""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(prefix="/api/runs", tags=["runs"])

# In-memory run registry (v1 single-process; multi-worker needs shared store).
_runs: dict[str, dict[str, Any]] = {}


class RunBody(BaseModel):
    yaml: str
    inputs: dict[str, Any] = {}


@router.post("")
async def post_run(body: RunBody, request: Request) -> dict[str, Any]:
    from hanflow.api.deps import get_hanflow

    hf = get_hanflow(request)
    handle = await hf.run(body.yaml, inputs=body.inputs, stream=True)
    entry: dict[str, Any] = {
        "run_id": handle.run_id,
        "status": "running",
        "result": None,
        "handle": handle,
    }
    _runs[handle.run_id] = entry
    asyncio.create_task(_drive(handle, entry))
    return {"run_id": handle.run_id, "status": "running"}


async def _drive(handle: Any, entry: dict[str, Any]) -> None:
    from hanflow.api.ws import publish

    try:
        async for ev in handle.stream():
            publish(handle.run_id, ev.model_dump(mode="json"))
            if ev.kind == "error":
                entry["status"] = "failed"
                break
        result = await handle.wait()
        entry["status"] = result.status
        entry["result"] = result.model_dump(mode="json")
    except Exception as exc:  # noqa: BLE001
        entry["status"] = "failed"
        entry["result"] = {"error": str(exc)}
    finally:
        publish(handle.run_id, {"__done__": True})


@router.get("")
async def list_runs() -> list[dict[str, Any]]:
    return [
        {"run_id": e["run_id"], "status": e["status"], "result": e["result"]}
        for e in _runs.values()
    ]


@router.get("/{run_id}")
async def get_run(run_id: str) -> dict[str, Any]:
    if run_id not in _runs:
        raise HTTPException(status_code=404, detail=f"run not found: {run_id}")
    e = _runs[run_id]
    return {"run_id": e["run_id"], "status": e["status"], "result": e["result"]}


@router.delete("/{run_id}")
async def cancel_run(run_id: str) -> dict[str, bool]:
    # v1: mark cancelled; full async cancellation in multi-worker Phase 17.
    if run_id in _runs:
        _runs[run_id]["status"] = "cancelled"
        return {"cancelled": True}
    raise HTTPException(status_code=404, detail=f"run not found: {run_id}")
