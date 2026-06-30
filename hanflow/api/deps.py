"""Dependency injection for API routes (§11.7).

Routes resolve the Hanflow SDK instance and the WorkflowStore from
``app.state`` (set by ``build_app``). Kept as plain functions so they're
trivial to override in tests.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request

from hanflow.sdk import Hanflow


def get_hanflow(app: FastAPI | Request) -> Hanflow:
    """Resolve the Hanflow SDK instance attached to the app."""
    state = app.app.state if isinstance(app, Request) else app.state
    hanflow: Hanflow | None = getattr(state, "hanflow", None)
    if hanflow is None:
        raise RuntimeError("Hanflow instance not attached to app.state")
    return hanflow


def get_workflow_store(app: FastAPI | Request) -> Any:
    """Resolve (lazily creating) the WorkflowStore attached to the app."""
    state = app.app.state if isinstance(app, Request) else app.state
    store = getattr(state, "workflow_store", None)
    if store is None:
        from hanflow.workflows.store import WorkflowStore

        hanflow = get_hanflow(app)
        root = hanflow.config.workflows.get("root", "./workflows")
        store = WorkflowStore(root=root)
        state.workflow_store = store
    return store
