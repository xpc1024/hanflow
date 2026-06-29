"""Minimal FastAPI app (health + DSL schema endpoint) — v1 foundation (§11.7)."""

from __future__ import annotations

from typing import Any


def build_app(hanflow: Any = None) -> Any:
    """Build a FastAPI app. ``hanflow`` is the SDK instance (optional, for v1)."""
    from fastapi import FastAPI

    from hanflow.core.dsl import WorkflowDSL

    app = FastAPI(title="Hanflow", version="0.1.0")

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/schema/dsl")
    async def dsl_schema() -> dict[str, Any]:
        # Single source of truth for the frontend TS types (v1 Web Studio).
        return WorkflowDSL.model_json_schema()

    return app
