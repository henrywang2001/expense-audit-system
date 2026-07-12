"""
审批相关 Pydantic Schemas
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class ApprovalCreate(BaseModel):
    """创建审批请求"""
    expense_id: int = Field(..., description="报销单ID")
    flow_id: Optional[int] = Field(None, description="审批流程ID")
    level: int = Field(default=1, ge=1, description="审批层级")


class ApprovalResponse(BaseModel):
    """审批记录响应（含关联报销单字段）"""
    id: int
    expense_id: int
    approver_id: int
    flow_id: Optional[int] = None
    status: str
    level: int
    comment: Optional[str] = None
    approver_name: Optional[str] = None
    expense_no: Optional[str] = None
    title: Optional[str] = None
    expense_type: Optional[str] = None
    total_amount: Optional[float] = None
    expense_status: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ApprovalActionRequest(BaseModel):
    """审批操作请求（通过/拒绝）"""
    comment: Optional[str] = Field(None, max_length=500, description="审批意见")


class ApprovalListResponse(BaseModel):
    """审批列表响应"""
    success: bool = True
    data: List[ApprovalResponse] = []
    total: int = 0
    page: int = 1
    page_size: int = 20
