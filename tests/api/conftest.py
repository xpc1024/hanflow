"""TestClient + temporary Hanflow fixture for API integration tests."""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from hanflow.api import build_app
from hanflow.config import HanflowConfig
from hanflow.sdk import Hanflow


@pytest.fixture
def app_and_hanflow(tmp_path: Path):
    cfg = HanflowConfig(workspace_root=str(tmp_path / "ws"))
    hf = Hanflow(cfg)
    app = build_app(hf)
    return app, hf


@pytest.fixture
def client(app_and_hanflow):
    _app, _ = app_and_hanflow
    with TestClient(_app) as c:
        yield c


@pytest.fixture
def hanflow_app(app_and_hanflow):
    return app_and_hanflow
