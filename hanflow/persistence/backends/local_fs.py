"""Local filesystem backend for ArtifactStore.

LocalFsArtifactBackend stores one JSON manifest + one content blob per
artifact under ``<root>/<run_id>/<artifact_id>/``. Single-machine default.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from hanflow.core.result import Artifact


class LocalFsArtifactBackend:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def _dir(self, run_id: str, artifact_id: str) -> Path:
        d = self.root / run_id / artifact_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    async def put(self, run_id: str, artifact: Artifact) -> str:
        d = self._dir(run_id, artifact.id)
        content = artifact.content
        if isinstance(content, bytes):
            (d / "content.bin").write_bytes(content)
        else:
            (d / "content.txt").write_text(content, encoding="utf-8")
        manifest = artifact.model_dump(mode="json")
        (d / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        return f"local://{run_id}/{artifact.id}"

    async def get(self, run_id: str, artifact_id: str) -> Artifact | None:
        d = self.root / run_id / artifact_id
        if not d.exists():
            return None
        manifest = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
        content_file = d / "content.bin"
        if content_file.exists():
            manifest["content"] = content_file.read_bytes()
        else:
            manifest["content"] = (d / "content.txt").read_text(encoding="utf-8")
        return Artifact.model_validate(manifest)

    async def list(self, run_id: str, *, kind: str | None = None) -> list[Artifact]:
        run_dir = self.root / run_id
        if not run_dir.exists():
            return []
        out: list[Artifact] = []
        for sub in run_dir.iterdir():
            mf = sub / "manifest.json"
            if not mf.exists():
                continue
            a = Artifact.model_validate(json.loads(mf.read_text(encoding="utf-8")))
            if kind is None or a.kind == kind:
                out.append(a)
        return out

    async def delete(self, run_id: str, artifact_id: str) -> bool:
        d = self.root / run_id / artifact_id
        if d.exists():
            shutil.rmtree(d)
            return True
        return False

    async def signed_url(self, run_id: str, artifact_id: str, expires_seconds: int = 3600) -> str:
        d = self.root / run_id / artifact_id
        return (d / "manifest.json").as_uri()

    async def health(self) -> bool:
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            return self.root.is_dir()
        except Exception:
            return False
