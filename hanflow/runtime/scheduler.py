"""RunAffinityScheduler — route the same run to the same worker (§12.10).

Single-machine mode (``enabled=False``): passthrough, inline worker handles
dispatch. K8s multi-replica mode (``enabled=True``): ``hash(run_id) %
node_count`` pins a run to a worker so its scratch FS is local; a dead worker's
runs are reclaimed to another node, which triggers a scratch restore from the
last snapshot.
"""

from __future__ import annotations

import hashlib
from typing import Any


class RunAffinityScheduler:
    def __init__(
        self, enabled: bool = False, node_count: int = 1, self_node_id: str = "inline"
    ) -> None:
        self.enabled = enabled
        self.node_count = max(1, node_count)
        self.self_node_id = self_node_id

    def pick_node(self, run_id: str) -> int | None:
        if not self.enabled:
            return None
        h = int(hashlib.sha1(run_id.encode()).hexdigest(), 16)
        return h % self.node_count

    async def enqueue(self, run_id: str, task: Any) -> None:
        """Submit a run task. With affinity off, dispatch is the caller's job."""
        # Placeholder: real queue wiring lands in Phase 10 (SDK/worker loop).
        return None

    async def reclaim(self, failed_node_id: str) -> list[Any]:
        """Reclaim tasks owned by a dead node. Returns [] until Phase 10."""
        return []
