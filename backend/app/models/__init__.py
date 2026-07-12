"""导入所有模型，确保 Alembic 和 create_all 能发现所有表"""
from app.models.base import Base
from app.models.user import User
from app.models.expense import Expense, ExpenseItem, Category
from app.models.rule import Rule, ApprovalFlow, Approval, AuditLog

__all__ = [
    "Base",
    "User",
    "Expense",
    "ExpenseItem",
    "Category",
    "Rule",
    "ApprovalFlow",
    "Approval",
    "AuditLog",
]
