"""
报销单及相关模型
"""
import enum
from typing import Optional

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime,
    ForeignKey, Text, JSON, Enum, func
)
from sqlalchemy.orm import relationship
from app.models.base import BaseModel, Base


class ExpenseType(str, enum.Enum):
    """报销类型枚举"""
    TRAVEL = "travel"               # 差旅费
    OFFICE = "office"               # 办公费
    ENTERTAINMENT = "entertainment"  # 招待费
    TRANSPORT = "transport"         # 交通费
    MEAL = "meal"                   # 餐饮费
    TRAINING = "training"           # 培训费
    EQUIPMENT = "equipment"         # 设备费
    OTHER = "other"                 # 其他


class ExpenseStatus(str, enum.Enum):
    """报销单状态枚举"""
    DRAFT = "draft"           # 草稿
    SUBMITTED = "submitted"   # 已提交
    PENDING = "pending"       # 待审核
    APPROVED = "approved"     # 已通过
    REJECTED = "rejected"     # 已拒绝
    PAID = "paid"             # 已付款
    CANCELLED = "cancelled"   # 已取消


class RiskLevel(str, enum.Enum):
    """风险等级枚举"""
    LOW = "low"             # 低风险
    MEDIUM = "medium"       # 中风险
    HIGH = "high"           # 高风险
    CRITICAL = "critical"   # 严重风险


class Category(BaseModel):
    """费用类别表"""
    __tablename__ = "categories"

    name = Column(
        String(100),
        nullable=False,
        comment="类别名称（如：差旅费、办公用品、餐费）"
    )
    code = Column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="类别编码"
    )
    max_amount = Column(
        Float,
        nullable=True,
        comment="该类别最大可报销金额"
    )
    description = Column(
        String(500),
        nullable=True,
        comment="类别说明"
    )
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        comment="是否启用"
    )

    # 关联的费用明细
    expense_items = relationship("ExpenseItem", back_populates="category")

    def __repr__(self):
        return f"<Category(id={self.id}, code='{self.code}', name='{self.name}')>"


class Expense(BaseModel):
    """报销单主表"""
    __tablename__ = "expenses"

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
        comment="报销人ID"
    )
    expense_no = Column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="报销单编号"
    )
    title = Column(
        String(200),
        nullable=False,
        comment="报销单标题"
    )
    expense_type = Column(
        Enum(ExpenseType),
        nullable=False,
        comment="报销类型"
    )
    total_amount = Column(
        Float,
        default=0.0,
        nullable=False,
        comment="报销总金额"
    )
    currency = Column(
        String(10),
        default="CNY",
        nullable=False,
        comment="币种"
    )
    status = Column(
        Enum(ExpenseStatus),
        default=ExpenseStatus.DRAFT,
        nullable=False,
        index=True,
        comment="报销单状态"
    )
    description = Column(
        String(1000),
        nullable=True,
        comment="报销说明"
    )
    remark = Column(
        String(500),
        nullable=True,
        comment="备注"
    )
    submitted_at = Column(
        DateTime,
        nullable=True,
        comment="提交时间"
    )
    approved_at = Column(
        DateTime,
        nullable=True,
        comment="审批通过时间"
    )
    paid_at = Column(
        DateTime,
        nullable=True,
        comment="付款时间"
    )
    risk_level = Column(
        Enum(RiskLevel),
        nullable=True,
        comment="风险等级（AI评估）"
    )
    risk_score = Column(
        Float,
        nullable=True,
        comment="风险分数（0-100，AI评估）"
    )
    ai_review_result = Column(
        JSON,
        nullable=True,
        comment="AI审核结果详情（JSON）"
    )
    # --- 并发/幂等字段 ---
    version = Column(
        Integer,
        nullable=False,
        default=1,
        comment="乐观锁版本号，用于并发更新冲突检测"
    )
    ai_review_status = Column(
        String(20),
        nullable=True,
        comment="AI审核运行状态: running / done / failed"
    )

    # 关联
    user = relationship("User", lazy="joined")
    items = relationship(
        "ExpenseItem",
        back_populates="expense",
        cascade="all, delete-orphan"
    )
    approvals = relationship(
        "Approval",
        back_populates="expense",
        cascade="all, delete-orphan"
    )
    audit_logs = relationship(
        "AuditLog",
        back_populates="expense",
        cascade="all, delete-orphan"
    )

    # ===== 提交人冗余只读属性 =====
    # 说明：`user` 关系声明为 lazy="joined"，任何 Expense 查询都会随主查询
    # LEFT JOIN 出 users 行，因此这里读取不会触发异步懒加载。
    # 仍做防御性判空，保证关联缺失时返回 None 而非抛异常。

    @property
    def submitter_name(self) -> Optional[str]:
        """提交人姓名（优先 full_name，回退 username）"""
        user = self.__dict__.get("user")
        if user is None:
            return None
        return getattr(user, "full_name", None) or getattr(user, "username", None)

    @property
    def submitter_department(self) -> Optional[str]:
        """提交人所属部门"""
        user = self.__dict__.get("user")
        if user is None:
            return None
        return getattr(user, "department", None)

    def __repr__(self):
        return f"<Expense(id={self.id}, no='{self.expense_no}', status='{self.status}')>"


class ExpenseItem(BaseModel):
    """报销明细表"""
    __tablename__ = "expense_items"

    expense_id = Column(
        Integer,
        ForeignKey("expenses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属报销单ID"
    )
    category_id = Column(
        Integer,
        ForeignKey("categories.id"),
        nullable=True,
        comment="费用类别ID"
    )
    description = Column(
        String(500),
        nullable=False,
        comment="费用说明"
    )
    amount = Column(
        Float,
        nullable=False,
        comment="金额"
    )
    expense_date = Column(
        DateTime,
        nullable=True,
        comment="费用发生日期"
    )
    invoice_no = Column(
        String(100),
        nullable=True,
        comment="发票号码"
    )
    invoice_url = Column(
        String(500),
        nullable=True,
        comment="发票文件URL"
    )
    invoice_verified = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="发票是否已验证"
    )

    # 关联
    expense = relationship("Expense", back_populates="items")
    category = relationship("Category", back_populates="expense_items")

    def __repr__(self):
        return f"<ExpenseItem(id={self.id}, amount={self.amount})>"
