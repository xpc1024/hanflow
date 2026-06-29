"""Shared pytest fixtures for Hanflow tests.

The ``ctx`` fixture assembles a real RuntimeContext with in-memory/fake L4
components (no network) — shared by orchestration and atoms tests.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from hanflow.core.state import NexusState, RunMeta
from hanflow.isolation.sandbox import RunSandbox, SandboxMode
from hanflow.memory.backends.local_fs import LocalFsMemoryBackend
from hanflow.memory.filesystem import FilesystemMemory
from hanflow.models.governance import GovernanceConfig, GovernanceLayer
from hanflow.models.providers.fake import FakeProvider
from hanflow.models.router import ModelRouter
from hanflow.observability.trace import NullTraceExporter
from hanflow.orchestration.context_impl import RuntimeContextImpl
from hanflow.persistence.artifact import ArtifactStore
from hanflow.persistence.backends.local_fs import LocalFsArtifactBackend
from hanflow.persistence.backends.sqlite import SqliteKVBackend
from hanflow.persistence.session import SessionStore
from hanflow.persistence.workspace import WorkspaceManager
from hanflow.retrieval.embedding import FakeEmbedding
from hanflow.retrieval.fulltext.memory_fts import InMemoryFullTextProvider
from hanflow.retrieval.provider import HybridSearchProvider
from hanflow.retrieval.vector.memory import InMemoryVectorProvider
from hanflow.tools.builtin.base import BuiltinMCPServer, ToolDescriptor
from hanflow.tools.bus import MCPBus


class _EchoTool(BuiltinMCPServer):
    name = "echo"

    def tools(self):
        return [
            ToolDescriptor(
                name="say",
                server="echo",
                description="d",
                input_schema={"type": "object"},
                annotations={},
            )
        ]

    async def call(self, tool, args):
        return args


def make_state(run_id: str = "r1", mode: str = "static") -> NexusState:
    return NexusState(
        meta=RunMeta(
            run_id=run_id,
            workflow_name="w",
            workflow_version="0.1.0",
            started_at=datetime.now(UTC),
            mode=mode,  # type: ignore[arg-type]
            trigger="api",
        ),
        inputs={},
        outputs={},
        node_states={},
        artifacts=[],
        memory_ops=[],
        variables={},
    )


@pytest.fixture
async def ctx(tmp_path: Path):
    trace = NullTraceExporter()
    router = ModelRouter(
        providers={"cloud": FakeProvider("cloud", models=["strong", "fast"])},
        strategies=[],
        governance=GovernanceLayer(GovernanceConfig()),
        trace=trace,
        default_model=("cloud", "strong"),
    )
    bus = MCPBus(servers={}, trace=trace)
    bus.register_builtin("echo", _EchoTool())
    await bus.start()
    kv = SqliteKVBackend(path=str(tmp_path / "sess.db"))
    await kv.setup()
    session_store = SessionStore(kv)
    workspace_mgr = WorkspaceManager(
        scratch_root=tmp_path / "ws",
        artifact_store=ArtifactStore(LocalFsArtifactBackend(root=tmp_path / "art")),
        session_kv=kv,
    )
    memory = FilesystemMemory(
        workspace_root=tmp_path / "ws",
        session_store=session_store,
        backends={
            "scratch": LocalFsMemoryBackend(root=tmp_path / "ws" / "scratch"),
            "session": LocalFsMemoryBackend(root=tmp_path / "ws" / "session"),
            "long_term": None,
        },
    )
    embed = FakeEmbedding(dim=8)
    vec = InMemoryVectorProvider(dim=embed.dim)
    await vec.create_collection("docs", dim=embed.dim)
    ft = InMemoryFullTextProvider()
    await ft.create_index("docs")
    retrieval = {"docs": HybridSearchProvider(vector=vec, fulltext=ft, embedding=embed)}
    sandbox = RunSandbox.create(run_id="r1", mode=SandboxMode.LOCAL, workspace_mgr=workspace_mgr)

    ctx_obj = RuntimeContextImpl(
        state=make_state(),
        router=router,
        bus=bus,
        memory=memory,
        skills=None,
        retrieval=retrieval,
        trace=trace,
        workspace_mgr=workspace_mgr,
        sandbox=sandbox,
        named_models={"strong": ("cloud", "strong"), "fast": ("cloud", "fast")},
    )
    yield ctx_obj
    await bus.stop()
