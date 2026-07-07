"""Observation endpoints: trace / artifacts / download (§11.7).

Phase 15: /trace returns local span tree (placeholder structure);
download returns a placeholder URL (signed_url wired in Phase 17).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["observe"])


def _get_result(run_id: str) -> dict[str, Any]:
    from hanflow.api.routes.runs import _runs

    if run_id not in _runs:
        raise HTTPException(status_code=404, detail=f"run not found: {run_id}")
    return _runs[run_id].get("result") or {}


@router.get("/api/runs/{run_id}/trace")
async def trace(run_id: str) -> dict[str, Any]:
    result = _get_result(run_id)
    return {
        "run_id": run_id,
        "trace_tree": None,  # Phase 17: wire LocalTraceProvider
        "langsmith_url": None,
        "source": "local",
    }


@router.get("/api/runs/{run_id}/artifacts")
async def artifacts(run_id: str) -> list[dict[str, Any]]:
    result = _get_result(run_id)
    arts = result.get("artifacts", [])
    return [a if isinstance(a, dict) else a for a in arts]


@router.get("/api/artifacts/{run_id}/{artifact_id}/download")
async def download(run_id: str, artifact_id: str) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "artifact_id": artifact_id,
        "url": None,
        "note": "signed_url wired in Phase 17",
    }
