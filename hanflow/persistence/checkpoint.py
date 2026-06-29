"""CheckpointStore — adapts a backend to LangGraph's BaseCheckpointSaver.

We do NOT reimplement checkpointing; we delegate to LangGraph's official savers
(sqlite/postgres) so behaviour stays in lock-step with the runtime. The
``CheckpointBackend`` Protocol below is the seam for swapping storage.

namespace = ``run:{run_id}``; per-thread (LangGraph thread_id == run_id mapping
handled by the engine in Phase 8).
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from typing import Any, Protocol, cast

from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    ChannelVersions,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
)
from langgraph.types import RunnableConfig  # type: ignore[attr-defined]


class CheckpointBackend(Protocol):
    """Seam for swapping checkpoint storage (sqlite/postgres/redis)."""

    def saver(self) -> Any: ...  # async cm yielding a BaseCheckpointSaver
    async def health(self) -> bool: ...


class CheckpointStore(BaseCheckpointSaver[Any]):
    """LangGraph-compatible checkpointer delegating to a backend."""

    def __init__(self, backend: CheckpointBackend) -> None:
        self.backend = backend

    # ---- async API (used by Hanflow runtime) ----------------------------- #
    async def aput(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        async with self.backend.saver() as saver:
            return cast(
                RunnableConfig, await saver.aput(config, checkpoint, metadata, new_versions)
            )

    async def aget_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        async with self.backend.saver() as saver:
            return cast(CheckpointTuple | None, await saver.aget_tuple(config))

    async def alist(
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ) -> AsyncIterator[CheckpointTuple]:
        async with self.backend.saver() as saver:
            async for tup in saver.alist(config, filter=filter, before=before, limit=limit):
                yield tup

    async def aput_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        async with self.backend.saver() as saver:
            await saver.aput_writes(config, writes, task_id, task_path)

    async def health(self) -> bool:
        return await self.backend.health()

    # ---- sync API fallback (not used by Hanflow async runtime) ----------- #
    def put(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("Hanflow uses async checkpoint API only")

    def get_tuple(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("Hanflow uses async checkpoint API only")

    def list(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("Hanflow uses async checkpoint API only")
