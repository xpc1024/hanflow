<div align="center">

# Hanflow

**Harmony AI Nexus —— 基于 LangGraph 的高可控 Agent 编排框架**

静态工作流 · 动态 Agent · 混合编排，统一 DSL，无需切换模式

[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-%E2%89%A5%203.11-blue.svg)](https://www.python.org/)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.2.0-0a0a0a.svg)](https://github.com/langchain-ai/langgraph)
[![Version](https://img.shields.io/badge/version-1.2.3-green.svg)](CHANGELOG.md)
[![CI](https://github.com/xpc1024/hanflow/actions/workflows/ci.yml/badge.svg)](https://github.com/xpc1024/hanflow/actions)

[官网](https://hanflow.icu) · [在线文档](https://hanflow.icu) · [贡献墙](https://hanflow.icu/zh/contributors) · [English](README.md)

</div>

---

## 项目定位

当前 AI 编排领域存在两条路线，各有局限：

- **AI 自主规划（动态 Agent）** 智能化程度高、灵活，但可控性差、易产生幻觉，难以满足生产环境对稳定性的要求；
- **工作流编排（静态 Workflow）** 稳定、可复现，但缺乏应变能力，无法适应开放性任务。

**Hanflow 不要求在两者之间二选一。** 它在**同一套 YAML DSL** 下同时支持纯静态工作流、纯动态 Agent 以及两者递归组合的混合模式，编译为 LangGraph `StateGraph` 执行，全程无需模式切换。

更进一步，Hanflow 将以下能力作为**一等公民**设计，而非后期打补丁：

- 隐私模型路由（敏感数据自动走本地模型）
- RAG 检索（向量 / 全文 / 混合）
- 人机协同审批（HITL）
- 全链路可观测（LangSmith / OpenTelemetry）

---

## 核心优势

### 1. 统一 DSL，三种编排形态

声明式 YAML 是系统唯一的真相来源（single source of truth），可纳入 Git 版本管理、接受代码评审。同一份语法同时表达三种编排形态：

| 形态 | 适用场景 | 特征 |
| --- | --- | --- |
| **纯静态工作流** | SOP 标准化流程、合规审计 | 编译期校验的 DAG，确定性强、可复现 |
| **纯动态 Agent** | 开放性研究、探索性任务 | Coordinator 协调多 Agent，按需规划 |
| **混合编排** | 既有确定性骨架、又有动态决策 | 静态节点内嵌动态子图，递归组合 |

DSL 原生支持 `depends_on`、`condition`、`retry`、按节点的错误处理策略。

### 2. 13 类原语节点

一套完备的编排原语，覆盖控制流、能力调用与状态管理，支持静态与动态递归组合：

| 分组 | 节点 |
| --- | --- |
| 控制流 | `Sequential` · `Parallel` · `Loop` · `Branch` · `HITL` |
| 能力 | `LLM` · `Tool` · `Research` · `Execution` |
| 动态协调 | `Coordinator` |
| 状态 | `Memory` · `Subworkflow` |
| 检索 | `Knowledge` |

- **Research 原子**：带引用溯源的深度研究，结论可追溯。
- **Execution 原子**：以文件系统为记忆的任务执行，支持长周期工作。
- **Subworkflow**：工作流可被引用、嵌套，形成模块化复用。

### 3. 隐私路由 —— 企业级数据合规

`ModelRouter` 提供 **6 种路由策略**，以优先级仲裁：

```
privacy (hard)  >  role  >  task  >  cost  >  static      +  fallback（仅故障时激活）
```

其中 **`PrivacyStrategy` 是一票否决式（score=∞）的硬约束**：

- 基于敏感度分级与 PII（个人身份信息）检测，自动将受监管负载路由到本地模型；
- 支持 `hard`（无可用本地模型则直接抛 `PrivacyViolationError` 拒绝执行）与 `soft`（软降级）两种强制级别；
- 含 PII 时自动执行脱敏（redact）后再决定路由。

这使得 Hanflow 可在金融、医疗、政务等强合规场景中安全落地。

### 4. 多后端 RAG 检索

- 三种检索模式：**向量检索**、**全文检索**、**混合检索**；
- 三种融合算法：**RRF**、**加权融合**、**级联融合**；
- Embedding 与 Reranker 均可插拔。

### 5. MCP 工具总线

统一工具访问层，屏蔽底层差异。支持 **5 种传输协议**：`stdio` · `sse` · `http` · `websocket` · `inprocess`，并内置限流与破坏性操作防护。

### 6. 沙箱隔离执行

为代码执行类节点提供多级隔离，兼顾灵活与安全：

| 模式 | 说明 |
| --- | --- |
| `LOCAL` | 主机子进程执行，零额外依赖 |
| `DOCKER` | 容器级隔离，支持资源限制、工作区挂载、网络策略 |
| `K8S` | 集群级隔离（预留） |
| `NONE` | 不隔离（仅用于可信受控环境） |

### 7. 时间旅行与崩溃恢复

`L5 持久层`采用 **Checkpoint / Session / Artifact 三级存储**：

- 运行状态可检查点化，进程崩溃后可从断点恢复；
- 支持时间旅行（Time Travel）回放，可定位到任意历史状态重放执行。

### 8. 全链路可观测

`L6 观测层`横切于整个运行时，**一行启用**：

- **LangSmith**：开箱即用的 Trace / Eval / 监控；
- **OpenTelemetry**：接入既有可观测体系。

每个节点、每次 LLM 调用、每次工具调用均自动埋点。

---

## 六层架构

```
┌──────────────────────────────────────────────────────────┐
│  L1 交付层 Delivery     CLI · Web Studio · Python SDK      │
│                          REST · WebSocket · Webhook        │
├──────────────────────────────────────────────────────────┤
│  L2 编排层 Orchestration  YAML DSL  ──编译──▶  LangGraph   │
│                           13 原语节点 · 静态/动态递归组合    │
├──────────────────────────────────────────────────────────┤
│  L3 能力层 Capabilities   Research · Execution 原子         │
├──────────────────────────────────────────────────────────┤
│  L4 基础层 Foundation     ModelRouter · MCPBus · RAG        │
├──────────────────────────────────────────────────────────┤
│  L5 持久层 Persistence    Checkpoint · Session · Artifact   │
├──────────────────────────────────────────────────────────┤
│  L6 观测层 Observability  LangSmith · OpenTelemetry         │
└──────────────────────────────────────────────────────────┘
```

每一层职责清晰、相互解耦：DSL 描述意图，编译层将其转化为可执行图，基础层负责模型与工具调度，持久层保证可恢复，观测层提供透明度。

---

## 快速开始

### 环境要求

- Python ≥ 3.11
- （可选）Docker，用于容器化部署与沙箱隔离

### 一键部署（Docker Compose）

```bash
# 1. 克隆并配置
git clone https://github.com/xpc1024/hanflow.git
cd hanflow
cp deploy/docker/hanflow.yaml.example hanflow.yaml
cp deploy/docker/.env.example .env
# 在 .env 中填入 API Key

# 2. 启动全部服务
cd deploy/docker
docker compose up -d

# 3. 访问
#   Web Studio  : http://localhost:3000
#   API         : http://localhost:8000
#   API 文档    : http://localhost:8000/docs
```

### 本地开发

```bash
make install   # uv sync 安装依赖
make test      # pytest + 前端测试
make serve     # 启动引擎 :8000

# 前端开发
cd web && npm install && npm run dev
```

### CLI 用法

```bash
hanflow validate workflow.yaml   # 校验 DSL
hanflow compile  workflow.yaml   # 编译为 StateGraph（试运行）
hanflow run      workflow.yaml   # 执行
hanflow new      my-app          # 脚手架新建项目
hanflow index    <kb>            # 构建知识库索引
hanflow doctor                   # 环境自检
```

---

## DSL 示例

一份混合编排示例（静态骨架 + 动态 Coordinator + HITL 把关）：

```yaml
name: 智能研报管线
nodes:
  - id: intake              # 静态：解析选题
    type: LLM
    config:
      template: 解析选题

  - id: research            # 动态：协调多 Agent
    type: Coordinator
    depends_on: [intake]
    config:
      sub_agents: [researcher, coder]
      plan_hitl: true       # 规划阶段强制人工确认

  - id: factcheck_gate      # 人机协同审批
    type: HITL
    depends_on: [research]
    config:
      actions: [approve, edit, reject]

  - id: report              # 执行成稿
    type: Execution
    depends_on: [factcheck_gate]
```

更多示例见 [`examples/`](examples/)（`static.yaml` / `dynamic.yaml` / `hybrid.yaml`）。

---

## 配置（hanflow.yaml 节选）

```yaml
models:
  strong: { provider: openai,    model: gpt-4o,       api_key: "${OPENAI_KEY}" }
  fast:   { provider: glm,       model: glm-4-flash,  api_key: "${GLM_KEY}" }

routing:
  default: strong
  fallback_chain: [strong, fast]   # 主模型故障自动降级

mcp_servers:
  web_search: { transport: inprocess }

persistence:
  checkpoint: { backend: sqlite,    config: { path: ./data/checkpoints.db } }
  session:    { backend: sqlite,    config: { path: ./data/sessions.db } }
  artifact:   { backend: local_fs,  config: { root: ./workspace/artifacts } }
```

---

## 支持的模型提供商

| 提供商 | 说明 |
| --- | --- |
| OpenAI | GPT 系列 |
| Anthropic | Claude 系列 |
| DeepSeek | OpenAI 兼容接口 |
| GLM（智谱） | GLM-4 系列 |
| Ollama | 本地模型 |
| vLLM | 自托管推理，OpenAI 兼容 |

隐私路由默认将敏感负载导向 **Ollama / vLLM** 等本地模型。

---

## 自进化体系

Hanflow 项目本身由一套 **"定时触发 + Loop + Harness"** 的自进化机制驱动演进：

- **16 阶段 LOOP 状态机**：从情报搜集与选题、架构设计、实现（含 TDD 与影响面评估）、沙箱隔离、测试自愈、自动发布，到总结汇报、长期记忆，闭环完整；
- **多重安全护栏**：HITL 人机协同 + 社区审核 + Harness 约束 + 强制规约 + 自动化测试，确保"跑得快且跑得正"；
- **每个关键关卡都保留人工否决权**：开发者可拒绝或要求 AI 调整选题与方案。

提供两种进化强度，按需选择：

| 模式 | 适用场景 | 特点 |
| --- | --- | --- |
| **常规版** | 日常迭代、节省 Token | 基准成本，自动贡献者登记至贡献墙 |
| **满血版** | 重大特性、需专家把关 | 引入领域专家团 Code Review，成本约为常规版 7× |

> 每一次成功的自动贡献，贡献者 GitHub ID 会被系统自动登记至 [官网贡献墙](https://hanflow.icu/zh/contributors)，永久留痕。

---

## 路线图

- [x] 1.x：六层架构落地，13 原语节点，静态 / 动态 / 混合编排闭环
- [x] Docker 沙箱隔离，LOCAL / DOCKER / K8S / NONE 四模式
- [ ] 更多向量库与存储后端（Postgres / S3 已就绪，向量库扩展中）
- [ ] K8s 沙箱隔离完整实现
- [ ] Web Studio 低代码能力进一步增强

---

## 开源协议与社区中立

- **Apache-2.0 协议，永久开源**，承诺不会因商业利益闭源；
- 保持社区中立，为长期可持续发展奠定基础。

## 贡献

欢迎通过 Issue 与 Pull Request 参与共建。社区成员可使用一键自动 PR 的 Skills（需 GitHub Token）参与自进化流程，详细信息见官网。

## 链接

| 平台 | 地址 |
| --- | --- |
| 官网 | <https://hanflow.icu> |
| 贡献墙 | <https://hanflow.icu/zh/contributors> |
| GitHub | <https://github.com/xpc1024/hanflow> |
| Gitee | <https://gitee.com/easy-es/hanflow> |

如果 Hanflow 对你有帮助，欢迎点一个 ⭐ Star，这是项目持续演进的动力。
