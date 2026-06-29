"""LangSmith TraceExporter — the default observability backend.

Wraps the ``langsmith`` SDK ``Client``. Each closed span becomes a LangSmith
run: created on span open (so streaming UIs see it live) and updated with
end_time/error on close. Parent links are wired from the contextvar stack.

The ``client`` may be injected (tests) or lazily built from config/env via
``from_config``. ``create_run`` accepts ``run_id`` / ``parent_run_id`` via the
SDK's ``**kwargs`` (LangSmith honours them); ``update_run`` takes ``error``.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from hanflow.observability.trace import Span, _BufferedTraceExporter

_RUN_TYPE = {
    "workflow": "chain",
    "node": "chain",
    "atom": "chain",
    "llm": "llm",
    "tool": "tool",
    "retrieval": "retriever",
    "memory": "tool",
    "hitl": "chain",
}


def _to_uuid(short_id: str) -> uuid.UUID:
    """Pad a short id to a valid 32-hex UUID (LangSmith run_id compatibility)."""
    pad = (short_id + "0" * 32)[:32]
    return uuid.UUID(int=int(pad, 16))


class LangSmithTraceExporter(_BufferedTraceExporter):
    """Exports spans to LangSmith as runs."""

    def __init__(self, client: Any, project: str) -> None:
        super().__init__()
        self.client = client
        self.project = project

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> LangSmithTraceExporter:
        from langsmith import Client

        api_key = config.get("api_key")
        project = config.get("project", "hanflow")
        client = Client(api_key=api_key) if api_key else Client()
        return cls(client=client, project=project)

    async def _export(self, spans: list[Span]) -> None:
        for sp in spans:
            run_type = _RUN_TYPE.get(sp.kind, "chain")
            self.client.create_run(
                name=sp.name,
                inputs=sp.attributes,
                run_type=run_type,
                project_name=self.project,
                run_id=_to_uuid(sp.span_id),
                parent_run_id=_to_uuid(sp.parent_span_id) if sp.parent_span_id else None,
                start_time=sp.start_time,
            )
            self.client.update_run(
                _to_uuid(sp.span_id),
                end_time=sp.end_time or datetime.now(UTC),
                outputs={"events": [e.model_dump(mode="json") for e in sp.events]},
                error=(
                    f"{sp.attributes.get('error.type')}: {sp.attributes.get('error.message')}"
                    if sp.status == "error"
                    else None
                ),
            )
