"""Tests for ResearchAtom + ExecutionAtom (monkeypatched sub-steps, no network)."""

from __future__ import annotations

import pytest

from hanflow.atoms.execution import ExecutionAtom, ExecutionOptions
from hanflow.atoms.research import ResearchAtom, ResearchOptions

# --- Research ---------------------------------------------------------------


@pytest.mark.asyncio
async def test_research_quick_single_query(ctx, monkeypatch):
    atom = ResearchAtom()

    async def fake_search(query, max_results):
        return [{"url": "https://x", "title": "X", "snippet": "snip", "content": "body about X"}]

    async def fake_crawl(url, **kw):
        return {"markdown": "full body about X", "url": url, "title": "X"}

    monkeypatch.setattr(atom, "_search", fake_search)
    monkeypatch.setattr(atom, "_crawl", fake_crawl)

    result = await atom.run(
        ctx,
        inputs={},
        options=ResearchOptions(query="what is X", depth="quick", max_sources=3),
    )
    assert result.sources
    assert result.sources[0].kind == "web"
    assert result.sources[0].url == "https://x"


@pytest.mark.asyncio
async def test_research_private_kb_merged(ctx, monkeypatch):
    atom = ResearchAtom()

    async def fake_search(query, max_results):
        return [{"url": "https://x", "title": "X", "snippet": "s", "content": "web about X"}]

    async def fake_crawl(url, **kw):
        return {"markdown": "web about X", "url": url, "title": "X"}

    async def fake_private(c, options):
        return [
            {
                "url": None,
                "title": "private",
                "snippet": "private knowledge",
                "content": "private knowledge about X",
                "source_id": "src-priv",
                "kind": "private_kb",
                "credibility": 0.9,
            }
        ]

    monkeypatch.setattr(atom, "_search", fake_search)
    monkeypatch.setattr(atom, "_crawl", fake_crawl)
    monkeypatch.setattr(atom, "_search_private_kb", fake_private)

    result = await atom.run(
        ctx,
        inputs={},
        options=ResearchOptions(query="X", depth="quick", private_kb="docs", private_top_k=3),
    )
    kinds = {s.kind for s in result.sources}
    assert "web" in kinds
    assert "private_kb" in kinds


@pytest.mark.asyncio
async def test_research_depth_standard_three_queries(ctx, monkeypatch):
    atom = ResearchAtom()
    calls: list[str] = []

    async def fake_search(query, max_results):
        calls.append(query)
        return [{"url": f"https://{query}", "title": query, "snippet": "s", "content": query}]

    async def fake_crawl(url, **kw):
        return {"markdown": url, "url": url, "title": url}

    monkeypatch.setattr(atom, "_search", fake_search)
    monkeypatch.setattr(atom, "_crawl", fake_crawl)

    await atom.run(ctx, inputs={}, options=ResearchOptions(query="topic X", depth="standard"))
    assert len(calls) == 3


# --- Execution --------------------------------------------------------------


@pytest.mark.asyncio
async def test_execution_completes_when_todos_done(ctx, monkeypatch):
    atom = ExecutionAtom()

    async def fake_plan(c, task):
        return ["step 1", "step 2"]

    async def fake_assess(c, todos, artifacts, task):
        return all(t.startswith("done:") for t in todos)

    monkeypatch.setattr(atom, "_init_plan", fake_plan)
    monkeypatch.setattr(atom, "_assess", fake_assess)

    result = await atom.run(
        ctx, inputs={}, options=ExecutionOptions(task="do thing", max_steps=5, sandbox="none")
    )
    assert result.output["status"] == "succeeded"
    assert result.output["reason"] == "completed"


@pytest.mark.asyncio
async def test_execution_delegates_when_allow_delegate(ctx, monkeypatch):
    atom = ExecutionAtom()
    delegated: list[str] = []

    async def fake_plan(c, task):
        return ["main", "delegate:subtask"]

    async def fake_assess(c, todos, artifacts, task):
        return all(t.startswith("done:") for t in todos)

    async def fake_delegate(c, sub_task):
        delegated.append(sub_task)
        return {"status": "succeeded", "output": "sub result"}

    monkeypatch.setattr(atom, "_init_plan", fake_plan)
    monkeypatch.setattr(atom, "_assess", fake_assess)
    monkeypatch.setattr(atom, "_delegate", fake_delegate)

    result = await atom.run(
        ctx,
        inputs={},
        options=ExecutionOptions(task="do", max_steps=5, sandbox="none", allow_delegate=True),
    )
    assert "subtask" in delegated
    assert result.output["status"] == "succeeded"


@pytest.mark.asyncio
async def test_execution_max_steps_exceeded(ctx, monkeypatch):
    atom = ExecutionAtom()

    async def fake_plan(c, task):
        return ["never done"]

    async def fake_assess(c, todos, artifacts, task):
        return False  # never complete

    monkeypatch.setattr(atom, "_init_plan", fake_plan)
    monkeypatch.setattr(atom, "_assess", fake_assess)

    result = await atom.run(
        ctx, inputs={}, options=ExecutionOptions(task="x", max_steps=2, sandbox="none")
    )
    assert result.output["status"] == "failed"
    assert result.output["reason"] == "max_steps_exceeded"
