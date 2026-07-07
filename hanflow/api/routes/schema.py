"""Schema endpoints - single source of truth for the frontend.

Phase 13: _CONFIG_SCHEMA upgraded to standard JSON Schema (13 types),
plus _VALIDATION_RULES and _OUTPUT_SCHEMA for Inspector form generation,
validation mirroring, and {{}} completion.
"""

from __future__ import annotations

from typing import Any, get_args

from fastapi import APIRouter, HTTPException

from hanflow.core.dsl import NodeType, WorkflowDSL

router = APIRouter(prefix="/api/schema", tags=["schema"])

_VALID_NODE_TYPES: list[str] = list(get_args(NodeType))

_NODE_META: dict[str, dict[str, Any]] = {
    "Sequential": {"color": "#6b7280", "group": "control", "icon": "ListOrdered"},
    "Parallel": {"color": "#6b7280", "group": "control", "icon": "Columns"},
    "Loop": {"color": "#6b7280", "group": "control", "icon": "Repeat"},
    "Branch": {"color": "#6b7280", "group": "control", "icon": "GitBranch"},
    "HITL": {"color": "#eab308", "group": "control", "icon": "🔶"},
    "LLM": {"color": "#3b82f6", "group": "leaf", "icon": "MessageSquare"},
    "Tool": {"color": "#22c55e", "group": "leaf", "icon": "Wrench"},
    "Research": {"color": "#6366f1", "group": "leaf", "icon": "Search"},
    "Execution": {"color": "#f97316", "group": "leaf", "icon": "Terminal"},
    "Coordinator": {"color": "#a855f7", "group": "dynamic", "icon": "🟣"},
    "Memory": {"color": "#0ea5e9", "group": "state", "icon": "📦"},
    "Subworkflow": {"color": "#0ea5e9", "group": "state", "icon": "🔗"},
    "Knowledge": {"color": "#14b8a6", "group": "retrieval", "icon": "📚"},
}

# Standard JSON Schema for each node type's config (Phase 13 spec §3.2)
_CONFIG_SCHEMA: dict[str, dict[str, Any]] = {
    "Sequential": {"type": "object", "properties": {}},
    "Parallel": {"type": "object", "properties": {
        "join": {"type": "string", "enum": ["all", "any", "first_n"]},
        "n": {"type": "integer", "minimum": 1}}},
    "Loop": {"type": "object", "properties": {
        "max_iterations": {"type": "integer", "minimum": 1, "maximum": 1000, "default": 100},
        "condition": {"type": "string", "format": "textarea"},
        "body": {"type": "array", "items": {"type": "string"}}}},
    "Branch": {"type": "object", "properties": {
        "cases": {"type": "object", "additionalProperties": {"type": "string", "format": "textarea"}},
        "default": {"type": "string"}}},
    "HITL": {"type": "object", "properties": {
        "actions": {"type": "array", "items": {"type": "string", "enum": ["approve", "edit", "reject", "reroute"]}},
        "title": {"type": "string"},
        "description": {"type": "string", "format": "textarea"},
        "form": {"type": "object"},
        "timeout_seconds": {"type": "integer", "minimum": 1},
        "reject_branch": {"type": "string"}}},
    "LLM": {"type": "object", "properties": {
        "template": {"type": "string", "format": "textarea"},
        "prompt": {"type": "string", "format": "textarea"},
        "model": {"type": "string"},
        "role": {"type": "string", "enum": ["planner", "researcher", "coder"]}}},
    "Tool": {"type": "object", "properties": {
        "tool": {"type": "string"},
        "args": {"type": "object", "additionalProperties": True}}},
    "Research": {"type": "object", "properties": {
        "query": {"type": "string", "format": "textarea"},
        "depth": {"type": "string", "enum": ["quick", "standard", "deep"]},
        "max_sources": {"type": "integer", "minimum": 1, "maximum": 50},
        "private_kb": {"type": "string"},
        "citation": {"type": "boolean"}}},
    "Execution": {"type": "object", "properties": {
        "task": {"type": "string", "format": "textarea"},
        "sandbox": {"type": "string", "enum": ["docker", "firecracker", "none"]},
        "max_steps": {"type": "integer", "minimum": 1, "maximum": 200},
        "allow_delegate": {"type": "boolean"},
        "skills": {"type": "array", "items": {"type": "string"}},
        "tools_whitelist": {"type": "array", "items": {"type": "string"}}}},
    "Coordinator": {"type": "object", "properties": {
        "sub_agents": {"type": "array", "items": {"type": "string"}},
        "planning_model": {"type": "string"},
        "plan_hitl": {"type": "boolean"},
        "replan": {"type": "boolean"},
        "max_iterations": {"type": "integer", "minimum": 1, "maximum": 20, "default": 5},
        "success_criteria": {"type": "string", "format": "textarea"},
        "skills": {"type": "array", "items": {"type": "string"}}}},
    "Memory": {"type": "object", "properties": {
        "action": {"type": "string", "enum": ["read", "write", "update", "delete", "summarize"]},
        "key": {"type": "string"},
        "value": {},
        "scope": {"type": "string", "enum": ["scratch", "session", "long_term"]},
        "ttl_seconds": {"type": "integer", "minimum": 1},
        "source_keys": {"type": "array", "items": {"type": "string"}}}},
    "Subworkflow": {"type": "object", "properties": {
        "ref": {"type": "string"},
        "inputs": {"type": "object"},
        "version": {"type": "string"},
        "timeout_seconds": {"type": "integer", "minimum": 1}}},
    "Knowledge": {"type": "object", "properties": {
        "store": {"type": "string"},
        "query": {"type": "string", "format": "textarea"},
        "top_k": {"type": "integer", "minimum": 1, "maximum": 100, "default": 5},
        "rerank": {"type": "string"},
        "filter": {"type": "object"},
        "min_score": {"type": "number", "minimum": 0, "maximum": 1},
        "embedding": {"type": "string"}}},
}

_VALIDATION_RULES: dict[str, dict[str, Any]] = {
    "Sequential": {},
    "Parallel": {"enums": {"join": ["all", "any", "first_n"]}},
    "Loop": {"ranges": {"max_iterations": {"min": 1, "max": 1000}}},
    "Branch": {},
    "HITL": {"non_empty_if_set": ["actions"]},
    "LLM": {"alternatives": [["template", "prompt"]]},
    "Tool": {"required": ["tool"]},
    "Research": {"required": ["query"]},
    "Execution": {"required": ["task"]},
    "Coordinator": {"ranges": {"max_iterations": {"min": 1, "max": 20}}},
    "Memory": {"required": ["action", "key"],
               "enums": {"action": ["read", "write", "update", "delete", "summarize"],
                         "scope": ["scratch", "session", "long_term"]}},
    "Subworkflow": {"required": ["ref"]},
    "Knowledge": {"required": ["store", "query"]},
}

_OUTPUT_SCHEMA: dict[str, dict[str, Any]] = {
    "Sequential": {"fields": {}},
    "Parallel": {"fields": {"children_results": "array"}},
    "Loop": {"fields": {}},
    "Branch": {"fields": {}},
    "HITL": {"fields": {"action": "string", "value": "any"}},
    "LLM": {"fields": {"content": "string", "model": "string"}},
    "Tool": {"fields": {"result": "any"}},
    "Research": {"fields": {"summary": "string", "notes": "array", "sources": "array"}},
    "Execution": {"fields": {"output": "any", "status": "string", "artifacts": "array"}},
    "Coordinator": {"fields": {"achieved": "boolean", "result": "any", "iterations": "integer"}},
    "Memory": {"fields": {"value": "any"}},
    "Subworkflow": {"fields": {"ref": "string", "depth": "integer"}},
    "Knowledge": {"fields": {"chunks": "array", "count": "integer"}},
}

_DEFAULT_CONFIG: dict[str, dict[str, Any]] = {
    "Sequential": {},
    "Parallel": {"join": "all"},
    "Loop": {"max_iterations": 100},
    "Branch": {},
    "HITL": {"actions": ["approve", "edit", "reject", "reroute"]},
    "LLM": {"template": ""},
    "Tool": {"tool": "", "args": {}},
    "Research": {"query": "", "depth": "standard", "max_sources": 10},
    "Execution": {"task": "", "sandbox": "docker", "max_steps": 20},
    "Coordinator": {"sub_agents": [], "plan_hitl": False, "max_iterations": 5},
    "Memory": {"action": "read", "key": ""},
    "Subworkflow": {"ref": ""},
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
        "config_schema": _CONFIG_SCHEMA.get(node_type, {"type": "object", "properties": {}}),
        "default_config": _DEFAULT_CONFIG.get(node_type, {}),
        "validation_rules": _VALIDATION_RULES.get(node_type, {}),
        "output_schema": _OUTPUT_SCHEMA.get(node_type, {"fields": {}}),
        "visual": _NODE_META.get(node_type, {}),
    }
