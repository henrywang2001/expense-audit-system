# AI Agent 财务报销审核系统

基于 AI Agent 技术的智能化财务报销审核系统，集成 LLM 大模型、RAG 知识检索、**LangGraph StateGraph 工作流编排**、LangChain 框架，实现报销单据的智能识别、规则校验、风险预警和自动化审批流程。

## 技术栈

| 技术组件 | 版本 | 用途 |
|---------|------|------|
| Python | 3.12+ | 后端开发语言 |
| FastAPI | 0.125.0 | 高性能Web框架 |
| LangChain | 0.3.30 | LLM应用开发框架 |
| **LangGraph** | **0.4.10** | **Agent工作流编排 (StateGraph + Send并行)** |
| LangChain-OpenAI | 0.2.14 | OpenAI兼容LLM集成 |
| DeepSeek V4 Flash | — | LLM大模型服务 |
| 千问 text-embedding-v1 | — | 文本向量嵌入模型 |
| ChromaDB | 1.5.9 | 向量数据库(RAG) |
| SQLAlchemy | 2.0.51 | ORM框架 |
| SQLite (aiosqlite) | 0.21.0 | 关系型数据库(开发环境) |
| Vue 3 | 3.4.0+ | 前端框架 |
| Element Plus | 2.4.0+ | UI组件库 |
| Pinia | 2.1.0+ | 状态管理 |
| Axios | 1.6.0+ | HTTP客户端 |

## 核心功能

1. **智能单据识别**：自动识别发票、收据等报销单据的关键信息
2. **规则引擎校验**：基于企业财务制度自动校验报销合规性
3. **RAG知识检索**：检索历史案例和财务制度，辅助审核决策
4. **多Agent协作**：通过 LangGraph StateGraph 编排5个专业Agent协同工作
5. **风险评估预警**：智能识别异常报销和潜在风险
6. **审批流程自动化**：根据规则自动流转审批流程
7. **数据统计分析**：报销数据的多维度统计和分析

## 项目结构

```
expense-audit-system/
├── backend/                   # 后端服务
│   ├── app/
│   │   ├── main.py            # FastAPI应用入口
│   │   ├── config.py          # 配置管理
│   │   ├── api/               # API路由
│   │   │   └── v1/            # API v1 接口
│   │   ├── core/              # 核心模块（安全/异常）
│   │   ├── models/            # SQLAlchemy 数据模型
│   │   ├── schemas/           # Pydantic 序列化模型
│   │   ├── services/          # 业务服务层
│   │   ├── agents/            # AI Agent 模块 ★
│   │   │   ├── base_agent.py       # Agent 基类（结构化输出）
│   │   │   ├── document_agent.py   # 文档解析 Agent
│   │   │   ├── rule_agent.py       # 规则校验 Agent
│   │   │   ├── risk_agent.py       # 风险评估 Agent (fail-closed)
│   │   │   ├── rag_agent.py        # RAG 检索 Agent
│   │   │   ├── decision_agent.py   # 决策生成 Agent (fail-review)
│   │   │   ├── workflow.py         # 工作流 facade (LangGraph入口)
│   │   │   └── graph/              # LangGraph StateGraph ★
│   │   │       ├── state.py        # AuditState TypedDict
│   │   │       ├── nodes.py        # 5个节点工厂函数
│   │   │       └── builder.py      # StateGraph构建器（条件路由+Send并行）
│   │   ├── rag/               # RAG模块（向量存储/检索/嵌入）
│   │   ├── tools/             # Agent工具（OCR/通知/数据库）
│   │   └── utils/             # 工具函数
│   ├── tests/                 # 测试 ★
│   │   ├── conftest.py             # 共享 fixtures
│   │   ├── test_workflow_routing.py # 条件路由测试
│   │   ├── test_graph.py           # 图编译/结构测试
│   │   └── test_api_regression.py  # API回归测试
│   └── requirements.txt       # 依赖清单
├── frontend/                  # 前端项目
│   ├── src/
│   │   ├── main.ts            # 入口文件
│   │   ├── App.vue            # 根组件
│   │   ├── views/             # 页面
│   │   ├── components/        # 组件
│   │   ├── stores/            # Pinia状态
│   │   ├── router/            # 路由
│   │   ├── api/               # API接口
│   │   └── utils/             # 工具
│   ├── package.json
│   └── vite.config.ts
├── 运行指南.md                 # 运行部署指南
└── README.md                  # 项目说明
```

## AI Agent 工作流架构

### 工作流流程图

```
                        ┌─────────────────────────────────┐
                        │        LangGraph StateGraph       │
                        │  (AsyncSqliteSaver checkpointer)  │
                        └─────────────────────────────────┘
                                         │
                                         ▼
                              ┌──────────────────┐
                              │   document_node  │  文档解析
                              │  (DocumentAgent) │  提取发票信息
                              └────────┬─────────┘
                                       │
                                       ▼
                              ┌──────────────────┐
                              │    rule_node     │  规则校验
                              │   (RuleAgent)    │  合规性检查
                              └────────┬─────────┘
                                       │
                          ┌────────────┴────────────┐
                          │  条件路由 (conditional)   │
                          │  _route_after_rule()     │
                          └────────────┬────────────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    │ failed >= 2      │                  │ failed < 2
                    │ OR errors        │                  │ AND no errors
                    ▼                  │                  ▼
           ┌──────────────┐           │    ┌─────────────────────────┐
           │  decision_node│           │    │   Send fan-out (并行)    │
           │ (DecisionAgent)│          │    │                         │
           └──────────────┘           │    │  ┌──────────┐ ┌───────┐ │
                                      │    │  │risk_node │ │rag_node│ │
                                      │    │  │(RiskAgent)│ │(RAGAgent)│ │
                                      │    │  │ fail-closed│ │        │ │
                                      │    │  └─────┬────┘ └───┬───┘ │
                                      │    │        └────┬────┘      │
                                      │    │             ▼           │
                                      │    └────────→ decision_node ◄┘
                                      │         (fan-in 汇聚)
                                      ▼
                              ┌──────────────┐
                              │ decision_node │  最终决策
                              │(DecisionAgent)│  approve/reject/review
                              │  fail-review  │
                              └──────┬───────┘
                                     │
                                     ▼
                                   END
```

### 四个核心价值

| 价值 | 实现方式 | 效果 |
|------|----------|------|
| **① 条件路由** | `add_conditional_edges` + `_route_after_rule()` | 严重违规(≥2项)时跳过风险评估和知识检索，**节省2次LLM调用** |
| **② Checkpointer** | `AsyncSqliteSaver` + `thread_id` | 5次LLM调用任一失败，从失败节点续跑，不重跑成功的节点 |
| **③ 并行执行** | `Send` fan-out → `risk` ∥ `rag` | risk和rag无依赖关系，并行执行，减少总延迟 |
| **④ State管理** | `TypedDict` + `Annotated` reducer | 状态类型安全，并行节点合并受控 |

### 异常处理策略

| Agent | 异常策略 | 兜底值 | 原因 |
|-------|----------|--------|------|
| **RiskAgent** | **fail-closed** | `critical / 100` | 评估失败不应低估风险 |
| **DecisionAgent** | **fail-review** | `review / confidence=0` | 异常时保守，建议人工复核 |
| **RuleAgent** | **fail-safe** | `failed=0, total_risk=unknown` | 无法确定合规状态，走全流程收集信息 |
| DocumentAgent | fail-continue | `{}` | 文档解析失败不阻塞后续流程 |
| RAGAgent | fail-continue | `[]` | 检索失败不阻塞后续流程 |

### 结构化输出

所有 5 个 Agent 使用 `response_format={"type": "json_object"}` 强制 LLM 返回合法 JSON，替代旧版的正则 `response.find("{")...json.loads` 兜底模式，提升输出可靠性。

## 快速开始

详细的安装和运行步骤请参阅 [运行指南.md](./运行指南.md)

```bash
# 后端
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 前端
cd frontend
npm install
npm run dev
```

## 默认账号

| 角色 | 用户名 | 密码 |
|------|--------|------|
| 管理员 | admin | admin123 |
| 财务 | finance01 | finance123 |
| 员工 | employee01 | employee123 |

## API文档

启动后端后访问: http://localhost:8000/api/docs

## 运行测试

```bash
cd backend
pytest tests/ -v
```

```
======================== 38 passed in 2.32s =========================

test_workflow_routing.py (13 tests)  — 条件路由 + enabled_agents
test_graph.py          (10 tests)  — 图编译 + Send并行 + 节点工厂
test_api_regression.py (13 tests)  — API回归 + fail-closed
```

## 模型配置

| 模型 | 类型 | API地址 | 用途 |
|------|------|---------|------|
| DeepSeek V4 Flash | LLM | api.deepseek.com | 智能审核、文档解析、风险分析 |
| 千问 text-embedding-v1 | Embedding | DashScope | 文本向量化、RAG检索 |
