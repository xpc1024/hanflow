"""ArtifactStore — persistent run products (cross-run queryable).

Boundary vs FilesystemMemory: FilesystemMemory is the ephemeral workspace
(scratch/session); ArtifactStore is the durable product store. Atoms write to
``workspace/outputs/``; the engine promotes them here at run end (Phase 8).

Backends: local_fs (default) / s3 (production). See §9.4.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from hanflow.core.result import Artifact


@runtime_checkable
class ArtifactBackend(Protocol):
    async def put(self, run_id: str, artifact: Artifact) -> str: ...
    async def get(self, run_id: str, artifact_id: str) -> Artifact | None: ...
    async def list(self, run_id: str, *, kind: str | None = None) -> list[Artifact]: ...
    async def delete(self, run_id: str, artifact_id: str) -> bool: ...
    async def signed_url(
        self, run_id: str, artifact_id: str, expires_seconds: int = 3600
    ) -> str: ...
    async def health(self) -> bool: ...


class ArtifactStore:
    def __init__(self, backend: ArtifactBackend) -> None:
        self.backend = backend

    async def put(self, run_id: str, artifact: Artifact) -> str:
        return await self.backend.put(run_id, artifact)

    async def get(self, run_id: str, artifact_id: str) -> Artifact | None:
        return await self.backend.get(run_id, artifact_id)

    async def list(self, run_id: str, *, kind: str | None = None) -> list[Artifact]:
        return await self.backend.list(run_id, kind=kind)

    async def delete(self, run_id: str, artifact_id: str) -> bool:
        return await self.backend.delete(run_id, artifact_id)

    async def signed_url(self, run_id: str, artifact_id: str, expires_seconds: int = 3600) -> str:
        return await self.backend.signed_url(run_id, artifact_id, expires_seconds)

    async def health(self) -> bool:
        return await self.backend.health()
