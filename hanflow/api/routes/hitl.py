"""HITL endpoints: pending list + approve/edit/reject/reroute (§11.7).

``pending`` lists runs paused at a HITL gate. The 4 action endpoints build a
HITLRecord and call the run handle's ``_resume`` hook (set by Hanflow.run),
which drives the graph forward via ``Command(resume={"hitl": record})``.
reject/reroute require a reason/target respectively.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from langgraph.types import Command
from pydantic import BaseModel

from hanflow.core.result import HITLRecord

router = APIRouter(tags=["hitl"])


class DecisionBody(BaseModel):
    decided_by: str
    edited_value: Any | None = None
    reroute_target: str | None = None
    reason: str | None = None


@router.get("/api/hitl/pending")
async def pending() -> list[dict[str, Any]]:
    from hanflow.api.routes.runs import _runs

    out: list[dict[str, Any]] = []
    for run_id, entry in _runs.items():
        if entry["status"] == "paused":
            handle = entry["handle"]
            out.append(
                {
                    "run_id": run_id,
                    "payload": getattr(handle, "_pending_payload", None),
                }
            )
    return out


async def _resume(run_id: str, record: HITLRecord) -> dict[str, str]:
    from hanflow.api.routes.runs import _runs

    if run_id not in _runs:
        raise HTTPException(status_code=404, detail=f"run not found: {run_id}")
    entry = _runs[run_id]
    if entry["status"] != "paused":
        raise HTTPException(status_code=409, detail="run is not paused")
    handle = entry["handle"]
    resume_fn = getattr(handle, "_resume", None)
    if resume_fn is None:
        raise HTTPException(status_code=409, detail="resume not wired on this run")
    entry["status"] = "running"
    await resume_fn(Command(resume={"hitl": record.model_dump(mode="json")}))
    return {"run_id": run_id, "status": "resumed"}


@router.post("/api/runs/{run_id}/approve")
async def approve(run_id: str, body: DecisionBody) -> dict[str, str]:
    return await _resume(
        run_id,
        HITLRecord(
            action="approve",
            decided_by=body.decided_by,
            decided_at=datetime.now(UTC),
            duration_seconds=0.0,
        ),
    )


@router.post("/api/runs/{run_id}/edit")
async def edit(run_id: str, body: DecisionBody) -> dict[str, str]:
    if body.edited_value is None:
        raise HTTPException(status_code=422, detail="edit requires edited_value")
    return await _resume(
        run_id,
        HITLRecord(
            action="edit",
            edited_value=body.edited_value,
            decided_by=body.decided_by,
            decided_at=datetime.now(UTC),
            duration_seconds=0.0,
        ),
    )


@router.post("/api/runs/{run_id}/reject")
async def reject(run_id: str, body: DecisionBody) -> dict[str, str]:
    if not body.reason:
        raise HTTPException(status_code=422, detail="reject requires a reason")
    return await _resume(
        run_id,
        HITLRecord(
            action="reject",
            decided_by=body.decided_by,
            decided_at=datetime.now(UTC),
            duration_seconds=0.0,
        ),
    )


@router.post("/api/runs/{run_id}/reroute")
async def reroute(run_id: str, body: DecisionBody) -> dict[str, str]:
    if not body.reroute_target:
        raise HTTPException(status_code=422, detail="reroute requires reroute_target")
    return await _resume(
        run_id,
        HITLRecord(
            action="reroute",
            reroute_target=body.reroute_target,
            decided_by=body.decided_by,
            decided_at=datetime.now(UTC),
            duration_seconds=0.0,
        ),
    )
