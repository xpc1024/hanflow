"""Observation endpoints: trace / artifacts / download (§11.7).

v1: trace/artifacts read from the run result; download is a placeholder wired
to ArtifactStore in Phase 15 (Monitor trace replay). Full trace-tree replay
(LangSmith) lands in Phase 15.
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
        "outputs": result.get("outputs", {}),
        "trace_events": [],  # full trace replay wired in Phase 15
    }


@router.get("/api/runs/{run_id}/artifacts")
async def artifacts(run_id: str) -> list[dict[str, Any]]:
    result = _get_result(run_id)
    arts = result.get("artifacts", [])
    return [a if isinstance(a, dict) else a for a in arts]


@router.get("/api/artifacts/{run_id}/{artifact_id}/download")
async def download(run_id: str, artifact_id: str) -> dict[str, Any]:
    # Phase 15 wires this to ArtifactStore.signed_url; v1 returns a placeholder.
    return {
        "run_id": run_id,
        "artifact_id": artifact_id,
        "url": None,
        "note": "signed_url wired in Phase 15 (Monitor)",
    }
