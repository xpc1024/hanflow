# Hanflow

> Harmony AI Nexus - a fusion agent framework with privacy routing, RAG, and observability as first-class citizens.

## Quick Start

```bash
# 1. Clone and configure
git clone <repo>
cd hanflow
cp deploy/docker/hanflow.yaml.example hanflow.yaml
cp deploy/docker/.env.example .env
# Fill in API keys in .env

# 2. Start all services
cd deploy/docker
docker compose up -d

# 3. Access
# Web Studio: http://localhost:3000
# API: http://localhost:8000
# API docs: http://localhost:8000/docs
```

## Architecture

6-layer architecture: L1 Delivery (CLI + Web Studio + SDK) / L2 Orchestration (YAML DSL to LangGraph) / L3 Capabilities (Research + Execution atoms) / L4 Foundation (GraphRuntime / ModelRouter / MCPBus / FilesystemMemory) / L5 Persistence (3 Stores) / L6 Observability (LangSmith trace).

## Web Studio

Three modes:
- **Build Mode**: Drag-and-drop visual workflow editor (React Flow canvas + schema-driven Inspector)
- **Monitor Mode**: Real-time run monitoring with WebSocket streaming + trace replay
- **HITL Approvals**: Human-in-the-loop approval panel with timeout countdown

## Develop

```bash
make install   # uv sync
make test     # pytest + frontend tests
make serve    # start engine at :8000

# Frontend dev
cd web && npm install && npm run dev
```

## Features

- 13 primitive node types
- 6 model routing strategies including privacy routing
- MCP tool bus
- Vector + full-text retrieval
- DSL is the single source of truth (YAML, git-versionable)

## License

MIT/Apache-2.0
