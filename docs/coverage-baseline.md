# Coverage Baseline

> First coverage baseline for the `hanflow` package, established by
> `contrib-2026-W31-002`. This is an **informational** baseline — it ships
> with **no `--cov-fail-under` CI gate**. The goal is to give refactors a
> regression signal, not to enforce a threshold.

## How to measure

```bash
make test-cov
# → terminal: per-file stmt%/branch% + uncovered line numbers (term-missing)
# → htmlcov/index.html: browsable annotated source
```

Branch coverage and the omit policy are driven by `[tool.coverage.*]` in
`pyproject.toml`, so `make test-cov` is a thin entry point.

## Baseline numbers

> ⚠️ **The concrete percentages below are filled in by CI.** The contributor
> environment that produced this PR had no network access to PyPI, so
> `pytest-cov` could not be installed locally and the numbers could not be
> measured on the contributor's machine. A maintainer (or PR CI) runs
> `make test-cov` once on the merged tree and records the result here.

| Metric | Value | Absolute denominator |
|--------|-------|----------------------|
| Statements covered | _CI to fill_ | _total stmt count_ |
| Branches covered | _CI to fill_ | _total branch count_ |

> **Why record the absolute denominator (total statements / total branches)?**
> Percentages alone drift when code is added or removed. Keeping the
> denominator next to the percentage makes "did coverage drop, or did the code
> base just grow?" unambiguous when comparing across refactors.

_Version measured against: hanflow **1.2.1** (commit to be filled by CI)._

## Omit policy (and one transient TODO)

`[tool.coverage.run] omit` excludes non-business paths:

| Omit | Reason |
|------|--------|
| `hanflow/observability/providers/*` | **Transient** — see TODO below |
| `hanflow/cli/main.py` | typer command-dispatch shim, not business logic |
| `*/__init__.py` | package markers (mostly re-exports, no logic) |

### TODO — restore observability provider coverage

`hanflow/observability/providers/{langsmith,otel}.py` are real, implemented
backends (the integration boundary — exactly the code that most benefits from
coverage signal). They are omitted from this baseline **only because the SDKs
are not installed in the default test environment, so the modules cannot be
imported and measured**. This is an **environment limitation, not a long-term
policy.**

When provider tests land (install the SDK, or mock it), **drop the
`hanflow/observability/providers/*` omit** — or replace it with per-line
`# pragma: no cover` + a conditional `skip` so the regression signal for the
integration code is restored.

## Why no `--cov-fail-under` gate?

This is the first baseline; the threshold value is unknown. Setting a guess
threshold would either block legitimate work (too high) or be meaningless
(too low). A threshold — if desired — should come later via an ADR that can
reference this measured baseline.

## Comparing across refactors

1. Note this baseline's stmt% / branch% / denominators.
2. After a refactor, run `make test-cov`.
3. Compare both the percentage **and** the denominator. A drop in percentage
   with a stable denominator is a real regression; a drop with a growing
   denominator usually just means new code was added (write tests for it).
