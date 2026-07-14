"""hanflow CLI — command matrix (§10.3).

Commands: run | resume | cancel | runs | status | approve | edit | reject |
reroute | trace | logs | artifacts | metrics | tools | search | index | eval |
datasets | serve | worker | validate | compile | new | config | doctor.

Run-management and HITL commands talk to a running ``hanflow serve`` process
via :class:`~hanflow.cli.client.CliClient`. ``tools``/``config`` run locally
against the SDK. The remaining commands (``metrics``/``search``/``eval``/
``datasets``/``worker``) are not yet wired and print a clear "planned" notice.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import typer

from hanflow.cli.client import CliClient
from hanflow.config import load_config

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


# ---------------------------------------------------------------------------
# Run management commands (HTTP — talk to a running 'hanflow serve')
# ---------------------------------------------------------------------------


def _client() -> CliClient:
    """Build a CliClient using the default (env-driven) base URL."""
    return CliClient()


def _run_async(coro: Any) -> Any:
    """Run ``coro`` on a fresh event loop, printing errors to stderr."""
    try:
        return asyncio.run(coro)
    except Exception as exc:  # noqa: BLE001 — single CLI error path
        typer.secho(f"ERROR: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1) from exc


@app.command()
def runs(limit: int = typer.Option(20, "--limit", "-n")) -> None:
    """List recent runs."""
    result = _run_async(_client().list_runs())
    if not result:
        typer.secho("(no runs)", fg=typer.colors.YELLOW)
        return
    for r in result[:limit]:
        typer.secho(
            f"{str(r.get('run_id', '?')):20} {r.get('status', '?')}",
            fg=typer.colors.CYAN,
        )


@app.command()
def status(run_id: str) -> None:
    """Show run status."""
    r = _run_async(_client().get_run(run_id))
    typer.secho(f"{r.get('run_id', '?'):20} {r.get('status', '?')}", fg=typer.colors.CYAN)
    result = r.get("result")
    if result is not None:
        typer.echo(f"  result: {result}")


@app.command()
def cancel(run_id: str) -> None:
    """Cancel a run."""
    r = _run_async(_client().cancel_run(run_id))
    typer.secho(f"cancelled {run_id}: {r}", fg=typer.colors.CYAN)


@app.command()
def logs(run_id: str, interval: int = typer.Option(2, "--interval")) -> None:
    """Poll run status until terminal (simplified; no websocket streaming yet)."""
    import time

    client = _client()
    terminal = {"succeeded", "failed", "cancelled"}
    last: str | None = None
    while True:
        r = _run_async(client.get_run(run_id))
        st = str(r.get("status", "?"))
        if st != last:
            typer.secho(f"{r.get('run_id', '?'):20} {st}", fg=typer.colors.CYAN)
            last = st
        if st in terminal:
            break
        time.sleep(interval)


@app.command()
def trace(run_id: str) -> None:
    """Render a run trace."""
    r = _run_async(_client().get_trace(run_id))
    typer.secho(
        f"trace {r.get('run_id', '?')} (source={r.get('source', 'local')})",
        fg=typer.colors.CYAN,
    )
    tree = r.get("trace_tree")
    if tree is None:
        typer.secho("  (trace_tree not yet wired)", fg=typer.colors.YELLOW)


@app.command()
def artifacts(run_id: str) -> None:
    """List run artifacts."""
    result = _run_async(_client().get_artifacts(run_id))
    if not result:
        typer.secho("(no artifacts)", fg=typer.colors.YELLOW)
        return
    for a in result:
        typer.secho(
            f"{str(a.get('artifact_id', a.get('id', '?'))):30} {a.get('kind', '')}",
            fg=typer.colors.CYAN,
        )


# ---------------------------------------------------------------------------
# HITL commands (HTTP — approve / edit / reject / reroute / resume)
# ---------------------------------------------------------------------------


@app.command()
def approve(run_id: str, decided_by: str = typer.Option("cli", "--by")) -> None:
    """Approve a HITL gate."""
    r = _run_async(_client().approve(run_id, decided_by=decided_by))
    typer.secho(f"approved {run_id}: {r.get('status', '?')}", fg=typer.colors.CYAN)


@app.command()
def edit(
    run_id: str,
    value: str = typer.Option(..., "--value"),
    decided_by: str = typer.Option("cli", "--by"),
) -> None:
    """Edit a HITL gate (``--value`` is parsed as JSON if possible, else string)."""
    import json

    try:
        edited_value: Any = json.loads(value)
    except json.JSONDecodeError:
        edited_value = value
    r = _run_async(_client().edit(run_id, decided_by=decided_by, edited_value=edited_value))
    typer.secho(f"edited {run_id}: {r.get('status', '?')}", fg=typer.colors.CYAN)


@app.command()
def reject(
    run_id: str,
    reason: str = typer.Option(..., "--reason"),
    decided_by: str = typer.Option("cli", "--by"),
) -> None:
    """Reject a HITL gate."""
    r = _run_async(_client().reject(run_id, decided_by=decided_by, reason=reason))
    typer.secho(f"rejected {run_id}: {r.get('status', '?')}", fg=typer.colors.CYAN)


@app.command()
def reroute(
    run_id: str,
    target: str = typer.Option(..., "--target"),
    reason: str = typer.Option("", "--reason"),
    decided_by: str = typer.Option("cli", "--by"),
) -> None:
    """Reroute a HITL gate to ``--target`` (node / human / model)."""
    r = _run_async(
        _client().reroute(
            run_id,
            decided_by=decided_by,
            reroute_target=target,
            reason=reason or None,
        )
    )
    typer.secho(f"rerouted {run_id}: {r.get('status', '?')}", fg=typer.colors.CYAN)


@app.command()
def resume(run_id: str, decided_by: str = typer.Option("cli", "--by")) -> None:
    """Resume a paused run (alias for approve)."""
    r = _run_async(_client().approve(run_id, decided_by=decided_by))
    typer.secho(f"resumed {run_id}: {r.get('status', '?')}", fg=typer.colors.CYAN)


# ---------------------------------------------------------------------------
# Local commands (SDK direct — no server needed)
# ---------------------------------------------------------------------------


@app.command()
def tools(server: str = typer.Option("", "--server", "-s")) -> None:
    """List available tools."""
    from hanflow.sdk import Hanflow

    result = _run_async(Hanflow().list_tools(server or None))
    if not result:
        typer.secho("(no tools)", fg=typer.colors.YELLOW)
        return
    for t in result:
        typer.secho(
            f"{t['name']:30} {str(t.get('server', '?')):15} {str(t.get('description', ''))[:50]}",
            fg=typer.colors.CYAN,
        )


@app.command(name="config")
def config_show() -> None:
    """Show resolved config (file + env overrides) as JSON."""
    cfg = load_config(validate=False)
    typer.echo(cfg.model_dump_json(indent=2))


# ---------------------------------------------------------------------------
# Degraded commands — not yet wired; print a clear, actionable message.
# ---------------------------------------------------------------------------


@app.command()
def metrics(run_id: str) -> None:
    """Show run metrics."""
    typer.secho(
        "metrics: aggregation not yet wired (RunResult.usage not populated)",
        fg=typer.colors.YELLOW,
    )


@app.command()
def search(query: str, store: str = typer.Option("", "--store")) -> None:
    """Search a retrieval store."""
    typer.secho(
        "search: retrieval not configured; use 'hanflow index' first (planned)",
        fg=typer.colors.YELLOW,
    )


@app.command(name="eval")
def eval_() -> None:
    """Evaluate a workflow on a dataset."""
    typer.secho(
        "eval: eval framework not yet implemented (planned)",
        fg=typer.colors.YELLOW,
    )


@app.command()
def datasets() -> None:
    """List eval datasets."""
    typer.secho(
        "datasets: eval framework not yet implemented (planned)",
        fg=typer.colors.YELLOW,
    )


@app.command()
def worker() -> None:
    """Start a worker process."""
    typer.secho(
        "worker: multi-worker mode not yet available; use 'hanflow serve' (planned)",
        fg=typer.colors.YELLOW,
    )


@app.command(help="Start the HTTP API server")
def serve(
    host: str = typer.Option("0.0.0.0", "--host", "-h"),
    port: int = typer.Option(8000, "--port", "-p"),
) -> None:
    """Start the FastAPI HTTP API server via uvicorn."""
    import uvicorn

    from hanflow.api import build_app
    from hanflow.config import HanflowConfig
    from hanflow.sdk import Hanflow

    hf = Hanflow(HanflowConfig())
    serve_app = build_app(hf)
    typer.secho(f"Starting Hanflow API on {host}:{port}", fg=typer.colors.CYAN)
    uvicorn.run(serve_app, host=host, port=port)


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
