"""
报表服务 - 多维度统计和分析
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from sqlalchemy import select, func, extract, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.expense import Expense, ExpenseStatus
from app.core.exceptions import ForbiddenException


class ReportService:
    """报表统计服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_summary(
        self,
        user: User,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        department: Optional[str] = None,
    ) -> dict:
        """获取报销总览"""
        base_query = select(Expense)

        # 时间范围筛选
        if start_date:
            base_query = base_query.where(Expense.created_at >= start_date)
        if end_date:
            base_query = base_query.where(Expense.created_at <= end_date + " 23:59:59")

        # 总金额和总笔数
        count_query = select(func.count(Expense.id))
        amount_query = select(func.coalesce(func.sum(Expense.total_amount), 0.0))

        # 如果指定了部门，关联用户表过滤
        if department:
            base_query = base_query.join(User, Expense.user_id == User.id).where(
                User.department == department
            )

        subquery = base_query.subquery()

        # 总计数
        total_count_result = await self.db.execute(
            select(func.count()).select_from(subquery)
        )
        total_count = total_count_result.scalar() or 0

        # 总金额
        total_amount_result = await self.db.execute(
            select(func.coalesce(func.sum(subquery.c.total_amount), 0.0))
        )
        total_amount = float(total_amount_result.scalar() or 0)

        # 状态分布
        status_distribution = await self._get_status_distribution(subquery)

        # 本月统计
        this_month = datetime.utcnow().replace(day=1)
        this_month_result = await self.db.execute(
            select(
                func.count(subquery.c.id),
                func.coalesce(func.sum(subquery.c.total_amount), 0.0)
            ).where(subquery.c.created_at >= this_month.strftime("%Y-%m-%d"))
        )
        month_row = this_month_result.one_or_none()
        month_count = month_row[0] if month_row else 0
        month_amount = float(month_row[1]) if month_row else 0.0

        return {
            "total_count": total_count,
            "total_amount": total_amount,
            "month_count": month_count,
            "month_amount": month_amount,
            "status_distribution": status_distribution,
        }

    async def get_by_type(
        self,
        user: User,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[dict]:
        """按报销类型统计"""
        query = select(
            Expense.expense_type,
            func.count(Expense.id).label("count"),
            func.coalesce(func.sum(Expense.total_amount), 0.0).label("total_amount"),
        ).group_by(Expense.expense_type)

        if start_date:
            query = query.where(Expense.created_at >= start_date)
        if end_date:
            query = query.where(Expense.created_at <= end_date + " 23:59:59")

        result = await self.db.execute(query)
        rows = result.all()

        return [
            {
                "expense_type": row[0].value if hasattr(row[0], 'value') else row[0],
                "count": row[1],
                "total_amount": float(row[2]),
            }
            for row in rows
        ]

    async def get_by_department(
        self,
        user: User,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[dict]:
        """按部门统计"""
        query = (
            select(
                User.department,
                func.count(Expense.id).label("count"),
                func.coalesce(func.sum(Expense.total_amount), 0.0).label("total_amount"),
            )
            .join(User, Expense.user_id == User.id)
            .where(User.department.isnot(None))
            .group_by(User.department)
        )

        if start_date:
            query = query.where(Expense.created_at >= start_date)
        if end_date:
            query = query.where(Expense.created_at <= end_date + " 23:59:59")

        result = await self.db.execute(query)
        rows = result.all()

        return [
            {
                "department": row[0],
                "count": row[1],
                "total_amount": float(row[2]),
            }
            for row in rows
        ]

    async def get_trend(self, user: User, months: int = 12) -> List[dict]:
        """获取月度报销趋势"""
        # 计算起始日期
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=months * 31)
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")

        # 按年月分组统计
        query = (
            select(
                func.strftime("%Y-%m", Expense.created_at).label("month"),
                func.count(Expense.id).label("count"),
                func.coalesce(func.sum(Expense.total_amount), 0.0).label("total_amount"),
            )
            .where(
                Expense.created_at >= start_str,
                Expense.created_at <= end_str + " 23:59:59",
            )
            .group_by(text("month"))
            .order_by(text("month"))
        )

        result = await self.db.execute(query)
        rows = result.all()

        return [
            {
                "month": row[0],
                "count": row[1],
                "total_amount": float(row[2]),
            }
            for row in rows
        ]

    async def _get_status_distribution(self, subquery) -> dict:
        """获取状态分布统计"""
        query = (
            select(
                subquery.c.status,
                func.count(subquery.c.id),
                func.coalesce(func.sum(subquery.c.total_amount), 0.0),
            )
            .group_by(subquery.c.status)
        )
        result = await self.db.execute(query)
        rows = result.all()

        distribution = {}
        for row in rows:
            status_value = row[0].value if hasattr(row[0], 'value') else row[0]
            distribution[status_value] = {
                "count": row[1],
                "amount": float(row[2]),
            }
        return distribution
