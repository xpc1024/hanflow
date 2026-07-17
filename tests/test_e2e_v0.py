"""v0 acceptance: public API importable + three modes build + static e2e."""

from __future__ import annotations

from pathlib import Path

import pytest

import hanflow
from hanflow import Hanflow, HanflowConfig, WorkflowDSL


def test_v0_all_subsystems_importable():
    """Smoke: every v0 subsystem can be imported."""
    import hanflow.api  # noqa: F401
    import hanflow.atoms  # noqa: F401
    import hanflow.cli.main  # noqa: F401
    import hanflow.config  # noqa: F401
    import hanflow.core  # noqa: F401
    import hanflow.isolation  # noqa: F401
    import hanflow.memory  # noqa: F401
    import hanflow.models  # noqa: F401
    import hanflow.observability  # noqa: F401
    import hanflow.orchestration  # noqa: F401
    import hanflow.persistence  # noqa: F401
    import hanflow.retrieval  # noqa: F401
    import hanflow.sdk  # noqa: F401
    import hanflow.tools  # noqa: F401
    import hanflow.workflows  # noqa: F401

    # Version is non-empty; not pinned to a literal so this test doesn't rot
    # on every release.
    assert hanflow.__version__


def test_top_level_api_exports():
    for name in ["Hanflow", "HanflowConfig", "WorkflowDSL", "RunHandle", "RunResult"]:
        assert hasattr(hanflow, name)


@pytest.fixture
def hf(tmp_path: Path) -> Hanflow:
    return Hanflow(HanflowConfig(workspace_root=str(tmp_path / "ws")))


@pytest.mark.asyncio
async def test_static_mode_runs(hf):
    dsl = hf.static(nodes=[{"id": "a", "type": "LLM", "config": {"template": "hi"}}])
    handle = await hf.run(dsl, mode="static")
    result = await handle.wait()
    assert result.status == "succeeded"


@pytest.mark.asyncio
async def test_dynamic_mode_runs(hf):
    dsl = hf.dynamic(goal="research X", agents=["researcher"], plan_hitl=False)
    handle = await hf.run(dsl, mode="dynamic")
    result = await handle.wait()
    assert result.run_id


@pytest.mark.asyncio
async def test_hybrid_mode_runs(hf):
    base = hf.static(nodes=[{"id": "intake", "type": "LLM", "config": {"template": "parse"}}])
    dsl = hf.hybrid(template=base)
    handle = await hf.run(dsl, mode="hybrid")
    result = await handle.wait()
    assert result.run_id


def test_examples_validate(tmp_path: Path):
    """All three appendix-B example workflows are valid DSL."""

    repo_root = Path(__file__).resolve().parent.parent
    for name in ("static.yaml", "dynamic.yaml", "hybrid.yaml"):
        p = repo_root / "examples" / name
        assert p.exists(), f"missing example {name}"
        dsl = WorkflowDSL.from_yaml(p.read_text(encoding="utf-8"))
        assert dsl.nodes
