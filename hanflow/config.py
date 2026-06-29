"""HanflowConfig — single source of truth for all subsystem config (§10.4, App. A).

Load priority (high→low): env (HANFLOW_*) > explicit dict > ./hanflow.yaml >
~/.hanflow/config.yaml > defaults. ``${VAR}`` placeholders are resolved from
env at load time. Startup validation: privacy.local_providers exist.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

from hanflow.core.errors import HanflowError

_VAR_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


class ConfigValidationError(HanflowError):
    code = "CONFIG_INVALID"


class ModelRef(BaseModel):
    provider: str
    model: str
    api_key: str | None = None
    base_url: str | None = None


class BudgetConfig(BaseModel):
    max_cost_per_run_usd: float = 1.0
    warn_at: float = 0.8


class PrivacyConfigSection(BaseModel):
    local_providers: list[str] = []
    enforce: str = "hard"
    audit: bool = True


class RoutingConfig(BaseModel):
    default: str | None = None
    roles: dict[str, str] = {}
    tasks: dict[str, str] = {}
    fallback_chain: list[str] = []
    budget: BudgetConfig = BudgetConfig()
    privacy: PrivacyConfigSection = PrivacyConfigSection()


class StoreConfig(BaseModel):
    mode: str = "vector"
    vector: dict[str, Any] = {}
    fulltext: dict[str, Any] = {}
    embedding: str | None = "default"
    fusion: dict[str, Any] = {}
    index_sync: str = "dual"


class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    inline_worker: bool = True


class HanflowConfig(BaseModel):
    workspace_root: str = "./workspace"
    models: dict[str, ModelRef] = {}
    routing: RoutingConfig = RoutingConfig()
    mcp_servers: dict[str, Any] = {}
    search: dict[str, Any] = {}  # stores/embeddings/rerankers/indexing
    embeddings: dict[str, Any] = {}
    rerankers: dict[str, Any] = {}
    memory: dict[str, Any] = {}
    skills: dict[str, Any] = {}
    persistence: dict[str, Any] = {}
    observability: dict[str, Any] = {}
    workspace: dict[str, Any] = {}
    workflows: dict[str, Any] = {}
    server: ServerConfig = ServerConfig()


def _resolve_placeholders(value: Any) -> Any:
    if isinstance(value, str):
        return _VAR_RE.sub(lambda m: os.environ.get(m.group(1), m.group(0)), value)
    if isinstance(value, dict):
        return {k: _resolve_placeholders(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_placeholders(v) for v in value]
    return value


def load_config(
    data: dict[str, Any] | None = None,
    *,
    path: str | Path | None = None,
    validate: bool = True,
) -> HanflowConfig:
    """Load config from explicit dict and/or YAML file, apply env overrides."""
    merged: dict[str, Any] = {}
    # 1. file
    if path is not None:
        p = Path(path)
        if p.exists():
            merged.update(yaml.safe_load(p.read_text(encoding="utf-8")) or {})
    elif data is None:
        for candidate in (Path("./hanflow.yaml"), Path.home() / ".hanflow" / "config.yaml"):
            if candidate.exists():
                merged.update(yaml.safe_load(candidate.read_text(encoding="utf-8")) or {})
                break
    # 2. explicit dict overrides file
    if data:
        merged.update(data)
    # 3. env overrides (HANFLOW_SECTION__KEY)
    for k, v in list(os.environ.items()):
        if k.startswith("HANFLOW_"):
            parts = k[len("HANFLOW_") :].lower().split("__")
            node = merged
            for part in parts[:-1]:
                node = node.setdefault(part, {})
            node[parts[-1]] = _coerce(v)
    # 4. placeholder substitution
    merged = _resolve_placeholders(merged)
    cfg = HanflowConfig.model_validate(merged)
    if validate:
        _startup_validate(cfg)
    return cfg


def _coerce(v: str) -> Any:
    if v.lower() in ("true", "false"):
        return v.lower() == "true"
    try:
        return int(v)
    except ValueError:
        try:
            return float(v)
        except ValueError:
            return v


def _startup_validate(cfg: HanflowConfig) -> None:
    # privacy.local_providers must reference defined models
    for lp in cfg.routing.privacy.local_providers:
        if lp not in cfg.models:
            raise ConfigValidationError(f"privacy.local_providers references unknown model: {lp!r}")
    # store dim sanity-check (positive int if present)
    stores = (cfg.search or {}).get("stores", {})
    for name, store in stores.items():
        if not isinstance(store, dict):
            continue
        v = store.get("vector", {})
        vcfg = v.get("config", {}) if isinstance(v, dict) else {}
        dim = vcfg.get("dim")
        if dim is not None and (not isinstance(dim, int) or dim <= 0):
            raise ConfigValidationError(f"store {name!r} has invalid dim {dim!r}")
