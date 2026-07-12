"""
审批管理接口 - 审批流程操作
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_admin_or_finance_user
from app.dependencies import get_db
from app.models.user import User
from app.schemas.approval import (
    ApprovalCreate, ApprovalResponse, ApprovalListResponse,
    ApprovalActionRequest,
)
from app.services.approval_service import ApprovalService

router = APIRouter()


@router.get("/", response_model=ApprovalListResponse, summary="获取审批列表")
async def list_approvals(
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
    status: Optional[str] = Query(None, description="审批状态筛选: pending/approved/rejected"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户的审批列表（待审批/已审批）"""
    service = ApprovalService(db)
    result = await service.list_approvals(
        user=current_user,
        page=page,
        page_size=page_size,
        status=status,
    )
    return ApprovalListResponse(**result)


@router.post("/{approval_id}/approve", summary="通过审批")
async def approve_expense(
    approval_id: int,
    request: ApprovalActionRequest,
    current_user: User = Depends(get_admin_or_finance_user),
    db: AsyncSession = Depends(get_db),
):
    """审批通过 - 需要管理员或财务权限"""
    service = ApprovalService(db)
    result = await service.approve(approval_id, current_user, request.comment)
    return {
        "success": True,
        "data": result,
        "message": "审批通过",
    }


@router.post("/{approval_id}/reject", summary="拒绝审批")
async def reject_expense(
    approval_id: int,
    request: ApprovalActionRequest,
    current_user: User = Depends(get_admin_or_finance_user),
    db: AsyncSession = Depends(get_db),
):
    """审批拒绝 - 需要管理员或财务权限"""
    service = ApprovalService(db)
    result = await service.reject(approval_id, current_user, request.comment)
    return {
        "success": True,
        "data": result,
        "message": "审批已拒绝",
    }


@router.get("/{expense_id}/history", summary="获取审批历史")
async def get_approval_history(
    expense_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取指定报销单的审批历史记录"""
    service = ApprovalService(db)
    result = await service.get_approval_history(expense_id, current_user)
    return {
        "success": True,
        "data": result,
        "message": "获取成功",
    }
