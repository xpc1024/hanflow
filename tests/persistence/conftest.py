"""Fixtures: temp sqlite db and local_fs root for persistence tests."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def tmp_sqlite_path(tmp_path: Path) -> Path:
    return tmp_path / "test.db"


@pytest.fixture
def tmp_fs_root(tmp_path: Path) -> Path:
    root = tmp_path / "fs"
    root.mkdir()
    return root


@pytest.fixture
def tmp_workspace_root(tmp_path: Path) -> Path:
    root = tmp_path / "workspace"
    root.mkdir()
    return root
