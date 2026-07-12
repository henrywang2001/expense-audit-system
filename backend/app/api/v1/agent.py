"""
AI Agent 工作流接口 - 执行智能审核流程
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_admin_or_finance_user
from app.dependencies import get_db
from app.models.user import User
from app.schemas.agent import AgentExecuteRequest, AgentExecuteResponse
from app.agents.workflow import AgentWorkflow

router = APIRouter()


@router.post("/execute", response_model=AgentExecuteResponse, summary="执行AI审核工作流")
async def execute_agent_workflow(
    request: AgentExecuteRequest,
    current_user: User = Depends(get_admin_or_finance_user),
    db: AsyncSession = Depends(get_db),
):
    """
    对指定报销单执行完整的AI Agent审核工作流

    工作流包含以下步骤：
    1. 文档解析 - 提取发票和费用信息
    2. 规则校验 - 检查是否符合财务规则
    3. 风险评估 - 多维度风险评分
    4. 知识检索 - 检索相似案例和规则
    5. 决策生成 - 给出审批建议
    """
    workflow = AgentWorkflow(db, current_user)
    result = await workflow.execute(
        expense_id=request.expense_id,
        enabled_agents=request.enabled_agents,
        custom_context=request.custom_context,
    )
    return result
