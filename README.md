# AI Agent 财务报销审核系统

基于 AI Agent 技术的智能化财务报销审核系统，集成 LLM 大模型、**json-logic 确定性规则引擎**、RAG 知识检索、**LangGraph StateGraph 工作流编排**、LangChain 框架，实现报销单据的智能识别、规则校验、风险预警和自动化审批流程。

> **2026-08-08 更新**：
> - **AI 审核展示层收敛** — 新增 `ai_review_presenter` 服务，将 workflow 原始结构映射为统一的 `summary/issues/suggestions` 展示字段，前端卡片和详情页消费同一份数据。
> - **规则管理全面升级** — 规则 CRUD 端点增强，前端 RuleManagement.vue 全面重写。
> - **前端 UI 增强** — ExpenseDetail/ExpenseForm/ExpenseList/ApprovalCenter/Login/Reports 全面优化。
> - **json-logic 确定性规则引擎** — RuleAgent 从 LLM 裁判升级为零次 LLM 调用的确定性求值器，规则可后台 CRUD、结果 100% 可复现、脏数据 fail-loud。
> - **并发安全 + 幂等去重 + 事务拆分改造** — 补齐状态机、乐观锁、缓存三大漏洞。
> - **bcrypt 兼容性修复** — 绕过 passlib 的 bcrypt 5.x 不兼容问题，直接使用 bcrypt 原生 API。
> - 详见各自章节。

## 技术栈

| 技术组件 | 版本 | 用途 |
|---------|------|------|
| Python | 3.12+ | 后端开发语言 |
| FastAPI | 0.125.0 | 高性能Web框架 |
| LangChain | 0.3.30 | LLM应用开发框架 |
| **LangGraph** | **0.4.10** | **Agent工作流编排 (StateGraph + Send并行)** |
| LangChain-OpenAI | 0.2.14 | OpenAI兼容LLM集成 |
| **maykin-json-logic-py** | **0.16.0** | **确定性规则引擎 (零次 LLM 调用)** |
| DeepSeek V4 Flash | — | LLM大模型服务 |
| 千问 text-embedding-v1 | — | 文本向量嵌入模型 |
| ChromaDB | 1.5.9 | 向量数据库(RAG) |
| SQLAlchemy | 2.0.51 | ORM框架 |
| SQLite (aiosqlite) | 0.21.0 | 关系型数据库(开发环境) |
| Vue 3 | 3.4.0+ | 前端框架 |
| Element Plus | 2.4.0+ | UI组件库 |
| Pinia | 2.1.0+ | 状态管理 |
| Vue Router | 4.2.0+ | 前端路由 |
| Axios | 1.6.0+ | HTTP客户端 |
| ECharts | 5.4.0+ | 数据可视化图表 |
| TypeScript | 5.6.0+ | 类型安全 |

## 核心功能

1. **智能单据识别**：自动识别发票、收据等报销单据的关键信息
2. **🆕 确定性规则引擎**：基于 json-logic 的规则引擎，零次 LLM 调用，100% 可复现，脏数据 fail-loud
3. **规则后台管理**：规则 CRUD API，运营可自助配置审核规则，无需改代码
4. **RAG知识检索**：检索历史案例和财务制度，辅助审核决策
5. **多Agent协作**：通过 LangGraph StateGraph 编排5个专业Agent协同工作
6. **风险评估预警**：智能识别异常报销和潜在风险
7. **审批流程自动化**：根据规则自动流转审批流程
8. **数据统计分析**：报销数据的多维度统计和分析
9. **🆕 并发安全保护**：乐观锁 + 状态机校验 + 幂等去重 + 事务拆分

## 项目结构

```
expense-audit-system/
├── backend/                   # 后端服务
│   ├── app/
│   │   ├── main.py            # FastAPI应用入口
│   │   ├── config.py          # 配置管理
│   │   ├── dependencies.py    # 依赖注入（DB会话/引擎工厂）
│   │   ├── api/               # API路由
│   │   │   ├── deps.py            # 路由层依赖（get_current_user / 权限校验）
│   │   │   └── v1/            # API v1 接口
│   │   │       ├── router.py      # ★ 路由注册器
│   │   │       ├── agent.py       # Agent工作流接口 ★
│   │   │       ├── expense.py     # 报销CRUD + AI审核接口
│   │   │       ├── approval.py    # 审批流程接口
│   │   │       ├── auth.py        # 认证接口（含修改密码）
│   │   │       ├── rule.py        # ★ 规则 CRUD API
│   │   │       └── report.py      # 报表接口
│   │   ├── core/              # 核心模块
│   │   │   ├── security.py    # JWT安全
│   │   │   ├── exceptions.py  # 自定义异常（含ConflictException）
│   │   │   ├── idempotency.py # ★ 幂等缓存（并发去重）
│   │   │   ├── rule_engine.py # ★ 确定性规则引擎 (json-logic)
│   │   │   └── rule_builder.py# ★ 规则编译器 ({field,op,val}→json-logic)
│   │   ├── models/            # SQLAlchemy 数据模型
│   │   │   ├── base.py        # 基类 + init_db + 列迁移
│   │   │   ├── user.py        # 用户模型
│   │   │   ├── expense.py     # ★ 报销单（含version乐观锁 + ai_review_status）
│   │   │   ├── rule.py        # 规则/审批/审计日志
│   │   │   └── idempotency.py # ★ 幂等缓存表 AIReviewCache
│   │   ├── schemas/           # Pydantic 序列化模型
│   │   │   ├── expense.py     # ★ AIReviewRequest（含idempotency_key）
│   │   │   ├── agent.py       # ★ AgentExecuteRequest（含idempotency_key）
│   │   │   ├── rule.py        # ★ RuleDef + CRUD schemas (json-logic)
│   │   │   ├── user.py        # 用户/登录/Token
│   │   │   └── approval.py    # 审批相关
│   │   ├── services/          # 业务服务层
│   │   │   ├── expense_service.py # ★ ai_review 重写（4 Phase并发安全）
│   │   │   ├── ai_review_presenter.py # ★ AI审核展示层收敛
│   │   │   ├── approval_service.py
│   │   │   ├── auth_service.py
│   │   │   └── report_service.py
│   │   ├── agents/            # AI Agent 模块
│   │   │   ├── base_agent.py       # Agent 基类（结构化输出）
│   │   │   ├── document_agent.py   # 文档解析 Agent
│   │   │   ├── rule_agent.py       # ★ 规则校验 Agent (确定性引擎+LLM语义)
│   │   │   ├── risk_agent.py       # 风险评估 Agent (fail-closed)
│   │   │   ├── rag_agent.py        # RAG 检索 Agent
│   │   │   ├── decision_agent.py   # 决策生成 Agent (fail-review)
│   │   │   ├── workflow.py         # 工作流 facade (LangGraph入口)
│   │   │   └── graph/              # LangGraph StateGraph
│   │   │       ├── state.py        # AuditState TypedDict
│   │   │       ├── nodes.py        # 5个节点工厂函数
│   │   │       └── builder.py      # StateGraph构建器（条件路由+Send并行）
│   │   ├── rag/               # RAG模块（向量存储/检索/嵌入）
│   │   ├── tools/             # Agent工具（OCR/通知/数据库）
│   │   └── utils/             # 工具函数（校验/辅助）
│   ├── tests/                 # ★ 测试
│   │   ├── __init__.py
│   │   ├── conftest.py             # 共享 fixtures
│   │   ├── test_workflow_routing.py # 条件路由测试 (13 tests)
│   │   ├── test_graph.py           # 图编译/结构测试 (10 tests)
│   │   ├── test_api_regression.py  # ★ API回归测试 (13 tests)
│   │   ├── test_rule_engine.py     # ★ 规则引擎测试 (42 tests)
│   │   ├── test_api/               # API 专项测试
│   │   ├── test_services/          # ★ Service 层测试（含 ai_review_presenter 22 tests）
│   │   └── test_agents/            # Agent 层测试
│   └── requirements.txt       # 依赖清单
├── frontend/                  # 前端项目
│   ├── src/
│   │   ├── main.ts            # 入口文件
│   │   ├── App.vue            # 根组件
│   │   ├── views/             # 页面视图
│   │   │   ├── Login.vue          # 登录页
│   │   │   ├── Dashboard.vue      # 首页仪表盘
│   │   │   ├── ExpenseList.vue    # 报销列表
│   │   │   ├── ExpenseSubmit.vue  # 提交报销
│   │   │   ├── ExpenseDetailPage.vue # 报销详情
│   │   │   ├── ApprovalCenter.vue  # ★ 审批中心
│   │   │   ├── Reports.vue        # ★ 数据报表
│   │   │   ├── RuleManagement.vue # ★ 规则管理 ← 全面重写
│   │   │   └── NotFound.vue       # 404 页面
│   │   ├── components/        # 可复用组件
│   │   │   ├── common/            # Header / Sidebar / Pagination
│   │   │   ├── expense/           # ExpenseList / ExpenseForm / ExpenseDetail
│   │   │   └── approval/          # ApprovalFlow / ApprovalHistory
│   │   ├── stores/            # Pinia 状态管理
│   │   │   ├── user.ts        # 用户认证状态
│   │   │   ├── expense.ts     # 报销数据
│   │   │   └── approval.ts    # 审批数据
│   │   ├── api/               # API 接口封装
│   │   │   ├── auth.ts        # 认证 API
│   │   │   ├── expense.ts     # 报销 API
│   │   │   ├── approval.ts    # 审批 API
│   │   │   ├── report.ts      # 报表 API
│   │   │   └── rule.ts        # 规则管理 API
│   │   ├── types/             # TypeScript 类型定义
│   │   │   ├── index.ts       # 通用类型
│   │   │   ├── expense.ts     # 报销类型
│   │   │   └── rule.ts        # ★ 规则类型
│   │   ├── router/            # 路由配置
│   │   └── utils/             # 工具函数 (request.ts / helpers.ts)
│   ├── package.json
│   ├── vite.config.ts
│   └── .env.example           # 前端环境变量模板
├── 运行指南.md                 # 运行部署指南
└── README.md                  # 项目说明（本文件）
```

*★ 标记为本次改造涉及的文件*

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
| **RuleAgent** | **json-logic 引擎** | 确定性求值，fail-loud |

### 结构化输出

所有 5 个 Agent 使用 `response_format={"type": "json_object"}` 强制 LLM 返回合法 JSON，替代旧版的正则 `response.find("{")...json.loads` 兜底模式，提升输出可靠性。

## 规则引擎 (json-logic) 🆕

### 架构

```
RuleAgent.execute(context)
  │
  ├─ 阶段1: 确定性引擎 (零次 LLM 调用)
  │   ├── build_data(expense) → 纯数据字典 (预计算 invoice_age_days 等)
  │   ├── RuleEngine(rules).evaluate(data) → jsonLogic(rule, data)
  │   └── 返回: [{rule, status: pass|warn|fail|error, action, message}, …]
  │
  └─ 阶段2: LLM 语义补充 (可选, 仅 exec_mode=semantic 的规则)
      └── _evaluate_semantic() → LLM 判断 (招待费备注是否合理等)
```

### 安全设计

| 层级 | 手段 | 说明 |
|------|------|------|
| **数据安全** | `FIELD_WHITELIST` | `build_data` 只暴露白名单标量字段 |
| **规则安全** | `validate_rule_ast` | 静态校验规则 AST，拦截白名单外字段/运算符 |
| **运行安全** | json-logic 天然安全 | 不解释代码，无 `eval`/`exec` 风险 |
| **脏数据** | fail-loud | 未知字段/None比较/脏枚举 → `status: error` |

### 改造成效

| 维度 | 改前 (LLM 当裁判) | 改后 (json-logic 引擎) |
|------|:---:|:---:|
| 规则校验 LLM 调用 | 每次 1 次 | **0 次** |
| 结果可复现 | ❌ | ✅ 100% 确定性 |
| 脏数据 | 被 LLM 吞掉/猜 | ✅ fail-loud 进人工复核 |
| 可测性 | 不可单测 | ✅ **42 项 pytest** |
| 规则管理 | 改代码 | ✅ **后台 CRUD 自配** (5 端点) |

## 并发/幂等/事务安全改造 🆕

### 问题背景

| 问题 | 根因 | 严重程度 |
|------|------|:---:|
| 已审批单点 AI 审核 → 被打回 PENDING | `ai_review` 无状态前置检查 | 🔴 状态机破坏 |
| 并发点两次 → 互相覆盖审核结果 | 无乐观锁/版本号 | 🔴 数据竞争 |
| 重复点击 → 重跑 5 次 LLM + 重复审计日志 | 无幂等键去重 | 🟡 资源浪费 |
| 几十秒 LLM 调用全程持 DB 事务 | SQLite 单写者阻塞所有表 | 🔴 锁库风险 |
| 两个 API 端点行为不一致 | `agent/execute` 绕过 `ExpenseService` | 🟡 代码分裂 |

### 改造架构

```
POST /agent/execute   ──┐
                         ├──→ ExpenseService.ai_review() 统一入口
POST /expense/{id}/ai-review ─┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
   Phase 0: 幂等快路     Phase 1: 短事务       Phase 2: LLM（事务外）
   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
   │ idempotency   │    │ ① 状态门禁    │    │ AgentWorkflow │
   │ _key 查缓存   │    │    DRAFT      │    │ .execute()   │
   │   → hit: 返回  │    │    PENDING   │    │ (30s, 不持锁) │
   │   → miss: 继续  │    │    才放行     │    └──────┬───────┘
   └──────────────┘    │ ② 乐观锁校验   │           │
                        │    WHERE       │    ┌──────▼───────┐
                        │    version=?   │    │ 异常: 清除    │
                        │ ③ 标记 running │    │ running→failed│
                        │    → COMMIT    │    └──────────────┘
                        └──────────────┘
                               │
               ┌───────────────┼───────────────┐
               ▼                               ▼
        Phase 3: 短事务                  Phase 4: 幂等缓存
        ┌──────────────┐                ┌──────────────┐
        │ 乐观锁写回     │                │ INSERT 缓存   │
        │ WHERE version=?│               │ UNIQUE 去重   │
        │ + 审计日志     │                │ (独立事务)     │
        │ → COMMIT      │                └──────────────┘
        └──────────────┘
```

### 三层防护对照

| 层级 | 手段 | 防御场景 | 文件 |
|------|------|----------|------|
| **状态机** | `ALLOWED_STATUSES` 前置校验 + `ai_review_status == "running"` 检查 | 已审批单不被回退 / 同一单不并发跑两次 | `services/expense_service.py` |
| **乐观锁** | `version` 字段 + `WHERE version=?` + `rowcount` 校验 | 并发更新互相覆盖 | `models/expense.py` / `services/expense_service.py` |
| **幂等键** | `idempotency_key` + 缓存表 `AIReviewCache` (5min TTL) | 重复请求不重跑 LLM / 不产生重复日志 | `core/idempotency.py` / `schemas/` |

### 事务拆分示意

```
改前：单个大事务
  ┌──────────────────────────────────────────────────────────┐
  │ BEGIN → SELECT → ... 30s LLM 调用 ... → UPDATE → COMMIT  │
  │         ↑________________ 全程持锁 ___________________↑   │
  └──────────────────────────────────────────────────────────┘

改后：三个短事务
  ┌────────────┐         ┌────────────┐         ┌────────────┐
  │ COMMIT ①   │  30s    │ COMMIT ③   │         │ COMMIT ④   │
  │ 状态门禁    │ ──→    │ 乐观锁写回   │  ──→   │ 幂等缓存    │
  │ 标记running │  LLM   │ 审计日志     │         │ (独立)      │
  └────────────┘  (无锁) └────────────┘         └────────────┘
```

> **关键收益**：SQLite 写入锁持有时长从 **30+ 秒** 降至 **毫秒级**，其他用户的报销操作不再被 AI 审核阻塞。

### 新增模型字段

| Expense 模型 | 类型 | 默认值 | 用途 |
|-------------|------|--------|------|
| `version` | `Integer` | `1` | 乐观锁版本号，每次 AI 审核成功后 +1 |
| `ai_review_status` | `String(20)` | `NULL` | AI 审核运行态：`running` / `done` / `failed` |

| AIReviewCache 模型（新表） | 类型 | 用途 |
|---------------------------|------|------|
| `expense_id` + `idempotency_key` | `UNIQUE` 约束 | 幂等去重，5 分钟 TTL |
| `result_json` | `Text` | 缓存的审核结果 JSON |

### 验证清单

| # | 场景 | 预期结果 | 验证方式 |
|---|------|----------|----------|
| 1 | APPROVED 单调用 AI 审核 | 409 ConflictException | `POST /expense/{id}/ai-review` |
| 2 | 同一单并发发 2 个请求（无幂等键） | 一个成功、一个 409 | 并发请求测试 |
| 3 | 同一单带相同 `idempotency_key` 发 2 次 | 第 2 次返回缓存，审计日志仅 1 条 | 幂等测试 |
| 4 | workflow 抛异常 | `ai_review_status` 回滚为 `failed` | Mock 异常测试 |
| 5 | 正常流程 DRAFT→AI审核→PENDING | 全流程通过 | 端到端测试 |

## 快速开始

详细的安装和运行步骤请参阅 [运行指南.md](./运行指南.md)

```bash
# 后端
cd backend
python -m venv venv && venv\Scripts\activate  # Windows
python3 -m venv venv && source venv/bin/activate  # Linux/macOS
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 前端
cd frontend
npm install        # 或用 pnpm install
npm run dev         # 或用 pnpm dev
```

## 默认账号

| 角色 | 用户名 | 密码 |
|------|--------|------|
| 管理员 | admin | admin123 |
| 财务 | finance01 | finance123 |
| 员工 | employee01 | employee123 |

> 更多账号（财务/经理/员工各2-3个）见 [运行指南.md](./运行指南.md#6-默认账号)

## API文档

启动后端后访问: http://localhost:8000/docs

## 运行测试

```bash
cd backend
pytest tests/ -v
```

```
======================== 84+ passed =========================

test_rule_engine.py     (42 tests) — 规则引擎 + schema + builder + 边界
test_workflow_routing.py (13 tests) — 条件路由 + enabled_agents
test_graph.py          (10 tests) — 图编译 + Send并行 + 节点工厂
test_api_regression.py (13 tests) — API回归 + fail-closed + 两入口统一
test_services/          (N tests) — ★ Service 层（含 ai_review_presenter）
test_conftest.py       (2 tests)  — fixtures
```

## 模型配置

| 模型 | 类型 | API地址 | 用途 |
|------|------|---------|------|
| DeepSeek V4 Flash | LLM | api.deepseek.com | 智能审核、文档解析、风险分析 |
| 千问 text-embedding-v1 | Embedding | DashScope | 文本向量化、RAG检索 |
