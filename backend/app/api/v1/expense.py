"""
报销管理接口 - 报销单的增删改查和工作流
"""
import os
import uuid
from typing import Optional, List

from fastapi import APIRouter, Depends, UploadFile, File, Form, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_admin_or_finance_user
from app.dependencies import get_db
from app.models.user import User
from app.schemas.expense import (
    ExpenseCreate, ExpenseUpdate, ExpenseResponse,
    ExpenseListResponse, ExpenseDetailResponse,
    AIReviewRequest, AIReviewResponse,
    StatisticsResponse, MessageResponse,
)
from app.services.expense_service import ExpenseService

router = APIRouter()


@router.get("/", response_model=ExpenseListResponse, summary="获取报销单列表")
async def list_expenses(
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
    status: Optional[str] = Query(None, description="状态筛选"),
    expense_type: Optional[str] = Query(None, description="报销类型筛选"),
    keyword: Optional[str] = Query(None, description="关键词搜索"),
    sort_by: str = Query(default="created_at", description="排序字段"),
    sort_order: str = Query(default="desc", description="排序方向: asc/desc"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取报销单列表，支持分页、筛选和搜索"""
    service = ExpenseService(db)
    result = await service.list_expenses(
        user=current_user,
        page=page,
        page_size=page_size,
        status=status,
        expense_type=expense_type,
        keyword=keyword,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return ExpenseListResponse(**result)


@router.post("/", response_model=ExpenseDetailResponse, summary="创建报销单")
async def create_expense(
    expense_data: ExpenseCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建新的报销单"""
    service = ExpenseService(db)
    result = await service.create_expense(current_user.id, expense_data)
    return ExpenseDetailResponse(
        success=True,
        data=result,
        message="报销单创建成功",
    )


@router.get("/{expense_id}", response_model=ExpenseDetailResponse, summary="获取报销单详情")
async def get_expense(
    expense_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """根据ID获取报销单详细信息"""
    service = ExpenseService(db)
    result = await service.get_expense(expense_id, current_user)
    return ExpenseDetailResponse(
        success=True,
        data=result,
        message="获取成功",
    )


@router.put("/{expense_id}", response_model=ExpenseDetailResponse, summary="更新报销单")
async def update_expense(
    expense_id: int,
    expense_data: ExpenseUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新报销单信息（仅草稿状态可修改）"""
    service = ExpenseService(db)
    result = await service.update_expense(expense_id, current_user, expense_data)
    return ExpenseDetailResponse(
        success=True,
        data=result,
        message="报销单更新成功",
    )


@router.delete("/{expense_id}", response_model=MessageResponse, summary="删除报销单")
async def delete_expense(
    expense_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除报销单（仅草稿状态可删除）"""
    service = ExpenseService(db)
    await service.delete_expense(expense_id, current_user)
    return MessageResponse(
        success=True,
        message="报销单删除成功",
    )


@router.post("/{expense_id}/submit", response_model=MessageResponse, summary="提交报销单")
async def submit_expense(
    expense_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """提交报销单进行审批（草稿 -> 已提交）"""
    service = ExpenseService(db)
    await service.submit_expense(expense_id, current_user)
    return MessageResponse(
        success=True,
        message="报销单提交成功",
    )


@router.post("/{expense_id}/withdraw", response_model=MessageResponse, summary="撤回报销单")
async def withdraw_expense(
    expense_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """撤回已提交的报销单（已提交/待审核 -> 草稿）"""
    service = ExpenseService(db)
    await service.withdraw_expense(expense_id, current_user)
    return MessageResponse(
        success=True,
        message="报销单已撤回",
    )


@router.post("/{expense_id}/ai-review", response_model=AIReviewResponse, summary="AI审核")
async def ai_review_expense(
    expense_id: int,
    request: AIReviewRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """对指定报销单执行AI智能审核"""
    service = ExpenseService(db)
    result = await service.ai_review(expense_id, current_user, request)
    return AIReviewResponse(
        success=True,
        data=result,
        message="AI审核完成",
    )


@router.post("/upload-invoice", summary="上传发票文件")
async def upload_invoice(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """上传发票图片或PDF文件"""
    service = ExpenseService(None)
    result = await service.upload_invoice(file, current_user)
    return {
        "success": True,
        "data": result,
        "message": "文件上传成功",
    }


@router.get("/statistics/overview", response_model=StatisticsResponse, summary="报销统计")
async def get_statistics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户的报销统计数据"""
    service = ExpenseService(db)
    result = await service.get_user_statistics(current_user)
    return StatisticsResponse(
        success=True,
        data=result,
        message="获取成功",
    )
