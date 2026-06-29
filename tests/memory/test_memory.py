"""Tests for FilesystemMemory + SkillsLoader."""

from __future__ import annotations

from pathlib import Path

import pytest

from hanflow.core.errors import HanflowError
from hanflow.memory.backends.local_fs import LocalFsMemoryBackend
from hanflow.memory.filesystem import FilesystemMemory
from hanflow.memory.skills import SkillsLoader
from hanflow.observability.trace import NullTraceExporter
from hanflow.persistence.backends.sqlite import SqliteKVBackend
from hanflow.persistence.session import SessionStore


@pytest.fixture
async def mem(tmp_path: Path) -> FilesystemMemory:
    kv = SqliteKVBackend(path=str(tmp_path / "session.db"))
    await kv.setup()
    return FilesystemMemory(
        workspace_root=tmp_path / "ws",
        session_store=SessionStore(kv),
        backends={
            "scratch": LocalFsMemoryBackend(root=tmp_path / "ws" / "scratch"),
            "session": LocalFsMemoryBackend(root=tmp_path / "ws" / "session"),
            "long_term": None,
        },
    )


@pytest.mark.asyncio
async def test_scratch_write_read(mem):
    await mem.write("scratch", "note", "hello")
    entry = await mem.read("scratch", "note")
    assert entry is not None
    assert entry.value == "hello"
    assert entry.scope == "scratch"


@pytest.mark.asyncio
async def test_scratch_update_overwrites(mem):
    await mem.write("scratch", "k", 1)
    await mem.update("scratch", "k", 2)
    entry = await mem.read("scratch", "k")
    assert entry.value == 2


@pytest.mark.asyncio
async def test_scratch_delete(mem):
    await mem.write("scratch", "k", "v")
    await mem.delete("scratch", "k")
    assert await mem.read("scratch", "k") is None


@pytest.mark.asyncio
async def test_long_term_routes_to_session_store(mem):
    await mem.write_long_term("u1", "pref", {"theme": "dark"})
    assert await mem.read_long_term("u1", "pref") == {"theme": "dark"}
    keys = await mem.list_long_term("u1")
    assert "pref" in keys
    assert await mem.delete_long_term("u1", "pref") is True
    assert await mem.read_long_term("u1", "pref") is None


@pytest.mark.asyncio
async def test_list_keys_with_prefix(mem):
    await mem.write("scratch", "notes/a", 1)
    await mem.write("scratch", "notes/b", 2)
    await mem.write("scratch", "other", 3)
    keys = await mem.list_keys("scratch", prefix="notes/")
    assert set(keys) == {"notes/a", "notes/b"}


@pytest.mark.asyncio
async def test_summarize_reads_multiple_and_joins(mem):
    await mem.write("scratch", "n1", "alpha")
    await mem.write("scratch", "n2", "beta")
    summary = await mem.summarize("scratch", source_keys=["n1", "n2"])
    assert "alpha" in summary and "beta" in summary


# --- SkillsLoader --------------------------------------------------------


_SKILL_MD = """\
---
name: deep-research
description: Deep research with citations
version: "0.1.0"
trigger:
  keywords: [research, investigate, report]
  task_type: research
tools: [web_search.search, web_fetch.fetch]
---

When asked to research:
1. Break the question into sub-queries
2. Search and fetch sources
3. Cite every claim
"""


@pytest.fixture
async def loader(tmp_path: Path) -> SkillsLoader:
    (tmp_path / "deep-research.md").write_text(_SKILL_MD, encoding="utf-8")
    ldr = SkillsLoader(skills_dirs=[tmp_path], trace=NullTraceExporter())
    await ldr.load_all()
    return ldr


@pytest.mark.asyncio
async def test_load_all_parses_front_matter(loader):
    doc = await loader.load_skill("deep-research")
    assert doc.name == "deep-research"
    assert doc.description == "Deep research with citations"
    assert "research" in doc.trigger.keywords
    assert doc.tools == ["web_search.search", "web_fetch.fetch"]
    assert "Cite every claim" in doc.instructions


@pytest.mark.asyncio
async def test_match_skills_by_keyword(loader):
    matches = await loader.match_skills("please research the topic")
    assert matches
    assert matches[0].skill.name == "deep-research"
    assert matches[0].score > 0


@pytest.mark.asyncio
async def test_match_skills_no_match(loader):
    matches = await loader.match_skills("write a haiku")
    assert matches == []


@pytest.mark.asyncio
async def test_render_prompt_includes_instructions(loader):
    doc = await loader.load_skill("deep-research")
    prompt = loader.render_prompt([doc])
    assert "deep-research" in prompt
    assert "Cite every claim" in prompt


@pytest.mark.asyncio
async def test_load_skill_unknown_raises(loader):
    with pytest.raises(HanflowError):
        await loader.load_skill("ghost")
