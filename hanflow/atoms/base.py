"""Atom Protocol — the L3 capability layer (§8.1).

Atoms hold complex business logic (research, execution) and only touch L4 via
``ctx``. NodeExecutors (L2) instantiate the matching atom and call ``run()``.
The two layers evolve and test independently.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel

from hanflow.core.result import AtomResult


class AtomOptions(BaseModel):
    timeout_seconds: int | None = None
    max_retries: int = 0
    trace_name: str | None = None


@runtime_checkable
class Atom(Protocol):
    name: str

    async def run(self, ctx: Any, inputs: dict[str, Any], options: AtomOptions) -> AtomResult: ...
