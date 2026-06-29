"""WorkspaceManager — layered storage for run workspaces (§12.10).

Layers:
- scratch/state  → local FS (latency-sensitive; per-run dir)
- snapshots      → Postgres/SessionStore (crash recovery for multi-replica)
- artifacts      → ArtifactStore (S3 in prod)

Single-machine default: scratch on local FS, snapshots optional (no affinity).
K8s multi-replica (Phase 10/17): run-affinity scheduling + snapshot on interval.
"""

from __future__ import annotations

import zipfile
from io import BytesIO
from pathlib import Path

from hanflow.core.result import Artifact
from hanflow.persistence.artifact import ArtifactStore
from hanflow.persistence.backends.sqlite import SqliteKVBackend

_SNAPSHOT_SCOPE = "workspace_snapshots"


class WorkspaceManager:
    def __init__(
        self,
        scratch_root: Path,
        artifact_store: ArtifactStore,
        session_kv: SqliteKVBackend | None,
        snapshot_interval_steps: int = 5,
    ) -> None:
        self.scratch_root = Path(scratch_root)
        self.artifact_store = artifact_store
        self.session_kv = session_kv
        self.snapshot_interval_steps = snapshot_interval_steps

    # ---- per-run workspace layout ---------------------------------------- #
    def run_root(self, run_id: str) -> Path:
        return self.scratch_root / run_id

    def workspace_for(self, run_id: str) -> Path:
        root = self.run_root(run_id)
        (root / "uploads").mkdir(parents=True, exist_ok=True)
        ws = root / "workspace"
        ws.mkdir(parents=True, exist_ok=True)
        (root / "outputs").mkdir(parents=True, exist_ok=True)
        return ws

    def sandbox_dir(self, run_id: str, sandbox_id: str) -> Path:
        d = self.workspace_for(run_id) / sandbox_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    # ---- snapshot / restore ---------------------------------------------- #
    async def snapshot_scratch(self, run_id: str, step: int) -> bool:
        """Snapshot the run workspace to SessionStore if step hits interval.

        Returns False if snapshot is disabled or step is off-interval.
        """
        if self.session_kv is None:
            return False
        if self.snapshot_interval_steps <= 0 or step % self.snapshot_interval_steps != 0:
            return False
        ws = self.workspace_for(run_id)
        buf = BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for p in ws.rglob("*"):
                if p.is_file():
                    zf.write(p, arcname=str(p.relative_to(ws)))
        await self.session_kv.put(_SNAPSHOT_SCOPE, run_id, buf.getvalue().hex())
        return True

    async def restore_scratch(self, run_id: str, to_node: str | None = None) -> bool:
        if self.session_kv is None:
            return False
        hex_blob = await self.session_kv.get(_SNAPSHOT_SCOPE, run_id)
        if hex_blob is None:
            return False
        ws = self.workspace_for(run_id)
        buf = BytesIO(bytes.fromhex(hex_blob))
        with zipfile.ZipFile(buf) as zf:
            zf.extractall(ws)
        return True

    # ---- artifact promotion ---------------------------------------------- #
    async def promote_artifact(self, run_id: str, artifact: Artifact) -> str:
        return await self.artifact_store.put(run_id, artifact)

    async def health(self) -> bool:
        try:
            self.scratch_root.mkdir(parents=True, exist_ok=True)
            return await self.artifact_store.health()
        except Exception:
            return False
