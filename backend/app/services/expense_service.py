"""
报销单服务 - 报销单的CRUD、状态流转和AI审核
"""
import os
import uuid
import math
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import UploadFile
from sqlalchemy import select, update, func, desc, asc, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.core.exceptions import (
    NotFoundException, ForbiddenException, ExpenseStatusException, BadRequestException,
    ConflictException,
)
from app.models.user import User
from app.models.expense import (
    Expense, ExpenseItem, Category, ExpenseStatus, ExpenseType
)
from app.models.rule import AuditLog
from app.schemas.expense import ExpenseCreate, ExpenseUpdate, AIReviewRequest
from app.services.ai_review_presenter import enrich_review_result

logger = logging.getLogger(__name__)


class ExpenseService:
    """报销单业务服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_expense(self, user_id: int, data: ExpenseCreate) -> Expense:
        """创建报销单"""
        # 生成报销单编号
        expense_no = self._generate_expense_no()

        # 计算总金额
        total_amount = sum(item.amount for item in data.items)

        expense = Expense(
            user_id=user_id,
            expense_no=expense_no,
            title=data.title,
            expense_type=ExpenseType(data.expense_type),
            total_amount=total_amount,
            currency=data.currency,
            status=ExpenseStatus.DRAFT,
            description=data.description,
        )
        self.db.add(expense)
        await self.db.flush()

        # 创建费用明细
        for item_data in data.items:
            item = ExpenseItem(
                expense_id=expense.id,
                category_id=item_data.category_id,
                description=item_data.description,
                amount=item_data.amount,
                expense_date=item_data.expense_date,
                invoice_no=item_data.invoice_no,
                invoice_url=item_data.invoice_url,
            )
            self.db.add(item)

        # 记录审计日志
        self._add_audit_log(expense.id, "create", user_id, {"status": "draft"})

        await self.db.flush()
        await self.db.refresh(expense)

        # 重新查询以加载关联数据
        return await self._get_expense_with_relations(expense.id)

    async def get_expense(self, expense_id: int, user: User) -> Expense:
        """获取报销单详情"""
        expense = await self._get_expense_with_relations(expense_id)
        if not expense:
            raise NotFoundException(message="报销单不存在")

        # 权限检查：非管理员只能看自己的
        if not user.is_superuser and user.role.value not in ("admin", "finance"):
            if expense.user_id != user.id:
                raise ForbiddenException(message="无权查看此报销单")

        return expense

    async def list_expenses(
        self,
        user: User,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        expense_type: Optional[str] = None,
        keyword: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> dict:
        """获取报销单列表"""
        query = select(Expense)

        # 权限过滤：非管理员只能看自己的
        if not user.is_superuser and user.role.value not in ("admin", "finance"):
            query = query.where(Expense.user_id == user.id)

        # 状态筛选
        if status:
            query = query.where(Expense.status == ExpenseStatus(status))

        # 类型筛选
        if expense_type:
            query = query.where(Expense.expense_type == ExpenseType(expense_type))

        # 关键词搜索
        if keyword:
            query = query.where(
                or_(
                    Expense.title.contains(keyword),
                    Expense.expense_no.contains(keyword),
                    Expense.description.contains(keyword),
                )
            )

        # 获取总数
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # 排序
        sort_column = getattr(Expense, sort_by, Expense.created_at)
        if sort_order == "asc":
            query = query.order_by(asc(sort_column))
        else:
            query = query.order_by(desc(sort_column))

        # 分页
        query = query.offset((page - 1) * page_size).limit(page_size)
        query = query.options(selectinload(Expense.items))

        result = await self.db.execute(query)
        expenses = result.scalars().unique().all()

        return {
            "success": True,
            "data": [self._expense_to_response(e) for e in expenses],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": math.ceil(total / page_size) if total > 0 else 0,
        }

    async def update_expense(
        self, expense_id: int, user: User, data: ExpenseUpdate
    ) -> Expense:
        """更新报销单"""
        expense = await self._get_expense_with_relations(expense_id)
        if not expense:
            raise NotFoundException(message="报销单不存在")

        # 权限检查
        if expense.user_id != user.id and not user.is_superuser:
            raise ForbiddenException(message="无权修改此报销单")

        # 只有草稿状态可修改
        if expense.status != ExpenseStatus.DRAFT:
            raise ExpenseStatusException(message="只有草稿状态的报销单可以修改")

        # 更新字段
        if data.title is not None:
            expense.title = data.title
        if data.expense_type is not None:
            expense.expense_type = ExpenseType(data.expense_type)
        if data.description is not None:
            expense.description = data.description
        if data.currency is not None:
            expense.currency = data.currency
        if data.remark is not None:
            expense.remark = data.remark

        # 更新费用明细（如果提供）
        if data.items is not None:
            # 删除旧明细
            delete_query = select(ExpenseItem).where(ExpenseItem.expense_id == expense_id)
            old_items = await self.db.execute(delete_query)
            for old_item in old_items.scalars().all():
                await self.db.delete(old_item)

            # 添加新明细
            total = 0.0
            for item_data in data.items:
                item = ExpenseItem(
                    expense_id=expense.id,
                    category_id=item_data.category_id,
                    description=item_data.description,
                    amount=item_data.amount,
                    expense_date=item_data.expense_date,
                    invoice_no=item_data.invoice_no,
                    invoice_url=item_data.invoice_url,
                )
                self.db.add(item)
                total += item_data.amount
            expense.total_amount = total

        await self.db.flush()
        await self.db.refresh(expense)
        return await self._get_expense_with_relations(expense.id)

    async def delete_expense(self, expense_id: int, user: User) -> None:
        """删除报销单"""
        expense = await self._get_expense_with_relations(expense_id)
        if not expense:
            raise NotFoundException(message="报销单不存在")

        # 权限检查
        if expense.user_id != user.id and not user.is_superuser:
            raise ForbiddenException(message="无权删除此报销单")

        # 只有草稿状态可以删除
        if expense.status != ExpenseStatus.DRAFT:
            raise ExpenseStatusException(message="只有草稿状态的报销单可以删除")

        await self.db.delete(expense)
        await self.db.flush()

    async def submit_expense(self, expense_id: int, user: User) -> None:
        """提交报销单"""
        expense = await self._get_expense_with_relations(expense_id)
        if not expense:
            raise NotFoundException(message="报销单不存在")

        if expense.user_id != user.id:
            raise ForbiddenException(message="无权提交此报销单")

        if expense.status != ExpenseStatus.DRAFT:
            raise ExpenseStatusException(message="只有草稿状态可以提交")

        if not expense.items:
            raise BadRequestException(message="报销单必须包含至少一条费用明细")

        expense.status = ExpenseStatus.PENDING
        expense.submitted_at = datetime.utcnow()
        self._add_audit_log(expense_id, "submit", user.id, {"status": "pending"})

        # 自动创建审批记录：分配财务/管理员为审批人
        await self._create_approval_records(expense_id, expense.total_amount)

        await self.db.flush()

    async def _create_approval_records(self, expense_id: int, total_amount: float):
        """为报销单自动创建审批记录"""
        from app.models.rule import Approval, ApprovalStatus
        from app.models.user import UserRole

        # 查询所有财务和管理员用户作为审批人
        result = await self.db.execute(
            select(User).where(
                User.role.in_([UserRole.ADMIN, UserRole.FINANCE]),
                User.is_active == True
            )
        )
        approvers = result.scalars().all()

        if not approvers:
            return

        # 根据金额决定审批层级
        if total_amount <= 500:
            levels = 1  # 一级审批
        elif total_amount <= 2000:
            levels = 2  # 二级审批
        else:
            levels = 3  # 三级审批

        for level in range(1, min(levels, len(approvers)) + 1):
            approver = approvers[level - 1]
            approval = Approval(
                expense_id=expense_id,
                approver_id=approver.id,
                status=ApprovalStatus.PENDING,
                level=level,
            )
            self.db.add(approval)

    async def withdraw_expense(self, expense_id: int, user: User) -> None:
        """撤回报销单"""
        expense = await self._get_expense_with_relations(expense_id)
        if not expense:
            raise NotFoundException(message="报销单不存在")

        if expense.user_id != user.id:
            raise ForbiddenException(message="无权撤回此报销单")

        if expense.status != ExpenseStatus.PENDING:
            raise ExpenseStatusException(message="只有已提交或待审核状态可以撤回")

        expense.status = ExpenseStatus.DRAFT
        expense.submitted_at = None
        self._add_audit_log(expense_id, "withdraw", user.id, {"status": "draft"})

        # 删除待处理的审批记录
        await self._remove_pending_approvals(expense_id)

        await self.db.flush()

    async def _remove_pending_approvals(self, expense_id: int):
        """删除待处理的审批记录"""
        from app.models.rule import Approval, ApprovalStatus
        result = await self.db.execute(
            select(Approval).where(
                Approval.expense_id == expense_id,
                Approval.status == ApprovalStatus.PENDING
            )
        )
        for approval in result.scalars().all():
            await self.db.delete(approval)

    async def ai_review(
        self, expense_id: int, user: User, request: AIReviewRequest
    ) -> dict:
        """
        执行 AI 智能审核（并发安全 + 幂等 + 乐观锁 + 事务拆分版）

        流程分四阶段：
          Phase 0: 幂等缓存快路 — 命中直接返回，不重跑 LLM
          Phase 1: 短事务 — 状态校验 + 标记 running + commit 释放
          Phase 2: LLM 调用 — 在事务外，不持有 DB 锁
          Phase 3: 短事务 — 乐观锁写回结果 + 审计日志 + commit
          Phase 4: 写入幂等缓存（独立事务）
        """
        from app.agents.workflow import AgentWorkflow
        from app.core.idempotency import get_cached_review, cache_review

        # ===== Phase 0: 幂等缓存快路 =====
        if request.idempotency_key:
            cached = await get_cached_review(
                self.db, expense_id, request.idempotency_key
            )
            if cached is not None:
                return cached

        # ===== Phase 1: 短事务 — 读取 + 状态门禁 + 标记 running =====
        expense = await self._get_expense_with_relations(expense_id)
        if not expense:
            raise NotFoundException(message="报销单不存在")

        # ① 状态转移前置校验：只允许 DRAFT / PENDING 触发 AI 审核
        ALLOWED_STATUSES = {ExpenseStatus.DRAFT, ExpenseStatus.PENDING}
        if expense.status not in ALLOWED_STATUSES:
            raise ConflictException(
                message=(
                    f"报销单当前状态为「{expense.status.value}」，"
                    f"只有「草稿」或「待审核」状态的报销单可以触发 AI 审核"
                )
            )

        # ①-bis: 防止并发重复触发（配合乐观锁形成双重防护）
        if expense.ai_review_status == "running":
            raise ConflictException(
                message="该报销单正在 AI 审核中，请稍后再试"
            )

        # ② 乐观锁：记录当前版本号，在 Phase 3 写回时校验
        snapshot_version = expense.version

        # 标记 running 并立即提交（手动 UPDATE + WHERE version 防止并发）
        stmt_mark = (
            update(Expense)
            .where(
                Expense.id == expense_id,
                Expense.version == snapshot_version,
            )
            .values(
                ai_review_status="running",
                version=Expense.version + 1,
            )
        )
        mark_result = await self.db.execute(stmt_mark)
        if mark_result.rowcount == 0:
            await self.db.rollback()
            raise ConflictException(
                message="数据版本冲突，可能已被其他请求修改，请刷新后重试"
            )

        await self.db.commit()  # ← 关键：短事务立即提交，释放 SQLite 写锁

        # ===== Phase 2: 长耗时 LLM 调用（在事务外，不持有 DB 锁） =====
        try:
            workflow = AgentWorkflow(self.db, user)
            result = await workflow.execute(
                expense_id=expense_id,
                enabled_agents=request.enabled_agents,
                custom_context=request.custom_rules,
            )
        except Exception as exc:
            # 异常回滚：清除 running 状态，防止死锁前端
            logger.error(
                f"[AI Review] workflow 执行异常 expense={expense_id}: {exc}",
                exc_info=True,
            )
            try:
                stmt_fail = (
                    update(Expense)
                    .where(Expense.id == expense_id)
                    .values(ai_review_status="failed")
                )
                await self.db.execute(stmt_fail)
                await self.db.commit()
            except Exception as cleanup_exc:
                logger.error(
                    f"[AI Review] 清除 running 状态失败 expense={expense_id}: "
                    f"{cleanup_exc}"
                )
                await self.db.rollback()
            raise  # 重新抛出原始异常

        # ===== Phase 2.5: 展示层字段收敛 =====
        # workflow 返回的是「工作流原始结构」(final_reason / agent_results)，
        # 而前端 AI 审核卡片消费的是 summary / issues / suggestions。
        # 这里把原始结构映射成展示字段（只加不减，workflow 原有键全部保留），
        # 使得同一份 result 同时满足两个消费方：
        #   ① 本次 POST 响应的 AIReviewResponse.data
        #   ② 落库的 expenses.ai_review_result（详情页读的就是它）
        result = enrich_review_result(result)

        # ===== Phase 3: 短事务 — 乐观锁写回结果 =====
        # Phase 1 已设 version=snapshot_version+1，这里直接校验该版本
        current_version = snapshot_version + 1

        risk_level = result.get("risk_level")
        risk_score = result.get("risk_score")

        stmt_update = (
            update(Expense)
            .where(
                Expense.id == expense_id,
                Expense.version == current_version,  # ② 乐观锁校验
            )
            .values(
                status=ExpenseStatus.PENDING,
                ai_review_result=result,
                risk_level=risk_level,
                risk_score=risk_score,
                version=Expense.version + 1,
                ai_review_status="done",
            )
        )
        update_result = await self.db.execute(stmt_update)
        if update_result.rowcount == 0:
            await self.db.rollback()
            raise ConflictException(
                message="审核结果写入冲突（数据版本已变化），请刷新后重试"
            )

        # 审计日志与结果写入在同一事务内（原子性）
        self._add_audit_log(
            expense_id, "ai_review", user.id,
            {"risk_level": risk_level, "risk_score": risk_score}
        )
        await self.db.commit()

        # ===== Phase 4: 写入幂等缓存（独立事务，失败不影响业务） =====
        if request.idempotency_key:
            await cache_review(
                self.db, expense_id, request.idempotency_key, result
            )

        return result

    async def upload_invoice(self, file: UploadFile, user: User) -> dict:
        """上传发票文件"""
        # 验证文件扩展名
        ext = os.path.splitext(file.filename or "")[1].lower()
        allowed_extensions = {".pdf", ".jpg", ".jpeg", ".png"}
        if ext not in allowed_extensions:
            raise BadRequestException(message=f"不支持的文件格式: {ext}")

        # 验证文件大小
        content = await file.read()
        if len(content) > settings.MAX_FILE_SIZE:
            raise BadRequestException(message=f"文件大小不能超过 {settings.MAX_FILE_SIZE // 1048576}MB")

        # 生成唯一文件名
        filename = f"{uuid.uuid4().hex}{ext}"
        upload_path = os.path.join(settings.UPLOAD_DIR, filename)

        # 确保目录存在
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

        # 保存文件
        with open(upload_path, "wb") as f:
            f.write(content)

        return {
            "filename": filename,
            "original_name": file.filename,
            "size": len(content),
            "url": f"/uploads/{filename}",
        }

    async def get_user_statistics(self, user: User) -> dict:
        """获取用户报销统计"""
        # 总数
        count_query = select(func.count(Expense.id)).where(Expense.user_id == user.id)
        total_result = await self.db.execute(count_query)
        total_count = total_result.scalar() or 0

        # 总金额
        amount_query = select(func.coalesce(func.sum(Expense.total_amount), 0.0)).where(
            Expense.user_id == user.id
        )
        amount_result = await self.db.execute(amount_query)
        total_amount = float(amount_result.scalar() or 0)

        # 状态分布
        status_query = (
            select(Expense.status, func.count(Expense.id), func.coalesce(func.sum(Expense.total_amount), 0.0))
            .where(Expense.user_id == user.id)
            .group_by(Expense.status)
        )
        status_result = await self.db.execute(status_query)
        status_distribution = {}
        for row in status_result.all():
            status_distribution[row[0].value] = {
                "count": row[1],
                "amount": float(row[2]),
            }

        # 类型分布
        type_query = (
            select(Expense.expense_type, func.count(Expense.id), func.coalesce(func.sum(Expense.total_amount), 0.0))
            .where(Expense.user_id == user.id)
            .group_by(Expense.expense_type)
        )
        type_result = await self.db.execute(type_query)
        type_distribution = {}
        for row in type_result.all():
            type_distribution[row[0].value] = {
                "count": row[1],
                "amount": float(row[2]),
            }

        return {
            "total_count": total_count,
            "total_amount": total_amount,
            "by_status": status_distribution,
            "by_type": type_distribution,
        }

    # ========== 私有辅助方法 ==========

    def _generate_expense_no(self) -> str:
        """生成报销单编号"""
        from datetime import datetime as dt
        now = dt.utcnow()
        random_suffix = uuid.uuid4().hex[:6].upper()
        return f"EXP-{now.strftime('%Y%m%d')}-{random_suffix}"

    async def _get_expense_with_relations(self, expense_id: int) -> Optional[Expense]:
        """带关联数据加载的报销单查询"""
        result = await self.db.execute(
            select(Expense)
            .options(
                selectinload(Expense.items),
                selectinload(Expense.user),
            )
            .where(Expense.id == expense_id)
        )
        return result.scalar_one_or_none()

    def _add_audit_log(
        self, expense_id: int, action: str, actor_id: int, details: dict = None
    ):
        """添加审核日志"""
        log = AuditLog(
            expense_id=expense_id,
            action=action,
            actor=str(actor_id),
            details=details or {},
        )
        self.db.add(log)

    @staticmethod
    def _extract_submitter(expense: Expense) -> tuple:
        """安全提取提交人姓名/部门.

        直接复用 ``Expense.submitter_name`` / ``Expense.submitter_department``
        只读属性，保证列表接口与详情接口（后者由 Pydantic 直接从 ORM 属性
        取值）行为完全一致。

        Returns:
            (submitter_name, submitter_department)
        """
        return (
            getattr(expense, "submitter_name", None),
            getattr(expense, "submitter_department", None),
        )

    def _expense_to_response(self, expense: Expense) -> dict:
        """将Expense模型转换为响应字典"""
        submitter_name, submitter_department = self._extract_submitter(expense)
        return {
            "id": expense.id,
            "user_id": expense.user_id,
            "submitter_name": submitter_name,
            "submitter_department": submitter_department,
            "expense_no": expense.expense_no,
            "title": expense.title,
            "expense_type": expense.expense_type.value if isinstance(expense.expense_type, ExpenseType) else expense.expense_type,
            "total_amount": expense.total_amount,
            "currency": expense.currency,
            "status": expense.status.value if isinstance(expense.status, ExpenseStatus) else expense.status,
            "description": expense.description,
            "remark": expense.remark,
            "submitted_at": expense.submitted_at,
            "approved_at": expense.approved_at,
            "paid_at": expense.paid_at,
            "risk_level": expense.risk_level.value if expense.risk_level else None,
            "risk_score": expense.risk_score,
            "ai_review_result": expense.ai_review_result,
            "items": [
                {
                    "id": item.id,
                    "expense_id": item.expense_id,
                    "category_id": item.category_id,
                    "description": item.description,
                    "amount": item.amount,
                    "expense_date": item.expense_date,
                    "invoice_no": item.invoice_no,
                    "invoice_url": item.invoice_url,
                    "invoice_verified": item.invoice_verified,
                    "created_at": item.created_at,
                }
                for item in (expense.items or [])
            ],
            "created_at": expense.created_at,
            "updated_at": expense.updated_at,
        }
