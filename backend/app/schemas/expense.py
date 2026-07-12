"""
报销单相关 Pydantic Schemas
"""
from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, Field
from decimal import Decimal


# ========== 费用明细 ==========

class ExpenseItemCreate(BaseModel):
    """费用明细创建请求"""
    category_id: Optional[int] = Field(None, description="费用类别ID")
    description: str = Field(..., min_length=1, max_length=500, description="费用说明")
    amount: float = Field(..., gt=0, description="金额")
    expense_date: Optional[date] = Field(None, description="费用发生日期")
    invoice_no: Optional[str] = Field(None, max_length=100, description="发票号码")
    invoice_url: Optional[str] = Field(None, max_length=500, description="发票URL")


class ExpenseItemResponse(BaseModel):
    """费用明细响应"""
    id: int
    expense_id: int
    category_id: Optional[int] = None
    description: str
    amount: float
    expense_date: Optional[date] = None
    invoice_no: Optional[str] = None
    invoice_url: Optional[str] = None
    invoice_verified: bool = False
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ========== 报销单 ==========

class ExpenseCreate(BaseModel):
    """报销单创建请求"""
    title: str = Field(..., min_length=1, max_length=200, description="报销单标题")
    expense_type: str = Field(..., description="报销类型: travel/office/entertainment/transport/meal/training/equipment/other")
    description: Optional[str] = Field(None, max_length=1000, description="报销说明")
    currency: str = Field(default="CNY", max_length=10, description="币种")
    items: List[ExpenseItemCreate] = Field(..., min_length=1, description="费用明细列表")


class ExpenseUpdate(BaseModel):
    """报销单更新请求"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    expense_type: Optional[str] = None
    description: Optional[str] = Field(None, max_length=1000)
    currency: Optional[str] = Field(None, max_length=10)
    remark: Optional[str] = Field(None, max_length=500)
    items: Optional[List[ExpenseItemCreate]] = None


class ExpenseResponse(BaseModel):
    """报销单响应"""
    id: int
    user_id: int
    expense_no: str
    title: str
    expense_type: str
    total_amount: float = 0.0
    currency: str = "CNY"
    status: str = "draft"
    description: Optional[str] = None
    remark: Optional[str] = None
    submitted_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    risk_level: Optional[str] = None
    risk_score: Optional[float] = None
    ai_review_result: Optional[dict] = None
    items: List[ExpenseItemResponse] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ExpenseListResponse(BaseModel):
    """报销单列表响应（带分页）"""
    success: bool = True
    data: List[ExpenseResponse] = []
    total: int = 0
    page: int = 1
    page_size: int = 20
    total_pages: int = 0


class ExpenseDetailResponse(BaseModel):
    """报销单详情响应"""
    success: bool = True
    data: ExpenseResponse
    message: str = "获取成功"


# ========== AI 审核 ==========

class AIReviewRequest(BaseModel):
    """AI审核请求"""
    expense_id: int = Field(..., description="报销单ID")
    include_history: bool = Field(default=False, description="是否包含历史记录分析")
    custom_rules: Optional[dict] = Field(None, description="自定义审核规则")


class AIReviewResponse(BaseModel):
    """AI审核响应"""
    success: bool = True
    data: dict = Field(default_factory=dict, description="AI审核结果详情")
    message: str = "AI审核完成"


# ========== 统计 ==========

class StatisticsResponse(BaseModel):
    """报销统计响应"""
    success: bool = True
    data: dict = Field(default_factory=dict)
    message: str = "获取成功"


# ========== 通用 ==========

class MessageResponse(BaseModel):
    """通用消息响应"""
    success: bool = True
    data: Optional[dict] = None
    message: str = "操作成功"
