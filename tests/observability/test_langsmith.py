from unittest.mock import MagicMock

import pytest

from hanflow.observability.providers.langsmith import LangSmithTraceExporter


def _fake_client():
    client = MagicMock()
    client.create_run = MagicMock()
    client.update_run = MagicMock()
    return client


@pytest.mark.asyncio
async def test_langsmith_export_creates_and_updates_runs():
    client = _fake_client()
    exp = LangSmithTraceExporter(client=client, project="hanflow-test")
    async with exp.span("workflow.run"):
        await exp.event("token", count=5)
    await exp.flush()

    assert client.create_run.called
    # On close, the run is updated with end_time
    assert client.update_run.called


@pytest.mark.asyncio
async def test_langsmith_nested_runs_parent_link():
    client = _fake_client()
    exp = LangSmithTraceExporter(client=client, project="p")
    async with exp.span("parent"), exp.span("child"):
        pass
    await exp.flush()

    create_calls = client.create_run.call_args_list
    assert len(create_calls) == 2
    # Spans close inner-first, so the buffer order is [child, parent]. Find the
    # child call by name and assert it references the parent as parent_run_id.
    child_call = next(c for c in create_calls if c.kwargs.get("name") == "child")
    assert child_call.kwargs.get("parent_run_id") is not None


@pytest.mark.asyncio
async def test_from_config_builds_with_project():
    # api_key provided so Client() doesn't require env; real SDK not called here.
    exp = LangSmithTraceExporter.from_config(
        {"backend": "langsmith", "api_key": "ls__x", "project": "p"}
    )
    assert exp.project == "p"


@pytest.mark.asyncio
async def test_error_span_exported_with_error_status():
    client = _fake_client()
    exp = LangSmithTraceExporter(client=client, project="p")
    with pytest.raises(ValueError):
        async with exp.span("bad"):
            raise ValueError("boom")
    await exp.flush()
    # update_run should carry error info on the failed span
    update_kwargs = client.update_run.call_args.kwargs
    assert update_kwargs.get("error") is not None
