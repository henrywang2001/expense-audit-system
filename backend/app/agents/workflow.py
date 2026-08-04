"""
AI Agent 工作流
编排多 Agent 协作完成报销审核

流程: 文档解析 → 规则校验 → (条件路由)
  - 严重违规(≥2项)或前置异常: 跳过风险评估和知识检索，直达决策
  - 正常: 风险评估 ∥ 知识检索 (LangGraph Send fan-out 并行) → 决策生成

架构:
  graph/state   — TypedDict AuditState + Annotated reducer
  graph/nodes   — 5 个 StateGraph 节点工厂函数
  graph/builder — StateGraph 构建器: 条件路由 + Send 并行 + AsyncSqliteSaver
  AgentWorkflow — facade: 预加载数据 → graph.ainvoke() → 装配返回
"""
import logging
from typing import Optional, List, Dict, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models.user import User
from app.models.expense import Expense, ExpenseStatus
from app.agents.graph.builder import build_audit_graph
from app.schemas.agent import AgentExecuteResponse, AgentResult

logger = logging.getLogger(__name__)


class AgentWorkflow:
    """
    AI Agent 审核工作流（LangGraph StateGraph 版本）

    使用 LangGraph StateGraph 编排 5 个 Agent:
    1. 文档解析 - 提取发票信息
    2. 规则校验 - 检查合规性
    3. (条件路由) 风险评估 - 多维度评分    }
    4. (条件路由) 知识检索 - 相似案例参考  } Send fan-out 并行
    5. 决策生成 - 最终审批建议

    核心设计:
    - 条件路由: rule 节点 failed_count>=2 → 跳过 risk+rag，直达 decision
    - Send 并行: risk 和 rag 通过 Send fan-out 在独立 superstep 中并行执行
    - AsyncSqliteSaver: 支持失败重试时从上一个节点续跑
    """

    def __init__(self, db: AsyncSession, user: User = None):
        self.db = db
        self.user = user

    async def execute(
        self,
        expense_id: int,
        enabled_agents: Optional[List[str]] = None,
        custom_context: Optional[dict] = None,
    ) -> dict:
        """
        执行 LangGraph StateGraph 审核工作流

        Args:
            expense_id: 报销单ID
            enabled_agents: 启用的Agent列表，None 表示启用全部
            custom_context: 自定义上下文

        Returns:
            工作流执行结果字典（与旧版结构完全兼容）
        """
        logger.info(
            f"========== AI Agent 审核 (LangGraph) expense={expense_id} =========="
        )

        # —— 1. 加载数据 ——
        expense = await self._load_expense(expense_id)
        if not expense:
            return self._error_response(expense_id, "报销单不存在")

        user_info = await self._load_user_info(expense.user_id)
        history = await self._load_user_history(expense.user_id)

        # —— 2. 构建初始状态（与 AuditState TypedDict 对齐） ——
        initial_state = {
            "expense_id": expense_id,
            "expense": expense,
            "user_info": user_info,
            "custom_context": custom_context,
            "history": history,
            "document_texts": [],
            "document_result": {},
            "rule_result": {},
            "risk_result": {},
            "rag_result": {},
            "decision_result": {},
            "agent_results": [],
            "failed_count": 0,
            "errors": [],
            "enabled_agents": enabled_agents,
        }

        # —— 3. 构建 StateGraph 并执行 ——
        try:
            from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

            async with AsyncSqliteSaver.from_conn_string(
                "data/audit_checkpoints.db"
            ) as saver:
                app = build_audit_graph(
                    db=self.db,
                    user=self.user,
                    enabled_agents=enabled_agents,
                    checkpointer=saver,
                )
                final_state = await app.ainvoke(
                    initial_state,
                    config={
                        "configurable": {
                            "thread_id": f"audit-{expense_id}"
                        }
                    },
                )
        except Exception as e:
            logger.error(f"[Workflow] StateGraph 执行异常: {e}", exc_info=True)
            return self._error_response(
                expense_id, f"工作流引擎异常: {str(e)}"
            )

        # —— 4. 装配返回 ——
        result = self._assemble_response(final_state)
        logger.info(
            f"========== AI Agent 审核完成: "
            f"decision={result['final_decision']} =========="
        )
        return result

    # ===== 辅助方法 =====

    def _error_response(self, expense_id: int, message: str) -> dict:
        """构造错误响应（兼容旧版返回结构）"""
        return AgentExecuteResponse(
            success=False,
            workflow_status="failed",
            expense_id=expense_id,
            final_decision="error",
            final_reason=message,
            agent_results=[],
            message=message,
        ).model_dump()

    def _assemble_response(self, state: dict) -> dict:
        """从 StateGraph 结果 dict 装配与旧版完全一致的返回"""
        dec = state.get("decision_result", {})
        risk = state.get("risk_result", {})

        return {
            "success": True,
            "workflow_status": "completed",
            "expense_id": state.get("expense_id"),
            "final_decision": dec.get("decision", "review"),
            "final_reason": dec.get(
                "reason",
                dec.get("message", "工作流已完成"),
            ),
            "risk_level": risk.get("risk_level", "low"),
            "risk_score": risk.get("risk_score", 0),
            "agent_results": state.get("agent_results", []),
            "message": "Agent工作流执行完成",
        }

    # ===== 数据加载方法（保持不变） =====

    async def _load_expense(self, expense_id: int) -> Optional[Expense]:
        """加载报销单"""
        try:
            result = await self.db.execute(
                select(Expense)
                .options(
                    selectinload(Expense.items),
                    selectinload(Expense.user),
                )
                .where(Expense.id == expense_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"加载报销单失败: {e}")
            return None

    async def _load_user_info(self, user_id: int) -> dict:
        """加载用户信息"""
        try:
            result = await self.db.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            if user:
                return {
                    "id": user.id,
                    "username": user.username,
                    "full_name": user.full_name,
                    "department": user.department,
                    "position": user.position,
                    "role": user.role.value if hasattr(user.role, 'value') else str(user.role),
                }
        except Exception as e:
            logger.warning(f"加载用户信息失败: {e}")
        return {}

    async def _load_user_history(self, user_id: int, limit: int = 10) -> List[dict]:
        """加载用户历史报销记录"""
        try:
            result = await self.db.execute(
                select(Expense)
                .where(Expense.user_id == user_id)
                .order_by(Expense.created_at.desc())
                .limit(limit)
            )
            expenses = result.scalars().all()
            return [
                {
                    "id": e.id,
                    "title": e.title,
                    "expense_type": e.expense_type.value if hasattr(e.expense_type, 'value') else str(e.expense_type),
                    "total_amount": e.total_amount,
                    "status": e.status.value if hasattr(e.status, 'value') else str(e.status),
                    "risk_level": e.risk_level.value if e.risk_level and hasattr(e.risk_level, 'value') else e.risk_level,
                    "submitted_at": str(e.submitted_at) if e.submitted_at else None,
                }
                for e in expenses
            ]
        except Exception as e:
            logger.warning(f"加载历史记录失败: {e}")
            return []

    def _to_agent_result(self, result: dict) -> AgentResult:
        """将字典转换为 AgentResult 对象（保留兼容）"""
        return AgentResult(
            agent_name=result.get("agent_name", "unknown"),
            status=result.get("status", "unknown"),
            result=result.get("result", {}),
            message=result.get("message", ""),
            duration_ms=result.get("duration_ms", 0),
        )
