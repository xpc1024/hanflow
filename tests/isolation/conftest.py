"""Fixtures for isolation tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from hanflow.observability.trace import NullTraceExporter
from hanflow.persistence.artifact import ArtifactStore
from hanflow.persistence.backends.local_fs import LocalFsArtifactBackend
from hanflow.persistence.backends.sqlite import SqliteKVBackend
from hanflow.persistence.workspace import WorkspaceManager


@pytest.fixture
async def workspace_mgr(tmp_path: Path) -> WorkspaceManager:
    kv = SqliteKVBackend(path=str(tmp_path / "snap.db"))
    await kv.setup()
    return WorkspaceManager(
        scratch_root=tmp_path / "ws",
        artifact_store=ArtifactStore(LocalFsArtifactBackend(root=tmp_path / "art")),
        session_kv=kv,
    )


@pytest.fixture
def trace():
    return NullTraceExporter()
