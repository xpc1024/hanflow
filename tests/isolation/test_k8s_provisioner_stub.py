"""K8sProvisioner stub tests (cycle 2026-W30-1.1.1).

K8sProvisioner is a placeholder (Phase 10); both provision and destroy raise
NotImplementedError per CHARTER §4 placeholder convention.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from hanflow.core.sandbox_contract import RunSandbox, SandboxMode
from hanflow.isolation.sandbox import K8sProvisioner


class _FakeMgr:
    def workspace_for(self, run_id: str) -> Path:
        return Path(f"/tmp/{run_id}")


def test_k8s_provisioner_name():
    assert K8sProvisioner.name == "k8s"


@pytest.mark.asyncio
async def test_k8s_provisioner_provision_raises_not_implemented():
    sb = RunSandbox.create("r1", SandboxMode.K8S, _FakeMgr())
    p = K8sProvisioner()
    with pytest.raises(NotImplementedError, match="Phase 10"):
        await p.provision(sb)


@pytest.mark.asyncio
async def test_k8s_provisioner_destroy_raises_not_implemented():
    p = K8sProvisioner()
    # destroy stub raises before reading its arg, so we can pass a minimal stub
    class _FakeProvisioned:
        run_id = "r1"
    with pytest.raises(NotImplementedError, match="Phase 10"):
        await p.destroy(_FakeProvisioned())  # type: ignore[arg-type]


def test_k8s_provisioner_message_mentions_phase_10():
    """Placeholder message explicitly names Phase 10 (CHARTER §4 convention)."""
    import inspect

    src = inspect.getsource(K8sProvisioner)
    assert "Phase 10" in src
