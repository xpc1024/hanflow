# tests/isolation/ — Sandbox isolation tests

Tests for the sandbox isolation layer (`hanflow/isolation/`): the
`SandboxProvisioner` contract across `LOCAL` / `DOCKER` / `K8S` modes and
the `build_sandbox` composition root.

## Running tests

```bash
# Everything (unit + contract + real-daemon, the CI default):
make test
# or:
pytest tests/isolation/

# Unit + mocked tests only (no external dependencies, fast):
pytest tests/isolation/ -m "not docker"

# Only the real-daemon docker lifecycle tests (see below):
make test-docker
# or:
pytest -m docker -v
```

## The `docker` marker — real container tests

Four tests in `test_docker_provisioner.py` exercise a **real** docker
container (provision → exec → destroy, resource limits, cleanup, timeout).
They carry **two** decorators:

- `@pytest.mark.skipif(not HAS_DOCKER, …)` — skips locally when no docker
  daemon or `python:3.11-slim` image is available.
- `@pytest.mark.docker` — makes them selectable via `pytest -m docker` and
  individually visible in CI output.

| Environment | `pytest -m docker` result |
|---|---|
| CI (daemon + `python:3.11-slim` pre-pulled) | 4 passed |
| Local dev, no Docker Desktop running | 4 skipped (reason: `no docker daemon or python:3.11-slim image`) |
| CI, image pull failed (Docker Hub flaky) | 4 skipped + a visible `::warning::` annotation |

> The local skip is **by design**, not a bug — the real container path is
> verified in CI on every push. The image-gate step in
> `.github/workflows/ci.yml` ensures a pull failure surfaces as a warning
> rather than a silent false-green.

### Running the real-daemon tests locally

1. Start Docker Desktop (ensure `docker info` succeeds).
2. Pull the image once: `docker pull python:3.11-slim`.
3. Run: `make test-docker` (or `pytest -m docker -v`).

## Marker semantics

- **`docker`** — needs a real docker daemon + the `python:3.11-slim` image.
  These are the 4 lifecycle tests; everything else in this directory is
  pure unit or mocked.
- **`integration`** — needs external services (postgres/redis/s3); used
  elsewhere in the suite, not in this directory. Orthogonal to `docker`.

## Provisioner coverage

| Provisioner | Test file | Real daemon needed? |
|---|---|---|
| `LocalProvisioner` | `test_local_provisioner.py` | No |
| `DockerProvisioner` | `test_docker_provisioner.py` | Only the 4 `@pytest.mark.docker` tests |
| `K8sProvisioner` (stub) | `test_k8s_provisioner_stub.py` | No (still a `NotImplementedError` placeholder) |
| `build_sandbox` root | `test_build_sandbox.py`, `test_sandbox.py` | No |
