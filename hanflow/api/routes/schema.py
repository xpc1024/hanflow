"""Schema endpoints — single source of truth for the frontend (§11.7).

``/api/schema/dsl`` returns the WorkflowDSL JSON Schema (drives TS type +
form generation). ``/api/schema/node/{type}`` returns per-primitive metadata
(validate_config rules, default config, visual hints) for the Inspector.
"""

from __future__ import annotations

from typing import Any, get_args

from fastapi import APIRouter, HTTPException

from hanflow.core.dsl import NodeType, WorkflowDSL

router = APIRouter(prefix="/api/schema", tags=["schema"])

_VALID_NODE_TYPES: list[str] = list(get_args(NodeType))

# Per-primitive visual hints + default config (mirrors detailed design §11.3).
_NODE_META: dict[str, dict[str, Any]] = {
    "Sequential": {"color": "#6b7280", "group": "control"},
    "Parallel": {"color": "#6b7280", "group": "control"},
    "Loop": {"color": "#6b7280", "group": "control"},
    "Branch": {"color": "#6b7280", "group": "control"},
    "HITL": {"color": "#eab308", "group": "control", "icon": "🔶"},
    "LLM": {"color": "#3b82f6", "group": "leaf"},
    "Tool": {"color": "#22c55e", "group": "leaf"},
    "Research": {"color": "#6366f1", "group": "leaf"},
    "Execution": {"color": "#f97316", "group": "leaf"},
    "Coordinator": {"color": "#a855f7", "group": "dynamic", "icon": "🟣"},
    "Memory": {"color": "#0ea5e9", "group": "state", "icon": "📦"},
    "Subworkflow": {"color": "#0ea5e9", "group": "state", "icon": "🔗"},
    "Knowledge": {"color": "#14b8a6", "group": "retrieval", "icon": "📚"},
}

_CONFIG_SCHEMA: dict[str, dict[str, Any]] = {
    "LLM": {"template": "string", "model": "string?"},
    "Tool": {"tool": "string", "args": "object?"},
    "HITL": {"actions": "array", "title": "string?", "description": "string?"},
    "Coordinator": {
        "sub_agents": "array",
        "plan_hitl": "boolean?",
        "max_iterations": "integer?",
        "success_criteria": "string?",
    },
    "Knowledge": {"store": "string", "query": "string", "top_k": "integer?"},
    "Memory": {"action": "string", "key": "string", "value": "any?"},
}

_DEFAULT_CONFIG: dict[str, dict[str, Any]] = {
    "LLM": {"template": ""},
    "Tool": {"tool": "", "args": {}},
    "HITL": {"actions": ["approve", "edit", "reject", "reroute"]},
    "Coordinator": {"sub_agents": [], "plan_hitl": False, "max_iterations": 5},
    "Knowledge": {"store": "", "query": "", "top_k": 5},
}


@router.get("/dsl")
async def dsl_schema() -> dict[str, Any]:
    return WorkflowDSL.model_json_schema()


@router.get("/node/{node_type}")
async def node_schema(node_type: str) -> dict[str, Any]:
    if node_type not in _VALID_NODE_TYPES:
        raise HTTPException(status_code=404, detail=f"unknown node type: {node_type}")
    return {
        "node_type": node_type,
        "config_schema": _CONFIG_SCHEMA.get(node_type, {}),
        "default_config": _DEFAULT_CONFIG.get(node_type, {}),
        "visual": _NODE_META.get(node_type, {}),
    }
