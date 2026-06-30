"""WorkflowStore — persist workflows as YAML files under root (§11.8).

v1 default backend: local filesystem. Web save = write file (+ optional git
commit, default off). Dynamic Coordinator plans stay in DB (run-scoped), not
here.
"""

from __future__ import annotations

from pathlib import Path


class WorkflowStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, workflow_id: str) -> Path:
        return self.root / f"{workflow_id}.yaml"

    def list(self) -> list[dict[str, str]]:
        out: list[dict[str, str]] = []
        for p in sorted(self.root.glob("*.yaml")):
            out.append({"id": p.stem, "yaml": p.read_text(encoding="utf-8")})
        return out

    def get(self, workflow_id: str) -> dict[str, str] | None:
        p = self._path(workflow_id)
        if not p.exists():
            return None
        return {"id": workflow_id, "yaml": p.read_text(encoding="utf-8")}

    def put(self, workflow_id: str, yaml_text: str) -> dict[str, str]:
        p = self._path(workflow_id)
        p.write_text(yaml_text, encoding="utf-8")
        return {"id": workflow_id, "yaml": yaml_text}

    def delete(self, workflow_id: str) -> bool:
        p = self._path(workflow_id)
        if p.exists():
            p.unlink()
            return True
        return False
