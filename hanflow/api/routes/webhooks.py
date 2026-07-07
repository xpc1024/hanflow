"""Webhook trigger endpoints (Phase 15 Task 3).

POST /api/webhooks/{workflow_id}/{token} - trigger a run via webhook.
Token must match a trigger in workflow metadata.triggers.
"""

from __future__ import annotations

import asyncio
from typing import Any

import yaml as pyyaml
from fastapi import APIRouter, HTTPException, Request

router = APIRouter(tags=["webhooks"])

_max_concurrent = asyncio.Semaphore(10)


@router.post("/api/webhooks/{workflow_id}/{token}")
async def trigger_via_webhook(
    workflow_id: str, token: str, payload: dict, request: Request
) -> dict[str, Any]:
    from hanflow.api.deps import get_workflow_store, get_hanflow
    from hanflow.api.routes.runs import _runs, _drive
    from hanflow.api.ws import publish

    store = get_workflow_store(request)
    wf = store.get(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="workflow not found")

    data = pyyaml.safe_load(wf["yaml"])
    if isinstance(data, dict) and "workflow" in data:
        data = data["workflow"]

    triggers = (data.get("metadata") or {}).get("triggers", [])
    match = [t for t in triggers if t.get("token") == token and t.get("enabled", True)]
    if not match:
        raise HTTPException(status_code=401, detail="invalid or disabled token")

    if _max_concurrent.locked():
        raise HTTPException(status_code=429, detail="too many concurrent runs")

    async with _max_concurrent:
        hf = get_hanflow(request)
        handle = await hf.run(wf["yaml"], inputs=payload, stream=True)

        entry: dict[str, Any] = {
            "run_id": handle.run_id,
            "status": "running",
            "result": None,
            "handle": handle,
            "workflow_name": data.get("name", workflow_id),
            "started_at": _now_iso(),
            "trigger_source": f"webhook:{match[0].get('label', 'webhook')}",
        }
        _runs[handle.run_id] = entry

        import asyncio
        asyncio.create_task(_drive(handle, entry))
        return {
            "run_id": handle.run_id,
            "status": "running",
            "trigger": match[0].get("label", "webhook"),
        }


def _now_iso() -> str:
    from datetime import datetime, UTC
    return datetime.now(UTC).isoformat()
