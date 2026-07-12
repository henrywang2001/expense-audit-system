"""
Agent 工作流相关 Pydantic Schemas
"""
from typing import Optional, List
from pydantic import BaseModel, Field


class AgentResult(BaseModel):
    """单个 Agent 执行结果"""
    agent_name: str = Field(..., description="Agent名称")
    status: str = Field(default="success", description="执行状态: success/failed/skipped")
    result: dict = Field(default_factory=dict, description="执行结果")
    message: Optional[str] = Field(None, description="执行消息")
    duration_ms: Optional[float] = Field(None, description="执行耗时（毫秒）")


class AgentExecuteRequest(BaseModel):
    """Agent 工作流执行请求"""
    expense_id: int = Field(..., description="报销单ID")
    enabled_agents: Optional[List[str]] = Field(
        None,
        description="指定启用的Agent列表，不传则启用全部"
    )
    custom_context: Optional[dict] = Field(
        None,
        description="自定义上下文信息"
    )


class AgentExecuteResponse(BaseModel):
    """Agent 工作流执行响应"""
    success: bool = True
    workflow_status: str = Field(default="completed", description="工作流状态: completed/failed/partial")
    expense_id: int = Field(..., description="报销单ID")
    final_decision: Optional[str] = Field(None, description="最终决策: approve/reject/review")
    final_reason: Optional[str] = Field(None, description="决策理由")
    risk_level: Optional[str] = Field(None, description="风险等级")
    risk_score: Optional[float] = Field(None, description="风险评分")
    agent_results: List[AgentResult] = Field(default_factory=list, description="各Agent执行结果")
    message: str = "Agent工作流执行完成"
