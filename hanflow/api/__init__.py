"""Hanflow FastAPI app — v1 backend (§11.7).

``build_app(hanflow)`` mounts resource routers (schema/workflows/runs/hitl/
observe) on top of the v0 health endpoint. The ``hanflow`` SDK instance is
stored on ``app.state`` for dependency injection (``deps.get_hanflow``).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware


def build_app(hanflow: Any = None) -> FastAPI:
    """Build the FastAPI app. ``hanflow`` is the SDK instance (stored for DI)."""
    app = FastAPI(title="Hanflow", version="0.1.0")
    app.state.hanflow = hanflow

    # CORS: allow frontend dev server (localhost:3000) to call API
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    root = APIRouter()

    @root.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(root)

    from hanflow.api.routes import (
        hitl as hitl_routes,
    )
    from hanflow.api.routes import (
        observe as observe_routes,
    )
    from hanflow.api.routes import (
        runs as runs_routes,
    )
    from hanflow.api.routes import (
        runs_ws as runs_ws_routes,
    )
    from hanflow.api.routes import (
        schema as schema_routes,
    )
    from hanflow.api.routes import (
        workflows as workflows_routes,
    )

    app.include_router(schema_routes.router)
    app.include_router(workflows_routes.router)
    app.include_router(runs_routes.router)
    app.include_router(runs_ws_routes.router)
    app.include_router(hitl_routes.router)
    app.include_router(observe_routes.router)

    from hanflow.api.routes import webhooks as webhooks_routes
    app.include_router(webhooks_routes.router)

    return app
