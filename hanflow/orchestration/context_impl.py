"""RuntimeContextImpl — the production RuntimeContext (§2.5).

Wires together every L4 capability (router/bus/memory/skills/retrieval) plus
the L6 TraceExporter and the spawn_agent isolation contract. This is the
convergence point of Phases 1-7. ``emit_hitl`` stages the payload on state;
the HITL node wrapper (Phase 8 control executors) raises LangGraph's interrupt.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from hanflow.core.result import Chunk, HITLPayload, MemoryOp, SensitivityLevel
from hanflow.core.state import NexusState
from hanflow.isolation.sandbox import AgentSpec, RunSandbox, enforce_tool_whitelist
from hanflow.models.providers.base import StreamChunk
from hanflow.observability.trace import TraceExporter

if TYPE_CHECKING:
    from hanflow.sdk import RunEvent


class RuntimeContextImpl:
    """Concrete RuntimeContext — owns all L4 components for one run."""

    def __init__(
        self,
        state: NexusState,
        router: Any,
        bus: Any,
        memory: Any,
        skills: Any | None,
        retrieval: dict[str, Any],
        trace: TraceExporter,
        workspace_mgr: Any,
        sandbox: RunSandbox,
        provisioned: Any | None = None,
        named_models: dict[str, tuple[str, str]] | None = None,
        run_handle_queue: asyncio.Queue[RunEvent | None] | None = None,
    ) -> None:
        self.state = state
        self._router = router
        self._bus = bus
        self._memory = memory
        self._skills = skills
        self._retrieval = retrieval
        self.trace = trace
        self._workspace_mgr = workspace_mgr
        self._sandbox = sandbox
        # cycle 2026-W30-1.1.1: provisioned sandbox handle (container/subprocess
        # + ExecInterface). Optional for backward compat; DOCKER mode requires it.
        # Typed Any because ProvisionedSandbox lives in core.sandbox_contract
        # but we already import RunSandbox transitively; avoid extra import here.
        self._provisioned = provisioned
        self._tool_whitelist: list[str] | None = None
        # named_models: {"strong": ("openai","gpt-4o"), ...} from config (§4.7).
        # Used to resolve PUBLIC prefer="strong" → ("openai","gpt-4o") tuple.
        self._named_models = named_models or {}
        # Optional RunHandle event queue (§5a). When attached, emit_run_event
        # pushes RunEvents (llm_token / node_*) so the host can stream them to
        # the SDK caller. None for sub-agents / isolated tests → silent drop.
        self._run_handle_queue = run_handle_queue

    def provisioned(self) -> Any | None:
        """Access the provisioned sandbox handle (container + exec interface).

        Used by builtin tools (code_exec / shell) to reach the ExecInterface.
        Returns None when no provisioner was wired (e.g. legacy test contexts).
        """
        return self._provisioned

    # --- GraphRuntime ------------------------------------------------------
    def emit_hitl(self, payload: HITLPayload) -> None:
        self.state.pending_hitl = payload

    # --- ModelRouter -------------------------------------------------------
    async def complete(
        self,
        messages: list[Any],
        *,
        role: str | None = None,
        task_type: str | None = None,
        sensitivity: SensitivityLevel = "public",
        prefer: str | None = None,
        **kwargs: Any,
    ) -> Any:
        # PUBLIC API takes a named-model string (§2.5, §4.7) e.g. prefer="strong".
        # Resolve it to the (provider, model) tuple the internal ModelRouter
        # expects, via the loaded models config. None → router default.
        resolved = self._resolve_named_model(prefer) if prefer else None
        return await self._router.complete(
            messages,
            role=role,
            task_type=task_type,
            sensitivity=sensitivity,
            prefer=resolved,
            **kwargs,
        )

    async def stream(
        self,
        messages: list[Any],
        *,
        role: str | None = None,
        task_type: str | None = None,
        sensitivity: SensitivityLevel = "public",
        prefer: str | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[StreamChunk]:
        """Streaming variant of :meth:`complete` (§design §4/§5a).

        Resolves the named-model ``prefer`` string to a (provider, model) tuple
        exactly like ``complete`` does, then yields ``StreamChunk``s from
        ``ModelRouter.stream``. Callers (e.g. the LLM node executor) may forward
        each chunk to ``emit_run_event`` so the host ``RunHandle`` can stream
        ``llm_token`` events to the SDK caller in real time.
        """
        resolved = self._resolve_named_model(prefer) if prefer else None
        async for chunk in self._router.stream(
            messages,
            role=role,
            task_type=task_type,
            sensitivity=sensitivity,
            prefer=resolved,
            **kwargs,
        ):
            yield chunk

    def _resolve_named_model(self, name: str) -> tuple[str, str] | None:
        """Map a config named model ('strong'/'fast'/...) → (provider, model).

        Populated at construction from the ``models:`` config block. If the
        name is unknown, return None (router falls back to default_model).
        """
        return self._named_models.get(name)

    # --- MCPBus ------------------------------------------------------------
    async def tool_call(self, name: str, args: dict[str, Any], *, timeout_seconds: int = 60) -> Any:
        enforce_tool_whitelist(name, self._tool_whitelist)
        result = await self._bus.tool_call(name, args, timeout_seconds=timeout_seconds)
        if not result.ok:
            from hanflow.core.errors import HanflowError

            raise HanflowError(result.error or "tool call failed", details={"tool": name})
        return result.output

    # --- FilesystemMemory --------------------------------------------------
    async def memory(self, op: MemoryOp) -> Any:
        if op.action == "read":
            entry = await self._memory.read(op.scope, op.key)
            return entry.value if entry else None
        if op.action in ("write", "update"):
            await self._memory.write(op.scope, op.key, op.value, op.ttl_seconds)
            return None
        if op.action == "delete":
            await self._memory.delete(op.scope, op.key)
            return None
        if op.action == "summarize":
            return await self._memory.summarize(op.scope, op.value or [])
        raise ValueError(f"unknown memory action: {op.action!r}")

    def workspace(self) -> Path:
        return self._sandbox.workspace_root

    # --- SkillsLoader ------------------------------------------------------
    async def load_skill(self, name: str) -> Any:
        if self._skills is None:
            raise RuntimeError("skills loader not configured")
        return await self._skills.load_skill(name)

    async def match_skills(self, task: str) -> list[Any]:
        if self._skills is None:
            return []
        return cast(list[Any], await self._skills.match_skills(task))

    # --- RetrievalProvider -------------------------------------------------
    async def retrieve(
        self,
        store: str,
        query: str,
        *,
        top_k: int = 5,
        rerank: str | None = None,
        filter: dict[str, Any] | None = None,
    ) -> list[Chunk]:
        provider = self._retrieval.get(store)
        if provider is None:
            raise KeyError(f"unknown retrieval store: {store!r}")
        return cast(list[Chunk], await provider.search(store, query, top_k=top_k, filter=filter))

    # --- TraceExporter -----------------------------------------------------
    @asynccontextmanager
    async def span(self, name: str, **attrs: Any) -> AsyncIterator[Any]:
        async with self.trace.span(name, **attrs) as sp:
            yield sp

    async def event(self, name: str, **attrs: Any) -> None:
        await self.trace.event(name, **attrs)

    # --- RunHandle event push (§5a) ---------------------------------------
    async def emit_run_event(self, event: Any) -> None:
        """Push a ``RunEvent`` (llm_token / node_* / ...) onto the host queue.

        When a ``RunHandle`` queue is attached (the top-level run), this is how
        streaming LLM tokens and node lifecycle events reach the SDK caller in
        real time. When no queue is attached (sub-agents spawned via
        ``spawn_agent`` / isolated unit tests) the event is silently dropped.
        """
        if self._run_handle_queue is not None:
            await self._run_handle_queue.put(event)

    # --- Sub-agent / sub-workflow ------------------------------------------
    async def compile_subgraph(self, dsl: Any) -> Any:
        from hanflow.orchestration.compiler import Compiler
        from hanflow.orchestration.registry import NodeExecutorRegistry

        compiler = Compiler(NodeExecutorRegistry.default())
        return compiler.compile(dsl)

    async def spawn_agent(self, spec: AgentSpec) -> RuntimeContextImpl:
        from hanflow.isolation.sandbox import spawn_agent

        child_fake = await spawn_agent(
            parent=self, spec=spec, run_sandbox=self._sandbox, trace=self.trace
        )
        # Promote to a real RuntimeContextImpl with isolated state, sharing L4.
        child = RuntimeContextImpl(
            state=child_fake.state,
            router=self._router,
            bus=self._bus,
            memory=self._memory,
            skills=self._skills,
            retrieval=self._retrieval,
            trace=self.trace,
            workspace_mgr=self._workspace_mgr,
            sandbox=self._sandbox,
            named_models=self._named_models,
        )
        child._tool_whitelist = spec.tools_whitelist
        return child
