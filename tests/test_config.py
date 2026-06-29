from pathlib import Path

import pytest

from hanflow.config import ConfigValidationError, load_config


def test_load_default_minimal():
    cfg = load_config({"workspace_root": "./workspace"}, validate=False)
    assert cfg.workspace_root == "./workspace"
    assert cfg.server.inline_worker is True  # default


def test_env_override(monkeypatch):
    monkeypatch.setenv("HANFLOW_SERVER__PORT", "9000")
    cfg = load_config({"workspace_root": "./ws"}, validate=False)
    assert cfg.server.port == 9000


def test_var_placeholder_substitution(monkeypatch):
    monkeypatch.setenv("OPENAI_KEY", "sk-test")
    cfg = load_config(
        {
            "workspace_root": "./ws",
            "models": {
                "strong": {"provider": "openai", "model": "gpt-4o", "api_key": "${OPENAI_KEY}"}
            },
        },
        validate=False,
    )
    assert cfg.models["strong"].api_key == "sk-test"


def test_load_from_yaml_file(tmp_path: Path):
    yaml_text = """
workspace_root: ./ws
server:
  port: 8888
"""
    p = tmp_path / "hanflow.yaml"
    p.write_text(yaml_text)
    cfg = load_config(path=p, validate=False)
    assert cfg.server.port == 8888


def test_startup_validate_privacy_local_providers_must_exist():
    with pytest.raises(ConfigValidationError):
        load_config(
            {
                "workspace_root": "./ws",
                "models": {"strong": {"provider": "openai", "model": "gpt-4o"}},
                "routing": {
                    "privacy": {"local_providers": ["nonexistent"], "enforce": "hard"},
                },
            },
            validate=True,
        )


def test_startup_validate_dim_positive():
    # config.validate only flags dim when it's a non-positive int
    cfg = load_config(
        {
            "workspace_root": "./ws",
            "search": {
                "stores": {
                    "kb": {
                        "mode": "vector",
                        "vector": {"provider": "memory", "config": {"collection": "c", "dim": 8}},
                    }
                }
            },
        },
        validate=True,
    )
    assert cfg.workspace_root == "./ws"


def test_dim_zero_rejected():
    with pytest.raises(ConfigValidationError):
        load_config(
            {
                "workspace_root": "./ws",
                "search": {
                    "stores": {
                        "kb": {
                            "mode": "vector",
                            "vector": {
                                "provider": "memory",
                                "config": {"collection": "c", "dim": 0},
                            },
                        }
                    }
                },
            },
            validate=True,
        )
