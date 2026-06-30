"""Hanflow FastAPI app — v1 backend (§11.7).

``build_app(hanflow)`` mounts resource routers (schema/workflows/runs/hitl/
observe) on top of the v0 health endpoint. The ``hanflow`` SDK instance is
stored on ``app.state`` for dependency injection (``deps.get_hanflow``).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, FastAPI


def build_app(hanflow: Any = None) -> FastAPI:
    """Build the FastAPI app. ``hanflow`` is the SDK instance (stored for DI)."""
    app = FastAPI(title="Hanflow", version="0.1.0")
    app.state.hanflow = hanflow

    root = APIRouter()

    @root.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(root)

    from hanflow.api.routes import schema as schema_routes

    app.include_router(schema_routes.router)
    return app
