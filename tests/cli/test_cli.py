from pathlib import Path

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
