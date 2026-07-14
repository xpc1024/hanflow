"""Lightweight async HTTP client for the hanflow CLI (§10.3).

Wraps the public REST API exposed by ``hanflow serve``. Each method makes one
HTTP request via a short-lived ``httpx.AsyncClient`` (no connection pooling is
needed for an interactive CLI), maps non-2xx responses and transport failures
to :class:`~hanflow.core.errors.CLIError`, and returns the parsed JSON body.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any, cast

import httpx

from hanflow.core.errors import CLIError

_DEFAULT_BASE_URL = "http://localhost:8000"


class CliClient:
    """Thin async wrapper over the Hanflow REST API.

    ``base_url`` defaults to the ``HANFLOW_BASE_URL`` environment variable, then
    to ``http://localhost:8000`` (the default ``hanflow serve`` address).
    """

    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = base_url or os.environ.get("HANFLOW_BASE_URL", _DEFAULT_BASE_URL)
        # Injectable factory so tests can drive a MockTransport without touching
        # the network. Production code leaves this as None and builds a plain
        # AsyncClient per request. The factory returns an already-constructed
        # ``httpx.AsyncClient`` (an async context manager); the caller is
        # responsible for closing it via ``async with``.
        self._client_factory: Callable[[], httpx.AsyncClient] | None = None

    def _new_client(self) -> httpx.AsyncClient:
        if self._client_factory is not None:
            return self._client_factory()
        return httpx.AsyncClient(base_url=self.base_url, timeout=30.0)

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: Any | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Perform one request and return the parsed JSON body.

        Raises:
            CLIError: on connection failure or any non-2xx status. The message
                embeds the HTTP status and the server's ``detail`` field when
                present, so callers can surface a single human-readable string.
        """
        try:
            async with self._new_client() as client:
                resp = await client.request(method, path, json=json, params=params)
        except httpx.HTTPError as exc:
            raise CLIError(f"request failed: {exc}") from exc

        if resp.status_code >= 400:
            detail = ""
            try:
                body = resp.json()
                detail = str(body.get("detail", "")) if isinstance(body, dict) else str(body)
            except Exception:  # noqa: BLE001 - non-JSON error body is fine
                detail = resp.text
            msg = f"HTTP {resp.status_code}: {detail}" if detail else f"HTTP {resp.status_code}"
            raise CLIError(msg)
        if resp.status_code == 204 or not resp.content:
            return None
        try:
            return resp.json()
        except Exception as exc:  # noqa: BLE001
            raise CLIError(f"invalid JSON response: {exc}") from exc

    # --- read commands ----------------------------------------------------- #
    async def list_runs(self) -> list[dict[str, Any]]:
        """List recent runs (``GET /api/runs``)."""
        return cast("list[dict[str, Any]]", await self._request("GET", "/api/runs"))

    async def get_run(self, run_id: str) -> dict[str, Any]:
        """Get a single run (``GET /api/runs/{run_id}``)."""
        return cast("dict[str, Any]", await self._request("GET", f"/api/runs/{run_id}"))

    async def get_trace(self, run_id: str) -> dict[str, Any]:
        """Get a run trace (``GET /api/runs/{run_id}/trace``)."""
        return cast("dict[str, Any]", await self._request("GET", f"/api/runs/{run_id}/trace"))

    async def get_artifacts(self, run_id: str) -> list[dict[str, Any]]:
        """List run artifacts (``GET /api/runs/{run_id}/artifacts``)."""
        return cast(
            "list[dict[str, Any]]",
            await self._request("GET", f"/api/runs/{run_id}/artifacts"),
        )

    # --- run control ------------------------------------------------------- #
    async def cancel_run(self, run_id: str) -> dict[str, Any]:
        """Cancel a run (``DELETE /api/runs/{run_id}``)."""
        return cast("dict[str, Any]", await self._request("DELETE", f"/api/runs/{run_id}"))

    # --- HITL decisions (§11.7) ------------------------------------------- #
    async def approve(
        self,
        run_id: str,
        decided_by: str,
        form: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Approve a paused HITL gate (``POST /api/runs/{run_id}/approve``)."""
        body: dict[str, Any] = {"decided_by": decided_by}
        if form is not None:
            body["form"] = form
        return cast(
            "dict[str, Any]",
            await self._request("POST", f"/api/runs/{run_id}/approve", json=body),
        )

    async def edit(
        self,
        run_id: str,
        decided_by: str,
        edited_value: Any,
        form: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Edit a paused HITL gate (``POST /api/runs/{run_id}/edit``)."""
        body: dict[str, Any] = {"decided_by": decided_by, "edited_value": edited_value}
        if form is not None:
            body["form"] = form
        return cast(
            "dict[str, Any]",
            await self._request("POST", f"/api/runs/{run_id}/edit", json=body),
        )

    async def reject(
        self,
        run_id: str,
        decided_by: str,
        reason: str,
        form: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Reject a paused HITL gate (``POST /api/runs/{run_id}/reject``)."""
        body: dict[str, Any] = {"decided_by": decided_by, "reason": reason}
        if form is not None:
            body["form"] = form
        return cast(
            "dict[str, Any]",
            await self._request("POST", f"/api/runs/{run_id}/reject", json=body),
        )

    async def reroute(
        self,
        run_id: str,
        decided_by: str,
        reroute_target: str,
        reason: str | None = None,
        form: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Reroute a paused HITL gate (``POST /api/runs/{run_id}/reroute``)."""
        body: dict[str, Any] = {
            "decided_by": decided_by,
            "reroute_target": reroute_target,
        }
        if reason is not None:
            body["reason"] = reason
        if form is not None:
            body["form"] = form
        return cast(
            "dict[str, Any]",
            await self._request("POST", f"/api/runs/{run_id}/reroute", json=body),
        )
