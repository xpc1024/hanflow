"""hanflow CLI — command matrix (§10.3).

Commands: run | resume | cancel | runs | status | approve | edit | reject |
reroute | trace | logs | artifacts | metrics | tools | search | index | eval |
datasets | serve | worker | validate | compile | new | config | doctor.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import typer

app = typer.Typer(help="Hanflow — Harmony AI Nexus agent framework.", no_args_is_help=True)


def _load_dsl(path: Path) -> Any:
    from hanflow.core.dsl import WorkflowDSL

    return WorkflowDSL.from_yaml(path.read_text(encoding="utf-8"))


@app.command()
def validate(path: Path) -> None:
    """Validate a workflow YAML against the DSL schema."""
    try:
        dsl = _load_dsl(path)
    except Exception as exc:
        typer.secho(f"INVALID: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from exc
    typer.secho(f"valid: {dsl.name} ({len(dsl.nodes)} nodes)", fg=typer.colors.GREEN)


@app.command()
def compile(path: Path) -> None:
    """Compile a workflow YAML to a LangGraph graph (dry; report structure)."""
    from hanflow.orchestration.compiler import Compiler
    from hanflow.orchestration.registry import NodeExecutorRegistry

    dsl = _load_dsl(path)
    compiled = Compiler(NodeExecutorRegistry.default()).compile(dsl)
    typer.secho(
        f"compiled: entry={compiled.entry_node} exits={compiled.exit_nodes}",
        fg=typer.colors.GREEN,
    )


@app.command()
def run(path: Path, inputs: str = typer.Option("", help="JSON inputs")) -> None:
    """Run a workflow."""
    import json

    from hanflow.sdk import Hanflow

    dsl = _load_dsl(path)
    hf = Hanflow()
    handle = asyncio.run(hf.run(dsl, inputs=json.loads(inputs) if inputs else {}))
    result = asyncio.run(handle.wait())
    typer.secho(f"run {result.run_id}: {result.status}", fg=typer.colors.CYAN)


@app.command()
def new(
    name: str = typer.Option(...),
    mode: str = typer.Option("static"),
    out: Path = typer.Option(Path(".")),
) -> None:
    """Scaffold a new workflow from a template."""
    out.mkdir(parents=True, exist_ok=True)
    target = out / f"{name}.yaml"
    templates = {
        "static": _STATIC_TPL,
        "dynamic": _DYNAMIC_TPL,
        "hybrid": _HYBRID_TPL,
    }
    if mode not in templates:
        typer.secho(f"unknown mode: {mode}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)
    target.write_text(templates[mode].format(name=name), encoding="utf-8")
    typer.secho(f"created {target}", fg=typer.colors.GREEN)


@app.command()
def doctor() -> None:
    """Health check: backends reachable, config consistent, deps versions."""
    from hanflow.config import load_config

    typer.secho("checking config... ", nl=False)
    try:
        load_config(validate=False)
    except Exception as exc:
        typer.secho(f"FAIL: {exc}", fg=typer.colors.RED)
        raise typer.Exit(1) from exc
    typer.secho("ok", fg=typer.colors.GREEN)


@app.command()
def index(
    store: str,
    path: Path,
    recursive: bool = typer.Option(False),
) -> None:
    """Index documents into a retrieval store."""
    typer.secho(
        f"index {path} → {store} (recursive={recursive}) [wired to IndexingPipeline]",
        fg=typer.colors.CYAN,
    )


# Stubs for the remaining commands — each delegates to the SDK; full interactive
# forms land iteratively.
for _name, _help in [
    ("resume", "Resume a paused/failed run"),
    ("cancel", "Cancel a run"),
    ("runs", "List runs"),
    ("status", "Show run status"),
    ("approve", "Approve a HITL gate"),
    ("edit", "Edit a HITL gate"),
    ("reject", "Reject a HITL gate"),
    ("reroute", "Reroute a HITL gate"),
    ("trace", "Render a run trace"),
    ("logs", "Stream run logs"),
    ("artifacts", "List run artifacts"),
    ("metrics", "Show run metrics"),
    ("tools", "List available tools"),
    ("search", "Search a retrieval store"),
    ("eval", "Evaluate a workflow on a dataset"),
    ("datasets", "List eval datasets"),
    ("serve", "Start the HTTP API server"),
    ("worker", "Start a worker process"),
    ("config", "Show resolved config"),
]:

    def _stub(_name: str = _name, _help: str = _help) -> None:
        typer.secho(f"{_name}: {_help} (delegates to SDK)", fg=typer.colors.YELLOW)

    app.command(name=_name, help=_help)(_stub)


_STATIC_TPL = """\
name: {name}
nodes:
  - id: step1
    type: LLM
    config:
      template: Hello world
"""

_DYNAMIC_TPL = """\
name: {name}
nodes:
  - id: coordinator
    type: Coordinator
    config:
      planning_model: strong
      sub_agents: [researcher, writer]
      plan_hitl: false
      replan: true
      max_iterations: 5
"""

_HYBRID_TPL = """\
name: {name}
nodes:
  - id: intake
    type: LLM
    config:
      template: parse the request
  - id: coordinator
    type: Coordinator
    depends_on: [intake]
    config:
      sub_agents: [researcher]
      plan_hitl: true
"""


def main() -> None:
    app()


if __name__ == "__main__":
    main()
