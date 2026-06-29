import pytest

from hanflow.core.result import Artifact
from hanflow.persistence.artifact import ArtifactStore
from hanflow.persistence.backends.local_fs import LocalFsArtifactBackend
from hanflow.persistence.workspace import WorkspaceManager


@pytest.fixture
def mgr(tmp_workspace_root):
    art = ArtifactStore(LocalFsArtifactBackend(root=tmp_workspace_root / "artifacts"))
    return WorkspaceManager(
        scratch_root=tmp_workspace_root / "scratch",
        artifact_store=art,
        session_kv=None,  # snapshot disabled when session_kv=None
        snapshot_interval_steps=2,
    )


def test_workspace_for_creates_layout(mgr, tmp_workspace_root):
    p = mgr.workspace_for("r1")
    assert p.exists()
    run_root = tmp_workspace_root / "scratch" / "r1"
    assert (run_root / "uploads").exists()
    assert (run_root / "outputs").exists()


def test_workspace_for_is_per_run(mgr):
    a = mgr.workspace_for("r1")
    b = mgr.workspace_for("r2")
    assert a != b


@pytest.mark.asyncio
async def test_promote_artifact_to_store(mgr):
    await mgr.promote_artifact(
        "r1",
        Artifact(id="a1", kind="report", content="x", mime_type="text/plain", source_node="n"),
    )
    got = await mgr.artifact_store.get("r1", "a1")
    assert got is not None


@pytest.mark.asyncio
async def test_snapshot_skipped_without_session_kv(mgr):
    # Without session_kv, snapshot is a no-op (returns False, no crash).
    ok = await mgr.snapshot_scratch("r1", step=2)
    assert ok is False


@pytest.mark.asyncio
async def test_snapshot_writes_when_interval_hits(tmp_workspace_root):
    from hanflow.persistence.backends.sqlite import SqliteKVBackend

    kv = SqliteKVBackend(path=tmp_workspace_root / "snap.db")
    await kv.setup()
    art = ArtifactStore(LocalFsArtifactBackend(root=tmp_workspace_root / "artifacts"))
    mgr = WorkspaceManager(
        scratch_root=tmp_workspace_root / "scratch",
        artifact_store=art,
        session_kv=kv,
        snapshot_interval_steps=2,
    )
    # write a file into scratch first
    ws = mgr.workspace_for("r1")
    (ws / "note.md").write_text("hello")
    ok = await mgr.snapshot_scratch("r1", step=2)
    assert ok is True


@pytest.mark.asyncio
async def test_restore_scratch_round_trip(tmp_workspace_root):
    from hanflow.persistence.backends.sqlite import SqliteKVBackend

    kv = SqliteKVBackend(path=tmp_workspace_root / "snap.db")
    await kv.setup()
    art = ArtifactStore(LocalFsArtifactBackend(root=tmp_workspace_root / "artifacts"))
    mgr = WorkspaceManager(
        scratch_root=tmp_workspace_root / "scratch",
        artifact_store=art,
        session_kv=kv,
        snapshot_interval_steps=1,
    )
    ws = mgr.workspace_for("r1")
    (ws / "note.md").write_text("snapshot me")
    assert await mgr.snapshot_scratch("r1", step=1) is True
    # wipe the workspace file, then restore from snapshot
    (ws / "note.md").unlink()
    assert await mgr.restore_scratch("r1") is True
    assert (ws / "note.md").read_text() == "snapshot me"
