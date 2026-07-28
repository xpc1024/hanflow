# Coverage Baseline — contrib-2026-W31-001

> 开发态快照,非用户文档(不入 hanflow-site)。由 `make test-cov` 生成,记录引入 pytest-cov 时的覆盖率现状。
> **此为度量基线,非质量目标** —— 数字反映当前测试覆盖,不代表未覆盖即缺陷。

- **生成时间**: 2026-07-28
- **pytest-cov 版本**: 7.1.0
- **pytest 版本**: 9.1.1
- **coverage.py 版本**: 7.15.2(pytest-cov 的传递依赖,非项目直接依赖)
- **测量命令**: `make test-cov`(等价 `uv run pytest --cov=hanflow --cov-report=term-missing --cov-report=html`)
- **测试结果**: 323 passed, 1 skipped(integration, 需 `HANFLOW_INTEGRATION=1`), 3 failed(**pre-existing**,与本贡献无关,见下文)

## 总体

- **语句覆盖**: 82%(3829 stmts, 558 miss)
- **分支覆盖**: branch=true 已启用(758 branches, 159 partial)

## 各模块覆盖率

> 列: `Stmts`=语句数, `Miss`=未覆盖语句, `Branch`=分支数, `BrPart`=部分分支, `Cover`=覆盖率, `Missing`=未覆盖行号(截断显示,完整见 `make test-cov` 输出)

| 模块 | Stmts | Miss | Branch | BrPart | Cover | Missing |
|------|-------|------|--------|--------|-------|---------|
| `hanflow/api/deps.py` | 20 | 1 | 4 | 1 | 92% | 23 |
| `hanflow/api/routes/hitl.py` | 75 | 10 | 24 | 7 | 79% | 40->39, 60, 72-76, 94, 117, 134, 151 |
| `hanflow/api/routes/observe.py` | 21 | 0 | 2 | 0 | 100% |  |
| `hanflow/api/routes/runs.py` | 49 | 6 | 8 | 2 | 86% | 52-53, 57-59, 100 |
| `hanflow/api/routes/runs_ws.py` | 17 | 12 | 2 | 0 | 26% | 16-29 |
| `hanflow/api/routes/schema.py` | 19 | 0 | 2 | 0 | 100% |  |
| `hanflow/api/routes/webhooks.py` | 36 | 26 | 8 | 0 | 23% | 24-62, 70-71 |
| `hanflow/api/routes/workflows.py` | 113 | 15 | 22 | 7 | 84% | 53->62, 55, 60-61, 64->68, 66-67, 107... |
| `hanflow/api/ws.py` | 13 | 0 | 2 | 0 | 100% |  |
| `hanflow/atoms/base.py` | 11 | 0 | 0 | 0 | 100% |  |
| `hanflow/atoms/execution.py` | 78 | 10 | 10 | 1 | 88% | 61->95, 99-113, 117-121, 141 |
| `hanflow/atoms/research.py` | 101 | 12 | 26 | 5 | 87% | 84, 88, 102-103, 113-118, 141, 164->1... |
| `hanflow/cli/client.py` | 68 | 17 | 16 | 5 | 69% | 41, 69-70, 74, 77-78, 91, 95, 115, 13... |
| `hanflow/config.py` | 112 | 9 | 38 | 5 | 91% | 107->115, 112-113, 135, 138-142, 148-... |
| `hanflow/core/context.py` | 55 | 6 | 0 | 0 | 89% | 109, 120, 123, 126, 146, 149 |
| `hanflow/core/dsl.py` | 100 | 2 | 46 | 2 | 97% | 99, 110 |
| `hanflow/core/errors.py` | 49 | 0 | 0 | 0 | 100% |  |
| `hanflow/core/expr.py` | 144 | 14 | 60 | 12 | 87% | 69, 71, 95-97, 112, 126->108, 173, 18... |
| `hanflow/core/result.py` | 78 | 0 | 0 | 0 | 100% |  |
| `hanflow/core/state.py` | 34 | 0 | 0 | 0 | 100% |  |
| `hanflow/isolation/sandbox.py` | 69 | 2 | 8 | 2 | 95% | 72, 148 |
| `hanflow/memory/backends/local_fs.py` | 34 | 1 | 10 | 2 | 93% | 39->exit, 44 |
| `hanflow/memory/filesystem.py` | 61 | 3 | 12 | 4 | 90% | 46, 77, 85->83, 107 |
| `hanflow/memory/skills.py` | 69 | 3 | 20 | 4 | 92% | 57, 60->58, 67, 108 |
| `hanflow/models/governance.py` | 43 | 1 | 8 | 1 | 96% | 64 |
| `hanflow/models/privacy.py` | 76 | 3 | 16 | 3 | 93% | 98, 132, 146 |
| `hanflow/models/providers/anthropic.py` | 28 | 12 | 0 | 0 | 57% | 31-32, 35-47 |
| `hanflow/models/providers/base.py` | 19 | 0 | 0 | 0 | 100% |  |
| `hanflow/models/providers/deepseek.py` | 12 | 0 | 0 | 0 | 100% |  |
| `hanflow/models/providers/fake.py` | 32 | 3 | 6 | 1 | 89% | 40, 43, 61 |
| `hanflow/models/providers/glm.py` | 28 | 12 | 0 | 0 | 57% | 30-31, 34-44 |
| `hanflow/models/providers/ollama.py` | 24 | 24 | 0 | 0 | 0% | 3-36 |
| `hanflow/models/providers/openai.py` | 29 | 14 | 0 | 0 | 52% | 25, 28, 31-32, 35-45 |
| `hanflow/models/providers/vllm.py` | 11 | 1 | 0 | 0 | 91% | 21 |
| `hanflow/models/router.py` | 67 | 6 | 24 | 7 | 86% | 84, 98, 115, 125, 135, 139->138, 141 |
| `hanflow/models/strategies/base.py` | 19 | 0 | 0 | 0 | 100% |  |
| `hanflow/models/strategies/cost.py` | 13 | 1 | 4 | 1 | 88% | 24 |
| `hanflow/models/strategies/fallback.py` | 9 | 0 | 0 | 0 | 100% |  |
| `hanflow/models/strategies/role.py` | 12 | 1 | 2 | 1 | 86% | 20 |
| `hanflow/models/strategies/static.py` | 10 | 0 | 2 | 0 | 100% |  |
| `hanflow/models/strategies/task.py` | 12 | 1 | 2 | 1 | 86% | 20 |
| `hanflow/observability/provider.py` | 21 | 6 | 6 | 2 | 70% | 23, 26, 41-43, 45-47 |
| `hanflow/observability/trace.py` | 75 | 3 | 6 | 2 | 94% | 85, 90->exit, 94, 135 |
| `hanflow/orchestration/compiler.py` | 106 | 28 | 34 | 7 | 72% | 59, 76->75, 78, 95-111, 117->120, 147... |
| `hanflow/orchestration/context_impl.py` | 81 | 22 | 16 | 3 | 66% | 86, 93-95, 106-111, 114, 118-120, 123... |
| `hanflow/orchestration/nodes/base.py` | 7 | 7 | 0 | 0 | 0% | 8-18 |
| `hanflow/orchestration/nodes/control.py` | 70 | 31 | 22 | 2 | 45% | 22-26, 29, 36-39, 42, 49-54, 57, 64-6... |
| `hanflow/orchestration/nodes/coordinator.py` | 68 | 6 | 14 | 4 | 88% | 33, 35, 55, 63, 121-122 |
| `hanflow/orchestration/nodes/knowledge.py` | 28 | 3 | 6 | 3 | 82% | 23, 25, 37 |
| `hanflow/orchestration/nodes/leaf.py` | 64 | 22 | 8 | 2 | 61% | 28, 55, 70-72, 75-93, 100-102, 105-124 |
| `hanflow/orchestration/nodes/state_ops.py` | 38 | 10 | 10 | 3 | 65% | 23, 25, 33->35, 43-45, 48-56 |
| `hanflow/orchestration/registry.py` | 26 | 1 | 4 | 1 | 93% | 24 |
| `hanflow/persistence/artifact.py` | 20 | 0 | 0 | 0 | 100% |  |
| `hanflow/persistence/backends/local_fs.py` | 59 | 7 | 16 | 5 | 84% | 29, 43, 51, 56, 67, 77-78 |
| `hanflow/persistence/backends/sqlite.py` | 60 | 8 | 2 | 1 | 85% | 35-36, 99, 108-112 |
| `hanflow/persistence/base.py` | 4 | 0 | 0 | 0 | 100% |  |
| `hanflow/persistence/checkpoint.py` | 30 | 3 | 2 | 0 | 91% | 83, 86, 89 |
| `hanflow/persistence/resume.py` | 45 | 7 | 8 | 1 | 81% | 50, 76-80, 100 |
| `hanflow/persistence/session.py` | 61 | 1 | 8 | 1 | 97% | 70 |
| `hanflow/persistence/workspace.py` | 59 | 11 | 12 | 4 | 79% | 51-53, 64, 69->68, 76, 79, 91-95 |
| `hanflow/retrieval/embedding.py` | 67 | 29 | 4 | 0 | 56% | 30, 44-46, 50, 53-57, 66-68, 72, 75-8... |
| `hanflow/retrieval/fulltext/base.py` | 15 | 0 | 0 | 0 | 100% |  |
| `hanflow/retrieval/fulltext/memory_fts.py` | 38 | 10 | 14 | 2 | 65% | 38, 41->36, 49-56, 59 |
| `hanflow/retrieval/hybrid.py` | 77 | 2 | 18 | 2 | 96% | 68, 112 |
| `hanflow/retrieval/indexing.py` | 53 | 0 | 10 | 1 | 98% | 47->60 |
| `hanflow/retrieval/provider.py` | 66 | 4 | 0 | 0 | 94% | 144, 204-206 |
| `hanflow/retrieval/reranker.py` | 31 | 6 | 0 | 0 | 81% | 41-42, 46, 55-56, 59 |
| `hanflow/retrieval/vector/base.py` | 14 | 0 | 0 | 0 | 100% |  |
| `hanflow/retrieval/vector/memory.py` | 67 | 16 | 38 | 8 | 68% | 56-60, 63, 66, 74, 82->101, 85-86, 88... |
| `hanflow/runtime/scheduler.py` | 17 | 0 | 2 | 0 | 100% |  |
| `hanflow/sdk.py` | 189 | 18 | 34 | 10 | 87% | 79-80, 86, 103-105, 170, 180, 193->20... |
| `hanflow/tools/builtin/base.py` | 13 | 0 | 0 | 0 | 100% |  |
| `hanflow/tools/builtin/code_exec.py` | 32 | 6 | 6 | 3 | 76% | 42, 44, 48, 62-64 |
| `hanflow/tools/builtin/filesystem.py` | 31 | 4 | 6 | 1 | 81% | 77-80 |
| `hanflow/tools/builtin/http_request.py` | 19 | 3 | 2 | 1 | 81% | 39, 50-51 |
| `hanflow/tools/builtin/shell.py` | 27 | 4 | 4 | 1 | 84% | 49, 59-61 |
| `hanflow/tools/builtin/vector_search.py` | 17 | 5 | 4 | 1 | 62% | 22, 43-48 |
| `hanflow/tools/builtin/web_fetch.py` | 21 | 6 | 2 | 1 | 70% | 34-39, 43 |
| `hanflow/tools/builtin/web_search.py` | 17 | 1 | 2 | 1 | 89% | 38 |
| `hanflow/tools/bus.py` | 112 | 19 | 28 | 8 | 79% | 38, 50, 89, 103, 116, 126-132, 142, 1... |
| `hanflow/tools/transport.py` | 86 | 20 | 20 | 3 | 73% | 60-61, 69, 72, 75, 78-79, 90, 98-100,... |
| `hanflow/workflows/store.py` | 28 | 1 | 6 | 1 | 94% | 43 |
| **TOTAL** | **3829** | **558** | **758** | **159** | **82%** | — |

## 测量范围说明

omit 了(`pyproject.toml [tool.coverage.run]`):
- `hanflow/observability/providers/*`(需外部 backend: langsmith / opentelemetry-sdk,本地未装时不 import)
- `hanflow/cli/main.py`(typer 命令调度,声明式胶水)
- `*/__init__.py`(空包标记)

## 已知的 3 个 pre-existing 测试失败(与本贡献无关)

基线采集时跑全量测试,有 3 个失败。经核实**在 master(本贡献改动前)同样失败**,非本贡献引入:

1. `tests/observability/test_otel.py::test_otel_from_config_builds_tracer` —— `ModuleNotFoundError: No module named 'opentelemetry'`(需 `uv sync --extra otel`,环境缺依赖)
2. `tests/test_smoke.py::test_package_importable` —— `assert hanflow.__version__ == "0.1.0"`,实际 `1.0.1`(v1.0.1 release 后未更新的陈旧断言)
3. `tests/test_e2e_v0.py::test_v0_all_subsystems_importable` —— 同样的 `__version__ == "0.1.0"` 陈旧断言

覆盖率数字基于 323 passed 测试采集,**未受这 3 个失败影响**(它们在 collect/import 阶段即失败,不产生额外的代码执行覆盖)。

## 如何复现

```bash
uv sync --extra dev
make test-cov
# 或: uv run pytest --cov=hanflow --cov-report=term-missing --cov-report=html
```

HTML 逐行报告:`htmlcov/index.html`。
