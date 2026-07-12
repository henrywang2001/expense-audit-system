"""
数据库查询工具
供 AI Agent 使用的数据库查询接口，用于检索历史数据和执行数据统计
"""
import logging
from typing import Optional, List, Dict, Any

from sqlalchemy import select, func, desc, and_, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.expense import Expense, ExpenseItem, ExpenseStatus, ExpenseType, Category
from app.models.rule import Rule, Approval, AuditLog

logger = logging.getLogger(__name__)


class DatabaseTool:
    """
    Agent 数据库查询工具

    为 AI Agent 提供安全的数据查询能力
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_expenses(
        self,
        user_id: int,
        limit: int = 20,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """获取用户的报销记录"""
        query = select(Expense).where(Expense.user_id == user_id)

        if status:
            query = query.where(Expense.status == ExpenseStatus(status))

        query = query.order_by(desc(Expense.created_at)).limit(limit)
        result = await self.db.execute(query)
        expenses = result.scalars().all()

        return [self._expense_to_dict(e) for e in expenses]

    async def get_similar_expenses(
        self,
        expense_type: str,
        amount_range: tuple = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """查找相似的报销记录"""
        query = select(Expense)

        if expense_type:
            query = query.where(Expense.expense_type == ExpenseType(expense_type))

        if amount_range:
            min_amount, max_amount = amount_range
            if min_amount is not None:
                query = query.where(Expense.total_amount >= min_amount)
            if max_amount is not None:
                query = query.where(Expense.total_amount <= max_amount)

        query = query.order_by(desc(Expense.created_at)).limit(limit)
        result = await self.db.execute(query)
        expenses = result.scalars().all()

        return [self._expense_to_dict(e) for e in expenses]

    async def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """获取用户报销统计"""
        # 总金额
        amount_result = await self.db.execute(
            select(func.coalesce(func.sum(Expense.total_amount), 0.0))
            .where(Expense.user_id == user_id)
        )
        total_amount = float(amount_result.scalar() or 0)

        # 总笔数
        count_result = await self.db.execute(
            select(func.count(Expense.id))
            .where(Expense.user_id == user_id)
        )
        total_count = count_result.scalar() or 0

        # 按月统计
        monthly_result = await self.db.execute(
            select(
                func.strftime("%Y-%m", Expense.created_at).label("month"),
                func.count(Expense.id).label("count"),
                func.coalesce(func.sum(Expense.total_amount), 0.0).label("amount"),
            )
            .where(Expense.user_id == user_id)
            .group_by(text("month"))
            .order_by(text("month DESC"))
            .limit(12)
        )

        monthly = []
        for row in monthly_result.all():
            monthly.append({
                "month": row[0],
                "count": row[1],
                "amount": float(row[2]),
            })

        return {
            "user_id": user_id,
            "total_count": total_count,
            "total_amount": total_amount,
            "monthly_trend": monthly,
        }

    async def get_department_stats(self, department: str) -> Dict[str, Any]:
        """获取部门报销统计"""
        result = await self.db.execute(
            select(
                func.count(Expense.id).label("count"),
                func.coalesce(func.sum(Expense.total_amount), 0.0).label("amount"),
            )
            .join(User, Expense.user_id == User.id)
            .where(User.department == department)
        )
        row = result.one_or_none()
        return {
            "department": department,
            "count": row[0] if row else 0,
            "amount": float(row[1]) if row else 0.0,
        }

    async def check_duplicate_invoice(self, invoice_no: str) -> bool:
        """检查发票号是否重复"""
        if not invoice_no:
            return False

        result = await self.db.execute(
            select(func.count(ExpenseItem.id))
            .where(
                ExpenseItem.invoice_no == invoice_no,
                ExpenseItem.invoice_verified == True,
            )
        )
        count = result.scalar() or 0
        return count > 0

    async def get_rules_by_type(self, rule_type: str) -> List[Dict[str, Any]]:
        """获取指定类型的规则"""
        result = await self.db.execute(
            select(Rule)
            .where(Rule.rule_type == rule_type, Rule.is_active == True)
        )
        rules = result.scalars().all()
        return [
            {
                "id": r.id,
                "name": r.name,
                "condition": r.condition,
                "action": r.action,
                "config": r.config,
            }
            for r in rules
        ]

    async def get_audit_logs(
        self, expense_id: int, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """获取报销单的审计日志"""
        result = await self.db.execute(
            select(AuditLog)
            .where(AuditLog.expense_id == expense_id)
            .order_by(desc(AuditLog.created_at))
            .limit(limit)
        )
        logs = result.scalars().all()
        return [
            {
                "id": log.id,
                "action": log.action,
                "actor": log.actor,
                "details": log.details,
                "created_at": str(log.created_at) if log.created_at else None,
            }
            for log in logs
        ]

    async def get_categories(self) -> List[Dict[str, Any]]:
        """获取所有费用类别"""
        result = await self.db.execute(
            select(Category).where(Category.is_active == True)
        )
        categories = result.scalars().all()
        return [
            {
                "id": c.id,
                "name": c.name,
                "code": c.code,
                "max_amount": c.max_amount,
                "description": c.description,
            }
            for c in categories
        ]

    async def run_custom_query(self, query_text: str) -> Dict[str, Any]:
        """
        执行自定义SQL查询（仅限SELECT）
        注意：此方法做了基本的安全限制，生产环境应使用更安全的方案
        """
        # 安全检查：只允许SELECT
        query_upper = query_text.strip().upper()
        if not query_upper.startswith("SELECT"):
            raise ValueError("仅允许执行 SELECT 查询")

        # 禁止危险操作
        dangerous = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE", "TRUNCATE"]
        for keyword in dangerous:
            if keyword in query_upper:
                raise ValueError(f"不允许使用 {keyword} 操作")

        try:
            result = await self.db.execute(text(query_text))
            rows = result.all()
            columns = list(result.keys()) if result.keys() else []

            return {
                "columns": columns,
                "rows": [dict(zip(columns, row)) for row in rows],
                "row_count": len(rows),
            }
        except Exception as e:
            logger.error(f"自定义查询失败: {e}")
            raise

    def _expense_to_dict(self, expense: Expense) -> Dict[str, Any]:
        """报销单转字典"""
        return {
            "id": expense.id,
            "user_id": expense.user_id,
            "expense_no": expense.expense_no,
            "title": expense.title,
            "expense_type": expense.expense_type.value if hasattr(expense.expense_type, 'value') else str(expense.expense_type),
            "total_amount": expense.total_amount,
            "status": expense.status.value if hasattr(expense.status, 'value') else str(expense.status),
            "description": expense.description,
            "risk_level": expense.risk_level.value if expense.risk_level and hasattr(expense.risk_level, 'value') else expense.risk_level,
            "risk_score": expense.risk_score,
            "created_at": str(expense.created_at) if expense.created_at else None,
        }
