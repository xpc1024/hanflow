"""Hanflow — top-level SDK API (§10.1, §10.2).

Aggregates every L4/L5/L6 component (lazy-init from config), compiles DSL to a
LangGraph graph, runs it, and returns a RunHandle. Three convenience builders
(``static``/``dynamic``/``hybrid``) are UX sugar — they all compile to the same
WorkflowDSL. ``RunMode='auto'`` picks the mode from DSL contents.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel

from hanflow.config import HanflowConfig
from hanflow.core.dsl import NodeConfig, WorkflowDSL, WorkflowNode
from hanflow.core.result import Artifact, Source

RunMode = Literal["auto", "static", "dynamic", "hybrid"]


class AggregatedUsage(BaseModel):
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    duration_seconds: float = 0.0


class RunResult(BaseModel):
    run_id: str
    status: str
    outputs: dict[str, Any] = {}
    artifacts: list[Artifact] = []
    sources: list[Source] = []
    usage: AggregatedUsage = AggregatedUsage()
    trace_id: str | None = None
    error: Any | None = None


class RunEvent(BaseModel):
    kind: Literal[
        "node_start",
        "node_end",
        "llm_token",
        "tool_call",
        "hitl_paused",
        "hitl_resumed",
        "artifact_created",
        "error",
    ]
    node_id: str | None = None
    data: dict[str, Any] = {}


class RunHandle:
    def __init__(self, run_id: str, status: str = "pending") -> None:
        self.run_id = run_id
        self.status = status
        self._result: RunResult | None = None
        self._queue: asyncio.Queue[RunEvent | None] = asyncio.Queue()
        # Resume hook (set by Hanflow.run): resume(Command) drives HITL recovery.
        self._resume: Any = None
        self._pending_payload: Any = None

    async def stream(self) -> AsyncIterator[RunEvent]:
        """Yield RunEvents in real time as the graph runs; ends when None sentinel."""
        while True:
            ev = await self._queue.get()
            if ev is None:
                break
            yield ev

    async def wait(self, timeout: float | None = None) -> RunResult:
        # Drain any remaining events if the result isn't ready yet.
        if self._result is None:
            async for _ in self.stream():
                pass
        assert self._result is not None
        return self._result

    @property
    def is_paused(self) -> bool:
        return self.status == "paused"


class Hanflow:
    def __init__(self, config: HanflowConfig | None = None) -> None:
        self.config = config or HanflowConfig()
        self._router: Any = None
        self._bus: Any = None
        self._memory: Any = None
        self._retrieval: dict[str, Any] = {}
        self._trace: Any = None
        self._stores: dict[str, Any] = {}
        self._workspace_mgr: Any = None
        self._sandbox: Any = None

    @classmethod
    def configure(cls, **overrides: Any) -> Hanflow:
        from hanflow.config import load_config

        return cls(load_config(overrides))

    # --- run --------------------------------------------------------------- #
    async def run(
        self,
        workflow: WorkflowDSL | str,
        inputs: dict[str, Any] | None = None,
        *,
        mode: RunMode = "auto",
        stream: bool = False,
        session_id: str | None = None,
    ) -> RunHandle:
        dsl = workflow if isinstance(workflow, WorkflowDSL) else WorkflowDSL.from_yaml(workflow)
        resolved_mode = mode if mode != "auto" else self._auto_mode(dsl)
        run_id = str(uuid.uuid4())
        handle = RunHandle(run_id=run_id, status="running")

        await self._ensure_components()
        from hanflow.core.state import NexusState, RunMeta
        from hanflow.isolation.sandbox import RunSandbox, SandboxMode
        from hanflow.orchestration.compiler import Compiler
        from hanflow.orchestration.context_impl import RuntimeContextImpl
        from hanflow.orchestration.registry import NodeExecutorRegistry

        named_models = self._build_named_models()
        sandbox = RunSandbox.create(
            run_id=run_id,
            mode=SandboxMode.LOCAL,
            workspace_mgr=self._workspace_mgr,
        )
        state = NexusState(
            meta=RunMeta(
                run_id=run_id,
                workflow_name=dsl.name,
                workflow_version=dsl.version,
                started_at=datetime.now(UTC),
                mode=resolved_mode,  # type: ignore[arg-type]
                trigger="sdk",
            ),
            inputs=inputs or {},
            outputs={},
            node_states={},
            artifacts=[],
            memory_ops=[],
            variables={},
        )
        ctx = RuntimeContextImpl(
            state=state,
            router=self._router,
            bus=self._bus,
            memory=self._memory,
            skills=None,
            retrieval=self._retrieval,
            trace=self._trace,
            workspace_mgr=self._workspace_mgr,
            sandbox=sandbox,
            named_models=named_models,
            run_handle_queue=handle._queue,
        )
        try:
            compiled = Compiler(NodeExecutorRegistry.default()).compile(dsl, ctx=ctx)
            config: dict[str, Any] = {"configurable": {"thread_id": run_id}}

            # Wire a resume hook so HITL approve/edit/reject/reroute can drive
            # the graph forward via Command(resume=...).
            async def _resume(command: Any) -> Any:
                return await compiled.graph.ainvoke(command, config=config)

            handle._resume = _resume

            final_outputs: dict[str, Any] = {}
            final_artifacts: list[Any] = []
            seen_node_states: dict[str, Any] = {}
            paused = False
            async for chunk in compiled.graph.astream(state, config=config, stream_mode="updates"):
                if not isinstance(chunk, dict):
                    continue
                for node_id, update in chunk.items():
                    if node_id == "__interrupt__":
                        await handle._queue.put(
                            RunEvent(
                                kind="hitl_paused", data=update if isinstance(update, dict) else {}
                            )
                        )
                        paused = True
                        continue
                    update_dict = update if isinstance(update, dict) else {}
                    node_states = update_dict.get("node_states", {})
                    ns = node_states.get(node_id)
                    if ns is not None:
                        st = ns.status if hasattr(ns, "status") else ns.get("status")
                        # Phase 15: emit node_start on first appearance of this node
                        if node_id not in seen_node_states:
                            await handle._queue.put(
                                RunEvent(kind="node_start", node_id=node_id, data={})
                            )
                        seen_node_states[node_id] = ns
                        await handle._queue.put(
                            RunEvent(kind="node_end", node_id=node_id, data={"status": st})
                        )
                    final_outputs = update_dict.get("outputs", final_outputs)
                    final_artifacts = (
                        update_dict.get("artifacts", final_artifacts) or final_artifacts
                    )
            await handle._queue.put(None)  # sentinel

            if paused:
                handle.status = "paused"
                handle._result = RunResult(run_id=run_id, status="paused")
            else:
                failed = any(
                    (ns.status if hasattr(ns, "status") else ns.get("status")) == "failed"
                    for ns in seen_node_states.values()
                )
                handle.status = "failed" if failed else "succeeded"
                handle._result = RunResult(
                    run_id=run_id,
                    status=handle.status,
                    outputs=final_outputs,
                    artifacts=final_artifacts,
                )
        except Exception as exc:  # noqa: BLE001
            await handle._queue.put(RunEvent(kind="error", data={"message": str(exc)}))
            await handle._queue.put(None)
            handle.status = "failed"
            handle._result = RunResult(run_id=run_id, status="failed", error=str(exc))
        return handle

    def run_sync(self, *args: Any, **kwargs: Any) -> RunResult:
        handle = asyncio.run(self.run(*args, **kwargs))
        return asyncio.run(handle.wait())

    # --- introspection (CLI-friendly) ------------------------------------- #
    async def list_tools(self, server: str | None = None) -> list[dict[str, Any]]:
        """List available tools as plain dicts.

        Thin public accessor over :meth:`MCPBus.list_tools` so the CLI does not
        need to reach into private components. Returns ``model_dump()`` so the
        result is JSON-serialisable plain data.
        """
        await self._ensure_components()
        tools = await self._bus.list_tools(server)
        return [t.model_dump() for t in tools]

    # --- convenience builders (UX sugar) ----------------------------------- #
    def static(self, *, nodes: list[dict[str, Any]], name: str = "static") -> WorkflowDSL:
        return WorkflowDSL(name=name, nodes=[WorkflowNode(**n) for n in nodes])

    def dynamic(
        self, *, goal: str, agents: list[str], plan_hitl: bool = False, **opts: Any
    ) -> WorkflowDSL:
        node = WorkflowNode(
            id="coordinator",
            type="Coordinator",
            config=NodeConfig(
                **{
                    "sub_agents": agents,
                    "planning_model": opts.get("planning_model", "strong"),
                    "plan_hitl": plan_hitl,
                    "replan": opts.get("replan", True),
                    "max_iterations": opts.get("max_iterations", 5),
                    "success_criteria": opts.get("success_criteria", goal),
                }
            ),
        )
        return WorkflowDSL(name="dynamic", nodes=[node])

    def hybrid(
        self, *, template: WorkflowDSL, overrides: dict[str, Any] | None = None
    ) -> WorkflowDSL:
        data = template.model_dump()
        if overrides:
            data.update(overrides)
        return WorkflowDSL(**data)

    def _auto_mode(self, dsl: WorkflowDSL) -> RunMode:
        types = {n.type for n in dsl.nodes}
        if "Coordinator" in types:
            return "dynamic" if len(types) == 1 else "hybrid"
        return "static"

    def _build_named_models(self) -> dict[str, tuple[str, str]]:
        return {name: (ref.provider, ref.model) for name, ref in self.config.models.items()}

    # --- component init ---------------------------------------------------- #
    async def _ensure_components(self) -> None:
        from hanflow.memory.backends.local_fs import LocalFsMemoryBackend
        from hanflow.memory.filesystem import FilesystemMemory
        from hanflow.models.governance import GovernanceConfig, GovernanceLayer
        from hanflow.models.providers.fake import FakeProvider
        from hanflow.models.router import ModelRouter
        from hanflow.observability.trace import NullTraceExporter
        from hanflow.persistence.backends.sqlite import SqliteKVBackend
        from hanflow.persistence.session import SessionStore
        from hanflow.tools.bus import MCPBus

        if self._trace is None:
            self._trace = NullTraceExporter()
        if self._router is None:
            # Default to a FakeProvider when no models configured (dev/tests).
            if self.config.models:
                providers = {
                    name: FakeProvider(name, models=[ref.model])
                    for name, ref in self.config.models.items()
                }
                default = next(iter(self.config.models.items()))
                default_model = (default[0], default[1].model)
            else:
                providers = {"cloud": FakeProvider("cloud", models=["strong"])}
                default_model = ("cloud", "strong")
            self._router = ModelRouter(
                providers=providers,
                strategies=[],
                governance=GovernanceLayer(GovernanceConfig()),
                trace=self._trace,
                default_model=default_model,
            )
        if self._bus is None:
            self._bus = MCPBus(servers={}, trace=self._trace)
            # Register a default in-process echo tool so Tool nodes work out of
            # the box in dev/tests. Production wires real MCP servers via config.
            from hanflow.tools.builtin.base import BuiltinMCPServer, ToolDescriptor

            class _EchoTool(BuiltinMCPServer):
                name = "echo"

                def tools(self) -> list[Any]:
                    return [
                        ToolDescriptor(
                            name="say",
                            server="echo",
                            description="echo",
                            input_schema={"type": "object"},
                            annotations={},
                        )
                    ]

                async def call(self, tool: str, args: dict[str, Any]) -> Any:
                    return args

            self._bus.register_builtin("echo", _EchoTool())
            await self._bus.start()
        if self._workspace_mgr is None:
            from pathlib import Path

            from hanflow.persistence.artifact import ArtifactStore
            from hanflow.persistence.backends.local_fs import LocalFsArtifactBackend
            from hanflow.persistence.workspace import WorkspaceManager

            ws_root = Path(self.config.workspace_root)
            ws_root.mkdir(parents=True, exist_ok=True)
            kv = SqliteKVBackend(path=str(ws_root / "session.db"))
            await kv.setup()
            self._workspace_mgr = WorkspaceManager(
                scratch_root=ws_root,
                artifact_store=ArtifactStore(LocalFsArtifactBackend(root=ws_root / "artifacts")),
                session_kv=kv,
            )
            self._memory = FilesystemMemory(
                workspace_root=ws_root,
                session_store=SessionStore(kv),
                backends={
                    "scratch": LocalFsMemoryBackend(root=ws_root / "scratch"),
                    "session": LocalFsMemoryBackend(root=ws_root / "session"),
                    "long_term": None,
                },
            )
