"""
AI Agent 工作流接口 - 执行智能审核流程
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_admin_or_finance_user
from app.dependencies import get_db
from app.models.user import User
from app.schemas.agent import AgentExecuteRequest, AgentExecuteResponse
from app.schemas.expense import AIReviewRequest
from app.services.expense_service import ExpenseService

router = APIRouter()


@router.post("/execute", response_model=AgentExecuteResponse, summary="执行AI审核工作流")
async def execute_agent_workflow(
    request: AgentExecuteRequest,
    current_user: User = Depends(get_admin_or_finance_user),
    db: AsyncSession = Depends(get_db),
):
    """
    对指定报销单执行完整的 AI Agent 审核工作流。

    委托给 ExpenseService.ai_review() 统一处理：
    - 状态转移前置校验（仅 DRAFT/PENDING 可审核）
    - 幂等键去重（相同 idempotency_key 直接返回缓存）
    - 乐观锁并发控制（version 字段校验）
    - 事务拆分（LLM 调用不持有 DB 事务）

    工作流包含以下步骤：
    1. 文档解析 - 提取发票和费用信息
    2. 规则校验 - 检查是否符合财务规则
    3. 风险评估 - 多维度风险评分
    4. 知识检索 - 检索相似案例和规则
    5. 决策生成 - 给出审批建议
    """
    service = ExpenseService(db)
    result = await service.ai_review(
        expense_id=request.expense_id,
        user=current_user,
        request=AIReviewRequest(
            expense_id=request.expense_id,
            custom_rules=request.custom_context,
            idempotency_key=request.idempotency_key,
            enabled_agents=request.enabled_agents,
        ),
    )
    return result
