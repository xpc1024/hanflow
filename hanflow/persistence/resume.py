"""ResumeManager — pause/cancel/time-travel command surface (§9.5).

Three resume semantics:
- HITL approve/edit/reject/reroute → inject HITLRecord, resume graph
- crash_recover → continue from most recent checkpoint
- time_travel → re-run from a specific step

The graph-driving resume (injecting HITLRecord and re-invoking the compiled
graph) is wired in Phase 8 (orchestration), once the compiler exists. This
module owns the *command contract* + paused-gate bookkeeping now.
"""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel

from hanflow.core.result import HITLPayload
from hanflow.persistence.backends.sqlite import SqliteKVBackend

ResumeKind = Literal[
    "hitl_approve",
    "hitl_edit",
    "hitl_reject",
    "hitl_reroute",
    "crash_recover",
    "time_travel",
]

_PAUSED_SCOPE = "paused_hitl"


class ResumeCommand(BaseModel):
    kind: ResumeKind
    payload: dict[str, Any] = {}


class ResumeManager:
    def __init__(self, kv: SqliteKVBackend) -> None:
        self.kv = kv

    async def record_paused(
        self, run_id: str, payload: HITLPayload, user_id: str | None = None
    ) -> None:
        await self.kv.setup()
        await self.kv.put(
            _PAUSED_SCOPE,
            run_id,
            json.dumps({"payload": payload.model_dump(mode="json"), "user_id": user_id}),
        )

    async def list_paused(
        self, *, user_id: str | None = None, older_than: str | None = None
    ) -> list[HITLPayload]:
        await self.kv.setup()
        rows = await self.kv.list(_PAUSED_SCOPE)
        out: list[HITLPayload] = []
        for _, raw in rows:
            rec = json.loads(raw)
            if user_id is not None and rec.get("user_id") != user_id:
                continue
            out.append(HITLPayload.model_validate(rec["payload"]))
        return out

    async def get_paused(self, run_id: str) -> HITLPayload | None:
        await self.kv.setup()
        raw = await self.kv.get(_PAUSED_SCOPE, run_id)
        if raw is None:
            return None
        return HITLPayload.model_validate(json.loads(raw)["payload"])

    async def clear_paused(self, run_id: str) -> bool:
        await self.kv.setup()
        return await self.kv.delete(_PAUSED_SCOPE, run_id)

    async def cancel(self, run_id: str, reason: str = "") -> None:
        await self.clear_paused(run_id)

    async def resume(self, run_id: str, command: ResumeCommand) -> Any:
        """Drive graph-level resume.

        Implemented in Phase 8 (orchestration). Raises NotImplementedError
        until the compiler integration lands.
        """
        raise NotImplementedError(
            "graph resume is wired in Phase 8 (orchestration); use it from the SDK then."
        )
