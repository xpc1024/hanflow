from pathlib import Path

import pytest
from typer.testing import CliRunner

from hanflow.cli.main import app

runner = CliRunner()


def test_cli_help_lists_commands():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    out = result.stdout
    for cmd in [
        "run",
        "resume",
        "cancel",
        "runs",
        "status",
        "validate",
        "compile",
        "new",
        "doctor",
        "index",
    ]:
        assert cmd in out


def test_validate_reports_valid_dsl(tmp_path: Path):
    p = tmp_path / "w.yaml"
    p.write_text(
        """
name: w
nodes:
  - id: a
    type: LLM
"""
    )
    result = runner.invoke(app, ["validate", str(p)])
    assert result.exit_code == 0
    assert "valid" in result.stdout.lower()


def test_validate_reports_invalid_dsl(tmp_path: Path):
    p = tmp_path / "w.yaml"
    p.write_text(
        """
name: w
nodes:
  - id: a
    type: LLM
  - id: a
    type: LLM
"""
    )
    result = runner.invoke(app, ["validate", str(p)])
    assert result.exit_code != 0


def test_new_scaffolds_static_template(tmp_path: Path):
    out = tmp_path / "gen"
    result = runner.invoke(app, ["new", "--name", "mywf", "--mode", "static", "--out", str(out)])
    assert result.exit_code == 0
    assert (out / "mywf.yaml").exists()


def test_doctor_runs_health_checks():
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Helpers for CliClient mocking
# ---------------------------------------------------------------------------


def _mock_client(monkeypatch: pytest.MonkeyPatch, method: str, return_value=None, raises=None):
    """Patch ``CliClient.<method>`` to return ``return_value`` or raise ``raises``."""

    async def mock_method(self, *args, **kwargs):
        if raises is not None:
            raise raises
        return return_value

    monkeypatch.setattr(f"hanflow.cli.client.CliClient.{method}", mock_method)


# ---------------------------------------------------------------------------
# Run management commands (Group A — HTTP)
# ---------------------------------------------------------------------------


def test_runs_lists_runs(monkeypatch: pytest.MonkeyPatch):
    _mock_client(monkeypatch, "list_runs", [{"run_id": "abc", "status": "succeeded"}])
    result = runner.invoke(app, ["runs"])
    assert result.exit_code == 0
    assert "abc" in result.stdout
    assert "succeeded" in result.stdout


def test_runs_empty_reports_no_runs(monkeypatch: pytest.MonkeyPatch):
    _mock_client(monkeypatch, "list_runs", [])
    result = runner.invoke(app, ["runs"])
    assert result.exit_code == 0
    assert "no runs" in result.stdout.lower()


def test_runs_error_exits_nonzero(monkeypatch: pytest.MonkeyPatch):
    from hanflow.core.errors import CLIError

    _mock_client(monkeypatch, "list_runs", raises=CLIError("request failed: refused"))
    result = runner.invoke(app, ["runs"])
    assert result.exit_code == 1


def test_status_shows_run(monkeypatch: pytest.MonkeyPatch):
    _mock_client(monkeypatch, "get_run", {"run_id": "abc", "status": "running"})
    result = runner.invoke(app, ["status", "abc"])
    assert result.exit_code == 0
    assert "abc" in result.stdout
    assert "running" in result.stdout


def test_status_404_exits_nonzero(monkeypatch: pytest.MonkeyPatch):
    from hanflow.core.errors import CLIError

    _mock_client(monkeypatch, "get_run", raises=CLIError("run not found: abc"))
    result = runner.invoke(app, ["status", "abc"])
    assert result.exit_code == 1


def test_cancel(monkeypatch: pytest.MonkeyPatch):
    _mock_client(monkeypatch, "cancel_run", {"cancelled": True})
    result = runner.invoke(app, ["cancel", "abc"])
    assert result.exit_code == 0


def test_trace(monkeypatch: pytest.MonkeyPatch):
    _mock_client(
        monkeypatch,
        "get_trace",
        {"run_id": "abc", "trace_tree": None, "source": "local"},
    )
    result = runner.invoke(app, ["trace", "abc"])
    assert result.exit_code == 0
    assert "abc" in result.stdout


def test_artifacts(monkeypatch: pytest.MonkeyPatch):
    _mock_client(monkeypatch, "get_artifacts", [{"artifact_id": "a1", "kind": "text"}])
    result = runner.invoke(app, ["artifacts", "abc"])
    assert result.exit_code == 0


def test_logs_polls_until_terminal(monkeypatch: pytest.MonkeyPatch):
    # First call running, then succeeded — logs should stop after success.
    states = iter(
        [
            {"run_id": "abc", "status": "running"},
            {"run_id": "abc", "status": "succeeded"},
        ]
    )

    async def get_run(self, run_id):
        return next(states)

    monkeypatch.setattr("hanflow.cli.client.CliClient.get_run", get_run)
    result = runner.invoke(app, ["logs", "abc", "--interval", "0"])
    assert result.exit_code == 0
    assert "succeeded" in result.stdout


# ---------------------------------------------------------------------------
# HITL commands (Group A — HTTP)
# ---------------------------------------------------------------------------


def test_approve(monkeypatch: pytest.MonkeyPatch):
    _mock_client(monkeypatch, "approve", {"run_id": "abc", "status": "resumed"})
    result = runner.invoke(app, ["approve", "abc"])
    assert result.exit_code == 0
    assert "resumed" in result.stdout


def test_approve_passes_decided_by(monkeypatch: pytest.MonkeyPatch):
    captured = {}

    async def approve(self, run_id, decided_by, form=None):
        captured["decided_by"] = decided_by
        return {"run_id": run_id, "status": "resumed"}

    monkeypatch.setattr("hanflow.cli.client.CliClient.approve", approve)
    result = runner.invoke(app, ["approve", "abc", "--by", "alice"])
    assert result.exit_code == 0
    assert captured["decided_by"] == "alice"


def test_edit_requires_value():
    result = runner.invoke(app, ["edit", "abc"])
    assert result.exit_code != 0


def test_edit(monkeypatch: pytest.MonkeyPatch):
    _mock_client(monkeypatch, "edit", {"run_id": "abc", "status": "resumed"})
    result = runner.invoke(app, ["edit", "abc", "--value", '{"x":1}'])
    assert result.exit_code == 0


def test_reject_requires_reason():
    result = runner.invoke(app, ["reject", "abc"])
    assert result.exit_code != 0


def test_reject(monkeypatch: pytest.MonkeyPatch):
    _mock_client(monkeypatch, "reject", {"run_id": "abc", "status": "resumed"})
    result = runner.invoke(app, ["reject", "abc", "--reason", "bad"])
    assert result.exit_code == 0


def test_reroute_requires_target():
    result = runner.invoke(app, ["reroute", "abc"])
    assert result.exit_code != 0


def test_reroute(monkeypatch: pytest.MonkeyPatch):
    _mock_client(monkeypatch, "reroute", {"run_id": "abc", "status": "resumed"})
    result = runner.invoke(app, ["reroute", "abc", "--target", "human"])
    assert result.exit_code == 0


def test_resume_alias_calls_approve(monkeypatch: pytest.MonkeyPatch):
    _mock_client(monkeypatch, "approve", {"run_id": "abc", "status": "resumed"})
    result = runner.invoke(app, ["resume", "abc"])
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Local commands (Group A — SDK direct)
# ---------------------------------------------------------------------------


def test_tools(monkeypatch: pytest.MonkeyPatch):
    async def mock_list_tools(self, server=None):
        return [{"name": "say", "server": "echo", "description": "echo tool"}]

    monkeypatch.setattr("hanflow.sdk.Hanflow.list_tools", mock_list_tools)
    result = runner.invoke(app, ["tools"])
    assert result.exit_code == 0
    assert "say" in result.stdout
    assert "echo" in result.stdout


def test_tools_error_exits_nonzero(monkeypatch: pytest.MonkeyPatch):
    async def mock_list_tools(self, server=None):
        raise RuntimeError("bus not started")

    monkeypatch.setattr("hanflow.sdk.Hanflow.list_tools", mock_list_tools)
    result = runner.invoke(app, ["tools"])
    assert result.exit_code == 1


def test_config_outputs_json(monkeypatch: pytest.MonkeyPatch):
    class _FakeCfg:
        def model_dump_json(self, indent):
            return '{"test": true}'

    monkeypatch.setattr("hanflow.cli.main.load_config", lambda **kw: _FakeCfg())
    result = runner.invoke(app, ["config"])
    assert result.exit_code == 0
    assert '"test"' in result.stdout


# ---------------------------------------------------------------------------
# Degraded commands (Group B — clear "planned" messages)
# ---------------------------------------------------------------------------


def test_metrics_shows_not_wired():
    result = runner.invoke(app, ["metrics", "abc"])
    assert result.exit_code == 0
    assert "not yet wired" in result.stdout


def test_search_shows_not_configured():
    result = runner.invoke(app, ["search", "test"])
    assert result.exit_code == 0
    assert "not configured" in result.stdout


def test_eval_shows_planned():
    result = runner.invoke(app, ["eval"])
    assert result.exit_code == 0
    assert "planned" in result.stdout.lower()


def test_datasets_shows_planned():
    result = runner.invoke(app, ["datasets"])
    assert result.exit_code == 0
    assert "planned" in result.stdout.lower()


def test_worker_shows_use_serve():
    result = runner.invoke(app, ["worker"])
    assert result.exit_code == 0
    assert "hanflow serve" in result.stdout


# ---------------------------------------------------------------------------
# Regression: no stub message remains
# ---------------------------------------------------------------------------


def test_no_command_says_delegates_to_sdk():
    """None of the former stub commands should output 'delegates to SDK'."""
    stub_commands = [
        "resume",
        "cancel",
        "runs",
        "status",
        "approve",
        "edit",
        "reject",
        "reroute",
        "trace",
        "logs",
        "artifacts",
        "metrics",
        "tools",
        "search",
        "eval",
        "datasets",
        "worker",
        "config",
    ]
    for cmd in stub_commands:
        result = runner.invoke(app, [cmd, "--help"])
        assert "delegates to SDK" not in result.stdout, f"{cmd} still has stub help text"
