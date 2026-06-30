"""Workflow CRUD + validate endpoints (§11.7, §11.8)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from hanflow.core.dsl import WorkflowDSL
from hanflow.core.errors import DSLValidationError

router = APIRouter(prefix="/api/workflows", tags=["workflows"])


class WorkflowDoc(BaseModel):
    id: str
    yaml: str


class ValidateBody(BaseModel):
    yaml: str


@router.get("")
async def list_workflows(request: Request) -> list[dict[str, str]]:
    from hanflow.api.deps import get_workflow_store

    return get_workflow_store(request).list()


@router.post("")
async def create_workflow(body: WorkflowDoc, request: Request) -> dict[str, str]:
    from hanflow.api.deps import get_workflow_store

    return get_workflow_store(request).put(body.id, body.yaml)


@router.get("/{workflow_id}")
async def get_workflow(workflow_id: str, request: Request) -> dict[str, str]:
    from hanflow.api.deps import get_workflow_store

    doc = get_workflow_store(request).get(workflow_id)
    if doc is None:
        raise HTTPException(status_code=404, detail=f"workflow not found: {workflow_id}")
    return doc


@router.put("/{workflow_id}")
async def update_workflow(workflow_id: str, body: WorkflowDoc, request: Request) -> dict[str, str]:
    from hanflow.api.deps import get_workflow_store

    return get_workflow_store(request).put(workflow_id, body.yaml)


@router.delete("/{workflow_id}")
async def delete_workflow(workflow_id: str, request: Request) -> dict[str, bool]:
    from hanflow.api.deps import get_workflow_store

    ok = get_workflow_store(request).delete(workflow_id)
    if not ok:
        raise HTTPException(status_code=404, detail=f"workflow not found: {workflow_id}")
    return {"deleted": True}


@router.post("/validate")
async def validate_workflow(body: ValidateBody) -> dict[str, Any]:
    try:
        WorkflowDSL.from_yaml(body.yaml)
        return {"valid": True}
    except DSLValidationError as exc:
        return {"valid": False, "error": str(exc)}
    except Exception as exc:
        return {"valid": False, "error": str(exc)}
