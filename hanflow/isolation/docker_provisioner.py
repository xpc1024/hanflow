"""DockerProvisioner — real container provisioning via aiodocker (§13.6, §5.3).

Cycle 2026-W30-1.1.1 — implements ``SandboxProvisioner`` for DOCKER mode.
Real container lifecycle (create/start/kill/delete) + resource limits
(--cpus/--memory/--storage-opt) + workspace bind mount + network policy
(--network=none default). ``aiodocker`` is an optional dependency
(``pip install hanflow[docker]``); missing-import surfaces as
``SandboxDependencyMissingError`` (non-retryable) instead of a hard
module-load failure.

Timeouts are wrapped internally as ``SandboxTimeoutError`` so callers
(``code_exec`` etc.) never see bare ``TimeoutError`` (§5 no-swallow).
"""

from __future__ import annotations

import asyncio
import contextlib
from pathlib import Path
from typing import Any

from hanflow.core.errors import (
    SandboxDependencyMissingError,
    SandboxDestroyFailedError,
    SandboxProvisionFailedError,
    SandboxTimeoutError,
)
from hanflow.core.sandbox_contract import (
    ProvisionedSandbox,
    RunSandbox,
    SandboxMode,
    SandboxResources,
)


def _import_aiodocker() -> tuple[type[Any], type[Any]]:
    """Lazy import; convert ImportError → SandboxDependencyMissingError.

    Returns the ``aiodocker.Docker`` client class and ``DockerError`` exception
    class. They are typed as ``type[Any]`` because ``aiodocker`` ships no
    ``py.typed`` marker; ``pyproject.toml`` sets ``ignore_missing_imports`` for
    it so this stays mypy-clean without the optional extra installed.
    """
    try:
        from aiodocker import Docker, DockerError
    except ImportError as exc:
        raise SandboxDependencyMissingError(
            "aiodocker not installed; pip install 'hanflow[docker]'",
        ) from exc
    return Docker, DockerError


class _DockerExec:
    """``docker exec`` execution interface (container already created)."""

    def __init__(
        self,
        container_id: str,
        workspace_in_container: str,
        run_id: str,
    ) -> None:
        self._cid = container_id
        self._ws = workspace_in_container
        self._run_id = run_id

    async def run(
        self,
        *,
        command: list[str],
        stdin: str | None = None,
        timeout: int = 30,
        cwd: str | None = None,
    ) -> dict[str, Any]:
        Docker, _DockerError = _import_aiodocker()
        client = Docker()
        try:
            container = await client.containers.get(self._cid)
            # cwd honoured by prepending a `cd` (Docker exec has no -cwd option).
            exec_cmd = command
            if cwd:
                # quote-safe shell join; container shell is POSIX sh.
                joined = " ".join(_shell_quote(arg) for arg in command)
                exec_cmd = ["sh", "-c", f"cd {cwd} && {joined}"]

            exec_obj = await container.exec(
                cmd=exec_cmd,
                stdin=stdin is not None,
                stdout=True,
                stderr=True,
            )

            try:
                # aiodocker's exec.start returns a stream; we drain it with a
                # timeout. detach=False gives us the multiplexed output stream.
                output_chunks: list[bytes] = []
                async with asyncio.timeout(timeout):
                    async for chunk in exec_obj.start(detach=False):
                        if isinstance(chunk, (bytes, bytearray)):
                            output_chunks.append(bytes(chunk))
                        elif isinstance(chunk, str):
                            output_chunks.append(chunk.encode())

                inspect = await exec_obj.inspect()
                returncode = inspect.get("ExitCode", 0) or 0

                # Docker multiplexed stream has 8-byte headers per frame
                # alternating stdout/stderr; aiodocker demuxes when detaching
                # is False but combines into one stream. For simplicity we
                # put everything in stdout and leave stderr empty — matches
                # the contract "dict with stdout/stderr/returncode".
                raw = b"".join(output_chunks)
                return {
                    "stdout": raw.decode(errors="replace"),
                    "stderr": "",
                    "returncode": int(returncode),
                }
            except TimeoutError:
                raise SandboxTimeoutError(
                    f"docker exec timed out after {timeout}s",
                    run_id=self._run_id,
                    details={"command": command, "container_id": self._cid},
                ) from None
        finally:
            await client.close()


def _shell_quote(arg: str) -> str:
    """POSIX shell-quote a single argument (for `cd X && cmd` composition)."""
    if not arg:
        return "''"
    # safe chars don't need quoting
    safe = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_./=:,@")
    if all(c in safe for c in arg):
        return arg
    return "'" + arg.replace("'", "'\"'\"'") + "'"


def _is_storage_opt_unsupported(exc: Exception) -> bool:
    """Detect docker daemon errors caused by --storage-opt not being supported.

    Some storage drivers (overlay2 over ext4, common on CI runners) reject
    ``--storage-opt size=`` with a 500 ("supported only for overlay over xfs
    with 'pquota' mount option"). Used to trigger a storage-opt-free retry.
    """
    msg = str(exc).lower()
    return "storage-opt" in msg or "storage_opt" in msg or "pquota" in msg


class DockerProvisioner:
    """Real container provisioner with resource limits + bind mount + destroy."""

    name = "docker"

    def __init__(self, base_image: str = "python:3.11-slim") -> None:
        self._image = base_image

    async def provision(self, run_sandbox: RunSandbox) -> ProvisionedSandbox:
        if run_sandbox.mode != SandboxMode.DOCKER:
            raise ValueError(
                f"DockerProvisioner requires SandboxMode.DOCKER, got {run_sandbox.mode!r}"
            )

        Docker, DockerError = _import_aiodocker()
        client = Docker()
        config = self._build_config(run_sandbox)
        try:
            try:
                container = await client.containers.create_or_replace(
                    name=f"hanflow-run-{run_sandbox.run_id}",
                    config=config,
                )
                await container.start()
                cid = container.id
            except DockerError as exc:
                # Graceful degradation: some docker daemons (e.g. GitHub Actions
                # runners: overlay2 over ext4) reject --storage-opt with a 500
                # ("supported only for overlay over xfs with 'pquota'"). The disk
                # quota is a best-effort limit; drop it and retry once so sandbox
                # provisioning still succeeds without the per-container size cap.
                has_storage_opt = bool(config.get("HostConfig", {}).get("StorageOpt"))
                if has_storage_opt and _is_storage_opt_unsupported(exc):
                    config["HostConfig"]["StorageOpt"] = None
                    container = await client.containers.create_or_replace(
                        name=f"hanflow-run-{run_sandbox.run_id}",
                        config=config,
                    )
                    await container.start()
                    cid = container.id
                else:
                    raise
        except DockerError as exc:
            raise SandboxProvisionFailedError(
                f"docker provision failed: {exc}",
                run_id=run_sandbox.run_id,
                details={"image": self._image, "docker_error": str(exc)},
            ) from exc
        finally:
            await client.close()

        return ProvisionedSandbox(
            run_id=run_sandbox.run_id,
            mode=SandboxMode.DOCKER,
            container_id=cid,
            exec_interface=_DockerExec(cid, "/workspace", run_sandbox.run_id),
            workspace_root=Path("/workspace"),  # in-container view
        )

    def _build_config(self, sb: RunSandbox) -> dict[str, Any]:
        """Map SandboxResources → Docker container create config.

        Unit-tested independently of any daemon (see test_docker_provisioner.py).
        """
        r: SandboxResources = sb.resources
        net = "none" if r.network_egress is None else "host"
        cpu_quota = int(float(r.cpu_limit) * 100000)
        memory_bytes = r.memory_limit_mb * 1024 * 1024
        storage_opt = {"size": f"{r.disk_limit_mb}m"} if r.disk_limit_mb else None

        # Bind mount: host workspace → /workspace (POSIX container path).
        # On Windows host, resolve() gives a Windows path (C:\...); Docker
        # Desktop auto-translates. We bind as :rw so code_exec can write outputs.
        host_path = str(sb.workspace_root.resolve()).replace("\\", "/")
        # Windows drive letter (C:/...) needs to stay — Docker Desktop handles it.

        return {
            "Image": self._image,
            "Cmd": ["sleep", str(r.timeout_seconds)],  # container liveness cap
            "WorkingDir": "/workspace",
            "HostConfig": {
                "CpuQuota": cpu_quota,
                "Memory": memory_bytes,
                "NetworkMode": net,
                "Binds": [f"{host_path}:/workspace:rw"],
                "StorageOpt": storage_opt,
            },
        }

    async def destroy(self, provisioned: ProvisionedSandbox) -> None:
        if provisioned.container_id is None:
            return
        Docker, DockerError = _import_aiodocker()
        client = Docker()
        try:
            container = await client.containers.get(provisioned.container_id)
            # already-stopped is fine: use contextlib.suppress (ruff SIM105)
            with contextlib.suppress(DockerError):
                await container.kill()
            await container.delete()
        except DockerError as exc:
            raise SandboxDestroyFailedError(
                f"docker destroy failed: {exc}",
                run_id=provisioned.run_id,
                details={"container_id": provisioned.container_id},
            ) from exc
        finally:
            await client.close()
