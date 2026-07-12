"""
AI Agent 工作流
使用 LangGraph 编排多 Agent 协作完成报销审核
流程: 文档解析 -> 规则校验 -> (条件判断) -> 风险评估 -> 知识检索 -> 决策生成
"""
import logging
from typing import Optional, List, Dict, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models.user import User
from app.models.expense import Expense, ExpenseStatus
from app.agents.document_agent import DocumentAgent
from app.agents.rule_agent import RuleAgent
from app.agents.risk_agent import RiskAgent
from app.agents.rag_agent import RAGAgent
from app.agents.decision_agent import DecisionAgent
from app.schemas.agent import AgentExecuteResponse, AgentResult

logger = logging.getLogger(__name__)


class AgentWorkflow:
    """
    AI Agent 审核工作流

    编排多个专业 Agent 协作完成报销审核:
    1. 文档解析 - 提取发票信息
    2. 规则校验 - 检查合规性
    3. 风险评估 - 多维度评分
    4. 知识检索 - 相似案例参考
    5. 决策生成 - 最终审批建议
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
        执行完整的 AI Agent 审核工作流

        Args:
            expense_id: 报销单ID
            enabled_agents: 启用的Agent列表，None表示启用全部
            custom_context: 自定义上下文

        Returns:
            工作流执行结果字典
        """
        logger.info(f"========== 开始 AI Agent 审核工作流 (报销单ID: {expense_id}) ==========")

        # 加载报销单和用户信息
        expense = await self._load_expense(expense_id)
        if not expense:
            return AgentExecuteResponse(
                success=False,
                workflow_status="failed",
                expense_id=expense_id,
                final_decision="error",
                final_reason="报销单不存在",
                agent_results=[],
                message="报销单不存在",
            ).model_dump()

        user_info = await self._load_user_info(expense.user_id)

        # 准备上下文
        context = {
            "expense": expense,
            "user_info": user_info,
            "document_texts": [],  # 后续可加载OCR文本
        }
        if custom_context:
            context["custom"] = custom_context

        agent_results: List[AgentResult] = []

        # 判断哪些 Agent 需要执行
        all_agents = enabled_agents is None
        should_run = lambda name: all_agents or name in (enabled_agents or [])

        # ===== 第1步: 文档解析 =====
        if should_run("document"):
            doc_agent = DocumentAgent()
            doc_result = await doc_agent.execute(context)
            agent_results.append(self._to_agent_result(doc_result))
            context["document_result"] = doc_result.get("result", {})
            logger.info(f"[Workflow] 步骤1 - 文档解析: {doc_result.get('status')}")
        else:
            context["document_result"] = {}

        # ===== 第2步: 规则校验 =====
        if should_run("rule"):
            rule_agent = RuleAgent(self.db)
            rule_result = await rule_agent.execute(context)
            agent_results.append(self._to_agent_result(rule_result))
            context["rule_result"] = rule_result.get("result", {})

            # 条件判断：如果规则校验发现严重违规，可以跳过后面的步骤
            rule_summary = rule_result.get("result", {}).get("summary", {})
            failed_count = rule_summary.get("failed", 0)
            logger.info(f"[Workflow] 步骤2 - 规则校验: {rule_result.get('status')}, 违规数: {failed_count}")
        else:
            context["rule_result"] = {}

        # ===== 第3步: 风险评估 =====
        if should_run("risk"):
            # 加载历史记录
            context["history"] = await self._load_user_history(expense.user_id)

            risk_agent = RiskAgent()
            risk_result = await risk_agent.execute(context)
            agent_results.append(self._to_agent_result(risk_result))
            context["risk_result"] = risk_result.get("result", {})
            logger.info(f"[Workflow] 步骤3 - 风险评估: {risk_result.get('status')}")
        else:
            context["risk_result"] = {}

        # ===== 第4步: 知识检索 =====
        if should_run("rag"):
            rag_agent = RAGAgent()
            rag_result = await rag_agent.execute(context)
            agent_results.append(self._to_agent_result(rag_result))
            context["rag_result"] = rag_result.get("result", {})
            logger.info(f"[Workflow] 步骤4 - 知识检索: {rag_result.get('status')}")
        else:
            context["rag_result"] = {}

        # ===== 第5步: 决策生成 =====
        if should_run("decision"):
            decision_agent = DecisionAgent()
            decision_result = await decision_agent.execute(context)
            agent_results.append(self._to_agent_result(decision_result))
            context["decision_result"] = decision_result.get("result", {})
            logger.info(f"[Workflow] 步骤5 - 决策生成: {decision_result.get('status')}")
        else:
            context["decision_result"] = {}

        # 提取最终决策
        final_decision_result = context.get("decision_result", {})
        final_decision_reason = final_decision_result.get(
            "reason",
            final_decision_result.get("message", "工作流已完成"),
        )

        # 提取风险信息
        risk_result = context.get("risk_result", {})
        risk_level = risk_result.get("risk_level", "low")
        risk_score = risk_result.get("risk_score", 0)

        logger.info(f"========== AI Agent 审核工作流完成 ==========")
        logger.info(f"最终决策: {final_decision_result.get('decision', 'unknown')}")

        return {
            "success": True,
            "workflow_status": "completed",
            "expense_id": expense_id,
            "final_decision": final_decision_result.get("decision", "review"),
            "final_reason": final_decision_reason,
            "risk_level": risk_level,
            "risk_score": risk_score,
            "agent_results": [r.model_dump() if isinstance(r, AgentResult) else r for r in agent_results],
            "message": "Agent工作流执行完成",
        }

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
        """将字典转换为 AgentResult 对象"""
        return AgentResult(
            agent_name=result.get("agent_name", "unknown"),
            status=result.get("status", "unknown"),
            result=result.get("result", {}),
            message=result.get("message", ""),
            duration_ms=result.get("duration_ms", 0),
        )
