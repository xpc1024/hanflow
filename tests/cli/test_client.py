"""Tests for hanflow.cli.client.CliClient.

Uses httpx.MockTransport to exercise the real status-code → CLIError mapping
without a live server. This tests behaviour, not mock interactions.
"""

from __future__ import annotations

import httpx
import pytest

from hanflow.cli.client import CliClient
from hanflow.core.errors import CLIError, HanflowError


def _client_with_transport(transport: httpx.MockTransport) -> CliClient:
    """Build a CliClient whose httpx calls are driven by ``transport``."""
    client = CliClient(base_url="http://test")
    client._client_factory = lambda: httpx.AsyncClient(transport=transport, base_url="http://test")
    return client


def _ok(handler: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json={"run_id": "abc", "status": "running"})


def _list_ok(handler: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json=[{"run_id": "abc", "status": "succeeded"}])


@pytest.mark.asyncio
async def test_list_runs_returns_json() -> None:
    transport = httpx.MockTransport(_list_ok)
    client = _client_with_transport(transport)
    result = await client.list_runs()
    assert result == [{"run_id": "abc", "status": "succeeded"}]


@pytest.mark.asyncio
async def test_get_run_returns_json() -> None:
    transport = httpx.MockTransport(_ok)
    client = _client_with_transport(transport)
    result = await client.get_run("abc")
    assert result["run_id"] == "abc"


@pytest.mark.asyncio
async def test_get_run_404_raises_cli_error() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"detail": "run not found: abc"})

    client = _client_with_transport(httpx.MockTransport(handler))
    with pytest.raises(CLIError) as exc_info:
        await client.get_run("abc")
    assert "abc" in str(exc_info.value)


@pytest.mark.asyncio
async def test_approve_posts_decision_body() -> None:
    captured: dict[str, object] = {}

    def handler(req: httpx.Request) -> httpx.Response:
        import json

        captured["url"] = str(req.url)
        captured["method"] = req.method
        captured["body"] = json.loads(req.content)
        return httpx.Response(200, json={"run_id": "abc", "status": "resumed"})

    client = _client_with_transport(httpx.MockTransport(handler))
    result = await client.approve("abc", decided_by="alice")
    assert result["status"] == "resumed"
    assert captured["method"] == "POST"
    assert "/api/runs/abc/approve" in str(captured["url"])
    assert captured["body"] == {"decided_by": "alice"}


@pytest.mark.asyncio
async def test_edit_requires_edited_value_in_body() -> None:
    captured: dict[str, object] = {}

    def handler(req: httpx.Request) -> httpx.Response:
        import json

        captured["body"] = json.loads(req.content)
        return httpx.Response(200, json={"run_id": "abc", "status": "resumed"})

    client = _client_with_transport(httpx.MockTransport(handler))
    await client.edit("abc", decided_by="bob", edited_value={"x": 1})
    assert captured["body"] == {"decided_by": "bob", "edited_value": {"x": 1}}


@pytest.mark.asyncio
async def test_cancel_run_404_raises_cli_error() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"detail": "run not found: abc"})

    client = _client_with_transport(httpx.MockTransport(handler))
    with pytest.raises(CLIError):
        await client.cancel_run("abc")


@pytest.mark.asyncio
async def test_422_raises_cli_error() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(422, json={"detail": "reject requires a reason"})

    client = _client_with_transport(httpx.MockTransport(handler))
    with pytest.raises(CLIError):
        await client.reject("abc", decided_by="x", reason="")


@pytest.mark.asyncio
async def test_connection_error_raises_cli_error() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=req)

    client = _client_with_transport(httpx.MockTransport(handler))
    with pytest.raises(CLIError):
        await client.get_run("abc")


def test_cli_error_is_hanflow_error() -> None:
    assert issubclass(CLIError, HanflowError)


def test_default_base_url() -> None:
    client = CliClient()
    assert client.base_url == "http://localhost:8000"
