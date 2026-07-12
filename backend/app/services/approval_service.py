"""
审批服务 - 审批流程操作
"""
import math
from datetime import datetime
from typing import Optional, List

from sqlalchemy import select, func, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import (
    NotFoundException, ForbiddenException, ExpenseStatusException, BadRequestException
)
from app.models.user import User
from app.models.expense import Expense, ExpenseStatus
from app.models.rule import Approval, ApprovalStatus, AuditLog


class ApprovalService:
    """审批业务服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_approvals(
        self,
        user: User,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
    ) -> dict:
        """获取审批列表"""
        query = select(Approval).options(
            selectinload(Approval.expense),
            selectinload(Approval.approver),
        )

        # 如果是普通用户，只看自己的审批记录
        if user.role.value not in ("admin", "finance") and not user.is_superuser:
            query = query.where(Approval.approver_id == user.id)

        # 状态筛选
        if status:
            query = query.where(Approval.status == ApprovalStatus(status))

        # 获取总数
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # 排序分页
        query = query.order_by(desc(Approval.created_at))
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        approvals = result.scalars().unique().all()

        return {
            "success": True,
            "data": [self._approval_to_response(a) for a in approvals],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def approve(
        self, approval_id: int, user: User, comment: Optional[str] = None
    ) -> dict:
        """审批通过"""
        approval = await self._get_approval(approval_id)
        if not approval:
            raise NotFoundException(message="审批记录不存在")

        if approval.status != ApprovalStatus.PENDING:
            raise BadRequestException(message="该审批已处理过")

        # 检查审批权限
        if approval.approver_id != user.id:
            raise ForbiddenException(message="您不是此审批的指定审批人")

        # 更新审批状态
        approval.status = ApprovalStatus.APPROVED
        approval.comment = comment

        # 更新报销单状态
        expense = await self._get_expense(approval.expense_id)
        if expense:
            expense.status = ExpenseStatus.APPROVED
            expense.approved_at = datetime.utcnow()

        # 记录审核日志
        log = AuditLog(
            expense_id=approval.expense_id,
            action="approve",
            actor=user.username,
            details={"comment": comment, "level": approval.level},
        )
        self.db.add(log)

        await self.db.flush()
        await self.db.refresh(approval)
        return self._approval_to_response(approval)

    async def reject(
        self, approval_id: int, user: User, comment: Optional[str] = None
    ) -> dict:
        """审批拒绝"""
        approval = await self._get_approval(approval_id)
        if not approval:
            raise NotFoundException(message="审批记录不存在")

        if approval.status != ApprovalStatus.PENDING:
            raise BadRequestException(message="该审批已处理过")

        if approval.approver_id != user.id:
            raise ForbiddenException(message="您不是此审批的指定审批人")

        # 更新审批状态
        approval.status = ApprovalStatus.REJECTED
        approval.comment = comment

        # 更新报销单状态
        expense = await self._get_expense(approval.expense_id)
        if expense:
            expense.status = ExpenseStatus.REJECTED

        # 记录审计日志
        log = AuditLog(
            expense_id=approval.expense_id,
            action="reject",
            actor=user.username,
            details={"comment": comment, "level": approval.level},
        )
        self.db.add(log)

        await self.db.flush()
        await self.db.refresh(approval)
        return self._approval_to_response(approval)

    async def get_approval_history(self, expense_id: int, user: User) -> List[dict]:
        """获取报销单的审批历史"""
        # 检查权限
        expense = await self._get_expense(expense_id)
        if not expense:
            raise NotFoundException(message="报销单不存在")

        if expense.user_id != user.id and user.role.value not in ("admin", "finance") and not user.is_superuser:
            raise ForbiddenException(message="无权查看审批历史")

        # 获取审批记录
        result = await self.db.execute(
            select(Approval)
            .options(selectinload(Approval.approver))
            .where(Approval.expense_id == expense_id)
            .order_by(asc(Approval.level))
        )
        approvals = result.scalars().unique().all()

        return [self._approval_to_response(a) for a in approvals]

    async def _get_approval(self, approval_id: int) -> Optional[Approval]:
        """获取审批记录"""
        result = await self.db.execute(
            select(Approval)
            .options(selectinload(Approval.expense), selectinload(Approval.approver))
            .where(Approval.id == approval_id)
        )
        return result.scalar_one_or_none()

    async def _get_expense(self, expense_id: int) -> Optional[Expense]:
        """获取报销单"""
        result = await self.db.execute(
            select(Expense).where(Expense.id == expense_id)
        )
        return result.scalar_one_or_none()

    def _approval_to_response(self, approval: Approval) -> dict:
        """将审批记录转换为响应字典（含关联报销单和审批人信息）"""
        result = {
            "id": approval.id,
            "expense_id": approval.expense_id,
            "approver_id": approval.approver_id,
            "flow_id": approval.flow_id,
            "status": approval.status.value if isinstance(approval.status, ApprovalStatus) else approval.status,
            "level": approval.level,
            "comment": approval.comment,
            "created_at": approval.created_at,
            "updated_at": approval.updated_at,
        }
        if approval.approver:
            result["approver_name"] = approval.approver.full_name or approval.approver.username

        # 包含关联的报销单信息，方便前端展示
        if approval.expense:
            exp = approval.expense
            exp_type = exp.expense_type.value if hasattr(exp.expense_type, 'value') else str(exp.expense_type)
            exp_status = exp.status.value if hasattr(exp.status, 'value') else str(exp.status)
            result["expense_no"] = getattr(exp, "expense_no", "")
            result["title"] = getattr(exp, "title", "")
            result["expense_type"] = exp_type
            result["total_amount"] = getattr(exp, "total_amount", 0)
            result["expense_status"] = exp_status

        return result
