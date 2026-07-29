# Changelog

All notable changes to this project are documented here. Versions follow
[Semantic Versioning](https://semver.org/).

## 1.2.1 — 2026-07-29

### Fixed

- **S0 quality gates green again.** Cleared pre-existing tech debt that was
  blocking `make ci` (lint + typecheck). All changes are annotation / format /
  import hygiene with **zero runtime behaviour change**:
  - `models/providers/base.py`: added `__all__` to fix `StreamChunk` /
    `TokenUsage` re-export — resolved 16 mypy `attr-defined` errors across 13
    provider/router files (real contract bug, not a false positive).
  - `isolation/docker_provisioner.py`: typed `_import_aiodocker` return and
    added a `pyproject.toml` mypy override for `aiodocker` (optional extra,
    ships no `py.typed` marker).
  - `api/routes/{workflows,webhooks}.py`: `dict` → `dict[str, Any]`, return
    annotations on `dry_run` / `_mock_output` / `generate`.
  - `api/routes/{observe,schema,workflows}.py`: dropped unused vars/imports,
    fixed `E501` / `E741` / `F841`.
  - `ruff format` applied across 25 files (incl. prior cycle's `isolation/`,
    `runtime/`, `core/` files that missed formatting before commit).

### Gates

- `ruff check` — 0 errors (was 15)
- `ruff format --check` — clean (was 25 files)
- `mypy hanflow` — 0 errors (was 28)
- `pytest` — 417 passed, 5 skipped (no regression; +6 from PR #5)

## 1.2.0 — 2026-07-21

### Added

- DOCKER sandbox isolation (`isolation/docker_provisioner.py`,
  `core/sandbox_contract.py`, `runtime/build_sandbox.py`): real container
  lifecycle via `aiodocker` with resource limits, workspace bind mount, and
  network policy. `LocalProvisioner` + `K8sProvisioner` stub complete the
  LOCAL/DOCKER/K8S/NONE isolation modes (CHARTER §3).
