<div align="center">

# Hanflow

**Harmony AI Nexus — a high-control agent framework built on LangGraph**

Static workflows · dynamic agents · hybrid orchestration, all from one unified DSL — no mode switching required.

[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-%E2%89%A5%203.11-blue.svg)](https://www.python.org/)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.2.0-0a0a0a.svg)](https://github.com/langchain-ai/langgraph)
[![Version](https://img.shields.io/badge/version-1.2.3-green.svg)](CHANGELOG.md)
[![CI](https://github.com/xpc1024/hanflow/actions/workflows/ci.yml/badge.svg)](https://github.com/xpc1024/hanflow/actions)

🌐 **[Website](https://hanflow.icu)**  ·  ⭐ **[GitHub](https://github.com/xpc1024/hanflow)**  ·  ⭐ **[Gitee](https://gitee.com/easy-es/hanflow)**  ·  [Contributors Wall](https://hanflow.icu/zh/contributors)  ·  [中文](README-ZH.md)

</div>

---

## What is Hanflow?

Today's AI orchestration is split between two camps, each with a real limitation:

- **Dynamic agents** are flexible and autonomous, but unpredictable and prone to hallucination — hard to trust in production.
- **Static workflows** are stable and reproducible, but brittle when faced with open-ended tasks.

**Hanflow does not force you to choose.** Under a single YAML DSL it supports pure static workflows, pure dynamic agents, and recursively combined hybrid modes — all compiled to a LangGraph `StateGraph`, with no mode switching anywhere.

Going further, Hanflow treats the following as **first-class citizens by design**, not retrofitted patches:

- Privacy-aware model routing (regulated data is routed to local models automatically)
- RAG retrieval (vector / full-text / hybrid)
- Human-in-the-loop approval (HITL)
- End-to-end observability (LangSmith / OpenTelemetry)

---

## Core Advantages

### 1. One unified DSL, three orchestration shapes

Declarative YAML is the single source of truth: Git-versionable, code-reviewable, and able to express all three shapes with identical syntax:

| Shape | Best for | Characteristics |
| --- | --- | --- |
| **Pure static workflow** | SOP-style processes, compliance & audit | Compile-time-validated DAG; deterministic, reproducible |
| **Pure dynamic agent** | Open-ended research, exploratory tasks | Coordinator orchestrates sub-agents, plans on demand |
| **Hybrid orchestration** | Deterministic skeleton + dynamic decisions | Static nodes embed dynamic sub-graphs, composed recursively |

The DSL natively supports `depends_on`, `condition`, `retry`, and per-node error policies.

### 2. 13 primitive node types

A complete set of orchestration primitives covering control flow, capability invocation, and state — composable both statically and recursively:

| Group | Nodes |
| --- | --- |
| Control flow | `Sequential` · `Parallel` · `Loop` · `Branch` · `HITL` |
| Capabilities | `LLM` · `Tool` · `Research` · `Execution` |
| Dynamic | `Coordinator` |
| State | `Memory` · `Subworkflow` |
| Retrieval | `Knowledge` |

- **Research atom**: deep research with citation provenance — every conclusion is traceable.
- **Execution atom**: long-running tasks using the file system as memory.
- **Subworkflow**: reference and nest workflows for modular reuse.

### 3. Privacy routing — enterprise-grade compliance

`ModelRouter` provides **6 routing strategies**, arbitrated by priority:

```
privacy (hard)  >  role  >  task  >  cost  >  static      +  fallback (activates only on failure)
```

**`PrivacyStrategy` is a single-vote veto (score=∞), enforced as a hard constraint:**

- Sensitivity tiers and PII (personally identifiable information) detection automatically route regulated workloads to local models;
- Supports both `hard` (raises `PrivacyViolationError` and refuses to run when no local provider is available) and `soft` (graceful degradation) enforcement;
- When PII is detected, data is redacted before the routing decision is made.

This makes Hanflow safe to deploy in highly regulated domains such as finance, healthcare, and government.

### 4. Multi-backend RAG retrieval

- Three retrieval modes: **vector**, **full-text**, and **hybrid**;
- Three fusion algorithms: **RRF**, **weighted**, and **cascade**;
- Pluggable embeddings and rerankers.

### 5. MCP tool bus

A unified tool-access layer that abstracts away backend differences. Supports **5 transports**: `stdio` · `sse` · `http` · `websocket` · `inprocess`, with built-in rate limiting and guards against destructive operations.

### 6. Sandboxed execution

Multiple isolation levels for code-execution nodes, balancing flexibility with safety:

| Mode | Description |
| --- | --- |
| `LOCAL` | Host subprocess execution, zero extra dependencies |
| `DOCKER` | Container-level isolation with resource limits, workspace bind mounts, and network policies |
| `K8S` | Cluster-level isolation (reserved) |
| `NONE` | No isolation (trusted, controlled environments only) |

### 7. Time travel and crash recovery

The `L5 Persistence` layer uses **three-tier storage — Checkpoint / Session / Artifact**:

- Runtime state is checkpointed, so a crashed process can resume from its last checkpoint;
- Time-travel replay lets you jump to any historical state and replay execution.

### 8. End-to-end observability

The `L6 Observability` layer cuts across the entire runtime and is **enabled in a single line**:

- **LangSmith**: out-of-the-box tracing, evaluation, and monitoring;
- **OpenTelemetry**: integrate with your existing observability stack.

Every node, every LLM call, and every tool invocation is instrumented automatically.

---

## Six-Layer Architecture

```
┌──────────────────────────────────────────────────────────┐
│  L1 Delivery            CLI · Web Studio · Python SDK      │
│                         REST · WebSocket · Webhook         │
├──────────────────────────────────────────────────────────┤
│  L2 Orchestration       YAML DSL  ──compile──▶  LangGraph  │
│                         13 primitives · recursive compose  │
├──────────────────────────────────────────────────────────┤
│  L3 Capabilities        Research · Execution atoms         │
├──────────────────────────────────────────────────────────┤
│  L4 Foundation          ModelRouter · MCPBus · RAG         │
├──────────────────────────────────────────────────────────┤
│  L5 Persistence         Checkpoint · Session · Artifact    │
├──────────────────────────────────────────────────────────┤
│  L6 Observability       LangSmith · OpenTelemetry          │
└──────────────────────────────────────────────────────────┘
```

Each layer has a clear, decoupled responsibility: the DSL describes intent, the compilation layer turns it into an executable graph, the foundation layer schedules models and tools, the persistence layer guarantees recoverability, and the observability layer provides transparency.

---

## Quick Start

### Requirements

- Python ≥ 3.11
- (Optional) Docker, for containerized deployment and sandbox isolation

### One-command deployment (Docker Compose)

```bash
# 1. Clone and configure
git clone https://github.com/xpc1024/hanflow.git
cd hanflow
cp deploy/docker/hanflow.yaml.example hanflow.yaml
cp deploy/docker/.env.example .env
# Fill in your API keys in .env

# 2. Start all services
cd deploy/docker
docker compose up -d

# 3. Access
#   Web Studio  : http://localhost:3000
#   API         : http://localhost:8000
#   API docs    : http://localhost:8000/docs
```

### Local development

```bash
make install   # uv sync — install dependencies
make test      # pytest + frontend tests
make serve     # start the engine on :8000

# Frontend development
cd web && npm install && npm run dev
```

### CLI usage

```bash
hanflow validate workflow.yaml   # validate the DSL
hanflow compile  workflow.yaml   # compile to a StateGraph (dry run)
hanflow run      workflow.yaml   # execute
hanflow new      my-app          # scaffold a new project
hanflow index    <kb>            # build a knowledge-base index
hanflow doctor                   # environment self-check
```

---

## DSL Example

A hybrid orchestration example (static skeleton + dynamic Coordinator + HITL gate):

```yaml
name: research-report-pipeline
nodes:
  - id: intake              # static: parse the topic
    type: LLM
    config:
      template: parse-topic

  - id: research            # dynamic: coordinate multiple agents
    type: Coordinator
    depends_on: [intake]
    config:
      sub_agents: [researcher, coder]
      plan_hitl: true       # force human confirmation at planning

  - id: factcheck_gate      # human-in-the-loop gate
    type: HITL
    depends_on: [research]
    config:
      actions: [approve, edit, reject]

  - id: report              # produce the final report
    type: Execution
    depends_on: [factcheck_gate]
```

More examples in [`examples/`](examples/) (`static.yaml` / `dynamic.yaml` / `hybrid.yaml`).

---

## Configuration (excerpt from hanflow.yaml)

```yaml
models:
  strong: { provider: openai,    model: gpt-4o,       api_key: "${OPENAI_KEY}" }
  fast:   { provider: glm,       model: glm-4-flash,  api_key: "${GLM_KEY}" }

routing:
  default: strong
  fallback_chain: [strong, fast]   # automatic fallback on primary failure

mcp_servers:
  web_search: { transport: inprocess }

persistence:
  checkpoint: { backend: sqlite,    config: { path: ./data/checkpoints.db } }
  session:    { backend: sqlite,    config: { path: ./data/sessions.db } }
  artifact:   { backend: local_fs,  config: { root: ./workspace/artifacts } }
```

---

## Supported Model Providers

| Provider | Notes |
| --- | --- |
| OpenAI | GPT series |
| Anthropic | Claude series |
| DeepSeek | OpenAI-compatible API |
| GLM (Zhipu) | GLM-4 series |
| Ollama | Local models |
| vLLM | Self-hosted inference, OpenAI-compatible |

Privacy routing directs sensitive workloads to local models (**Ollama / vLLM**) by default.

---

## Self-Evolution

The Hanflow project is itself driven by a **"scheduled trigger + Loop + Harness"** self-evolution mechanism:

- **16-stage LOOP state machine**: a complete closed loop — from intelligence gathering & topic selection, through architecture design, implementation (with TDD and impact analysis), sandbox isolation, test-and-self-heal, and automatic release, to summary and long-term memory;
- **Multiple safety guardrails**: HITL + community review + Harness constraints + mandatory conventions + automated tests — fast *and* correct;
- **Human veto at every critical gate**: contributors can reject or ask the AI to revise any chosen topic or proposed plan.

Two evolution intensities are available, selectable per need:

| Mode | Best for | Characteristics |
| --- | --- | --- |
| **Standard** | Day-to-day iteration, token-efficient | Baseline cost; contributors auto-registered on the Contributors Wall |
| **Full-blooded** | Major features needing expert review | Adds domain-expert Code Review; roughly 7× the cost of Standard |

> Every successful automated contribution registers the contributor's GitHub ID on the [Contributors Wall](https://hanflow.icu/zh/contributors) — a permanent record.

---

## Roadmap

- [x] 1.x: six-layer architecture landed; 13 primitive nodes; closed loop for static / dynamic / hybrid orchestration
- [x] Docker sandbox isolation; LOCAL / DOCKER / K8S / NONE modes
- [ ] More vector stores and storage backends (Postgres / S3 ready; vector-store expansion in progress)
- [ ] Complete K8s sandbox isolation
- [ ] Further low-code capabilities in Web Studio

---

## License & Community Neutrality

- **Apache-2.0, open source forever** — we commit to never closing the source for commercial interest;
- Community-neutral by design, laying the groundwork for sustainable long-term development.

## Contributing

Contributions via Issues and Pull Requests are welcome. Community members can join the self-evolution flow with one-command automated PRs (a GitHub Token is all you need); see the website for details.

## Links

| Platform | URL |
| --- | --- |
| Website | <https://hanflow.icu> |
| Contributors Wall | <https://hanflow.icu/zh/contributors> |
| GitHub | <https://github.com/xpc1024/hanflow> |
| Gitee | <https://gitee.com/easy-es/hanflow> |

If Hanflow helps you, a ⭐ Star is the best encouragement for the project to keep evolving.
