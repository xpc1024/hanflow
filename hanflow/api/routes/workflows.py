"""Workflow CRUD + validate + dry-run endpoints (§11.7, §11.8, Phase 14)."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml as pyyaml
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from hanflow.core.dsl import WorkflowDSL
from hanflow.core.errors import DSLValidationError

router = APIRouter(prefix="/api/workflows", tags=["workflows"])


class WorkflowDoc(BaseModel):
    id: str
    yaml: str


class ValidateBody(BaseModel):
    yaml: str


class DryRunBody(BaseModel):
    yaml: str
    node_id: str | None = None
    inputs: dict = {}


@router.get("")
async def list_workflows(request: Request) -> list[dict[str, Any]]:
    from hanflow.api.deps import get_workflow_store

    store = get_workflow_store(request)
    items = store.list()
    result: list[dict[str, Any]] = []
    for item in items:
        wf_id = item["id"]
        yaml_text = item["yaml"]
        meta: dict[str, Any] = {
            "id": wf_id, "name": wf_id, "description": "",
            "tags": [], "nodeCount": 0, "updatedAt": None,
        }
        try:
            data = pyyaml.safe_load(yaml_text)
            if isinstance(data, dict):
                if "workflow" in data:
                    data = data["workflow"]
                meta["name"] = data.get("name", wf_id)
                meta["description"] = data.get("description", "")
                meta["nodeCount"] = len(data.get("nodes", []))
                meta["tags"] = (data.get("metadata") or {}).get("tags", [])
        except Exception:
            pass
        try:
            wf_path = Path(store.root) / f"{wf_id}.yaml"
            if wf_path.exists():
                meta["updatedAt"] = datetime.fromtimestamp(wf_path.stat().st_mtime).isoformat()
        except Exception:
            pass
        result.append(meta)
    return result


@router.post("")
async def create_workflow(body: WorkflowDoc, request: Request) -> dict[str, Any]:
    from hanflow.api.deps import get_workflow_store

    store = get_workflow_store(request)
    existing = store.get(body.id)
    if existing is not None:
        raise HTTPException(status_code=409, detail=f"workflow '{body.id}' already exists")
    store.put(body.id, body.yaml)
    return {"id": body.id, "created": True}


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
        return {"valid": True, "error": None, "errors": []}
    except DSLValidationError as exc:
        msg = str(exc)
        return {"valid": False, "error": msg, "errors": [{"message": msg}]}
    except Exception as exc:
        msg = f"YAML parse error: {exc}"
        return {"valid": False, "error": msg, "errors": [{"message": msg}]}


def _mock_output(node_type: str, cfg: dict) -> dict:
    mock_map = {
        "LLM": lambda: {"content": f"[mock] {cfg.get('template', cfg.get('prompt', ''))}", "model": "mock-model"},
        "Tool": lambda: {"result": {"mock_args": cfg.get("args", {})}},
        "Research": lambda: {"summary": "[mock research]", "notes": [], "sources": []},
        "Execution": lambda: {"output": "[mock exec]", "status": "succeeded", "artifacts": []},
        "Coordinator": lambda: {"achieved": True, "result": "[mock coordinator]", "iterations": 1},
        "Memory": lambda: {"value": "[mock memory]"},
        "Subworkflow": lambda: {"ref": cfg.get("ref", ""), "depth": 1},
        "Knowledge": lambda: {"chunks": [], "count": 0},
        "HITL": lambda: {"action": "approve", "value": "[mock approved]"},
    }
    fn = mock_map.get(node_type)
    return fn() if fn else {}


@router.post("/{workflow_id}/dry-run")
async def dry_run(workflow_id: str, body: DryRunBody, request: Request):
    """Dry-run with mock ctx, SSE stream per-node output."""

    async def generate():
        try:
            dsl = WorkflowDSL.from_yaml(body.yaml)
            for node in dsl.nodes:
                if await request.is_disconnected():
                    break
                if getattr(node, "disabled", False):
                    yield f"data: {json.dumps({'node_id': node.id, 'status': 'skipped', 'output': {}})}\n\n"
                    continue
                cfg = node.config.__pydantic_extra__ or {}
                mock_output = _mock_output(node.type, cfg)
                yield f"data: {json.dumps({'node_id': node.id, 'status': 'ok', 'output': mock_output})}\n\n"
                if body.node_id and node.id == body.node_id:
                    break
            yield f"data: {json.dumps({'done': True})}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'node_id': '*', 'status': 'error', 'error': str(exc)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
