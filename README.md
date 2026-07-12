# AI Agent 财务报销审核系统

基于AI Agent技术的智能化财务报销审核系统，集成LLM大模型、RAG知识检索、LangGraph工作流编排、LangChain框架，实现报销单据的智能识别、规则校验、风险预警和自动化审批流程。

## 技术栈

| 技术组件 | 版本 | 用途 |
|---------|------|------|
| Python | 3.10+ | 后端开发语言 |
| FastAPI | 0.104.0+ | 高性能Web框架 |
| LangChain | 0.1.0+ | LLM应用开发框架 |
| LangGraph | 0.0.20+ | Agent工作流编排 |
| DeepSeek V4 Flash | - | LLM大模型服务 |
| 千问 text-embedding-v1 | - | 文本向量嵌入模型 |
| ChromaDB | 0.4.0+ | 向量数据库(RAG) |
| SQLAlchemy | 2.0+ | ORM框架 |
| SQLite | 3 | 关系型数据库(开发环境) |
| Vue 3 | 3.4.0+ | 前端框架 |
| Element Plus | 2.4.0+ | UI组件库 |
| Pinia | 2.1.0+ | 状态管理 |
| Axios | 1.6.0+ | HTTP客户端 |

## 核心功能

1. **智能单据识别**：自动识别发票、收据等报销单据的关键信息
2. **规则引擎校验**：基于企业财务制度自动校验报销合规性
3. **RAG知识检索**：检索历史案例和财务制度，辅助审核决策
4. **多Agent协作**：通过LangGraph编排多个专业Agent协同工作
5. **风险评估预警**：智能识别异常报销和潜在风险
6. **审批流程自动化**：根据规则自动流转审批流程
7. **数据统计分析**：报销数据的多维度统计和分析

## 项目结构

```
expense-audit-system/
├── backend/                # 后端服务
│   ├── app/
│   │   ├── main.py         # FastAPI应用入口
│   │   ├── config.py       # 配置管理
│   │   ├── api/            # API路由
│   │   ├── core/           # 核心模块
│   │   ├── models/         # 数据模型
│   │   ├── schemas/        # Pydantic模型
│   │   ├── services/       # 业务服务
│   │   ├── agents/         # AI Agent模块
│   │   ├── rag/            # RAG模块
│   │   ├── tools/          # Agent工具
│   │   └── utils/          # 工具函数
│   ├── tests/              # 测试
│   └── requirements.txt    # 依赖清单
├── frontend/               # 前端项目
│   ├── src/
│   │   ├── main.ts         # 入口文件
│   │   ├── App.vue         # 根组件
│   │   ├── views/          # 页面
│   │   ├── components/     # 组件
│   │   ├── stores/         # Pinia状态
│   │   ├── router/         # 路由
│   │   ├── api/            # API接口
│   │   └── utils/          # 工具
│   ├── package.json
│   └── vite.config.ts
├── 运行指南.md              # 运行部署指南
└── README.md               # 项目说明
```

## 快速开始

详细的安装和运行步骤请参阅 [运行指南.md](./运行指南.md)

### 快速预览

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

## 模型配置

- **LLM**: DeepSeek V4 Flash (api.deepseek.com)
- **Embedding**: 千问 text-embedding-v1 (DashScope)
