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
