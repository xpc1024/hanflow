"""HITL endpoints: pending list + approve/edit/reject/reroute + history (§11.7, Phase 16).

Phase 16 additions:
- DecisionBody has form + reason fields
- _resume has 409 concurrency guard (decided_by set) + duration calc
- _hitl_history list + GET /api/hitl/history endpoint
- HITLRecord carries reason + form for audit
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from langgraph.types import Command
from pydantic import BaseModel

from hanflow.core.result import HITLRecord

router = APIRouter(tags=["hitl"])

_hitl_history: list[dict[str, Any]] = []


class DecisionBody(BaseModel):
    decided_by: str
    edited_value: Any | None = None
    reroute_target: str | None = None
    reason: str | None = None
    form: dict[str, Any] | None = None


@router.get("/api/hitl/pending")
async def pending() -> list[dict[str, Any]]:
    from hanflow.api.routes.runs import _runs

    out: list[dict[str, Any]] = []
    for run_id, entry in _runs.items():
        if entry["status"] == "paused":
            handle = entry["handle"]
            payload = getattr(handle, "_pending_payload", None)
            out.append({"run_id": run_id, "payload": payload})
    return out


@router.get("/api/hitl/history")
async def history(limit: int = 100) -> list[dict[str, Any]]:
    return _hitl_history[-limit:]


async def _resume(run_id: str, record: HITLRecord) -> dict[str, str]:
    from hanflow.api.routes.runs import _runs

    if run_id not in _runs:
        raise HTTPException(status_code=404, detail=f"run not found: {run_id}")
    entry = _runs[run_id]
    # H4 修正: use decided_by guard instead of status (avoid stuck "resuming")
    if entry.get("decided_by") is not None:
        raise HTTPException(
            status_code=409, detail=f"Already decided by {entry['decided_by']}"
        )
    handle = entry["handle"]
    resume_fn = getattr(handle, "_resume", None)
    if resume_fn is None:
        raise HTTPException(status_code=409, detail="resume not wired on this run")

    # Duration: real calc from payload paused_at (H2/M2 fix)
    payload = getattr(handle, "_pending_payload", None)
    paused_at = None
    if isinstance(payload, dict):
        pa = payload.get("paused_at")
        if isinstance(pa, str):
            paused_at = datetime.fromisoformat(pa.replace("Z", "+00:00"))
        elif isinstance(pa, datetime):
            paused_at = pa
    decided_at = datetime.now(UTC)
    duration = (decided_at - paused_at).total_seconds() if paused_at else 0.0
    record = record.model_copy(update={"duration_seconds": duration})

    entry["decided_by"] = record.decided_by
    entry["status"] = "running"
    await resume_fn(Command(resume={"hitl": record.model_dump(mode="json")}))

    # Persist to history
    _hitl_history.append(
        {
            **record.model_dump(mode="json"),
            "run_id": run_id,
            "decided_at": decided_at.isoformat(),
        }
    )
    if len(_hitl_history) > 1000:
        _hitl_history.pop(0)

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
            form=body.form,
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
            form=body.form,
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
            reason=body.reason,
            form=body.form,
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
            reason=body.reason,
            form=body.form,
        ),
    )
