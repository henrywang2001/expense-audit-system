"""
规则引擎和审批流程模型
"""
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime,
    ForeignKey, Text, JSON, Enum, func
)
from sqlalchemy.orm import relationship
from app.models.base import BaseModel, Base
import enum


class RuleType(str, enum.Enum):
    """规则类型枚举"""
    AMOUNT_LIMIT = "amount_limit"           # 金额限制
    FREQUENCY = "frequency"                 # 频率限制
    CATEGORY = "category"                   # 类别限制
    DEPARTMENT = "department"               # 部门限制
    POSITION = "position"                   # 职位限制
    TIME = "time"                           # 时间限制
    COMPLIANCE = "compliance"               # 合规规则
    CUSTOM = "custom"                       # 自定义规则


class ApprovalStatus(str, enum.Enum):
    """审批状态枚举"""
    PENDING = "pending"         # 待审批
    APPROVED = "approved"       # 已通过
    REJECTED = "rejected"       # 已拒绝
    RETURNED = "returned"       # 已退回


class Rule(BaseModel):
    """审核规则表"""
    __tablename__ = "rules"

    name = Column(
        String(200),
        nullable=False,
        comment="规则名称"
    )
    rule_type = Column(
        Enum(RuleType),
        nullable=False,
        comment="规则类型"
    )
    condition = Column(
        Text,
        nullable=False,
        comment="规则条件（JSON字符串 / 人类可读描述）"
    )
    action = Column(
        String(200),
        nullable=False,
        comment="规则动作（如：reject / warn / require_approval）"
    )
    message = Column(
        String(500),
        nullable=True,
        default="",
        server_default="",
        comment="规则命中后的提示文案（为空时回退为 '{name}不符合规则'）"
    )
    config = Column(
        JSON,
        nullable=True,
        comment="规则配置（JSON对象）"
    )
    structured_condition = Column(
        JSON,
        nullable=True,
        comment="json-logic 结构化条件（机器可执行）"
    )
    exec_mode = Column(
        String(20),
        nullable=False,
        default="semantic",
        server_default="semantic",
        comment="执行模式: deterministic / pre_computed / semantic"
    )
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        comment="是否启用"
    )

    def __repr__(self):
        return f"<Rule(id={self.id}, name='{self.name}', type='{self.rule_type}')>"


class ApprovalFlow(BaseModel):
    """审批流程定义表"""
    __tablename__ = "approval_flows"

    name = Column(
        String(200),
        nullable=False,
        comment="流程名称（如：普通报销流程、大额报销流程）"
    )
    description = Column(
        String(500),
        nullable=True,
        comment="流程说明"
    )
    levels = Column(
        JSON,
        nullable=False,
        comment="审批层级（JSON数组，如：[{'level': 1, 'role': 'manager'}, {'level': 2, 'role': 'finance'}]）"
    )
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        comment="是否启用"
    )

    # 关联审批记录
    approvals = relationship("Approval", back_populates="flow")

    def __repr__(self):
        return f"<ApprovalFlow(id={self.id}, name='{self.name}')>"


class Approval(BaseModel):
    """审批记录表"""
    __tablename__ = "approvals"

    expense_id = Column(
        Integer,
        ForeignKey("expenses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="报销单ID"
    )
    approver_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        comment="审批人ID"
    )
    flow_id = Column(
        Integer,
        ForeignKey("approval_flows.id"),
        nullable=True,
        comment="审批流程ID"
    )
    status = Column(
        Enum(ApprovalStatus),
        default=ApprovalStatus.PENDING,
        nullable=False,
        comment="审批状态"
    )
    level = Column(
        Integer,
        default=1,
        nullable=False,
        comment="审批层级"
    )
    comment = Column(
        String(500),
        nullable=True,
        comment="审批意见"
    )

    # 关联
    expense = relationship("Expense", back_populates="approvals")
    approver = relationship("User")
    flow = relationship("ApprovalFlow", back_populates="approvals")

    def __repr__(self):
        return f"<Approval(id={self.id}, expense_id={self.expense_id}, status='{self.status}')>"


class AuditLog(BaseModel):
    """审核日志表"""
    __tablename__ = "audit_logs"

    expense_id = Column(
        Integer,
        ForeignKey("expenses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="报销单ID"
    )
    action = Column(
        String(100),
        nullable=False,
        comment="操作类型（如：create / submit / approve / reject / ai_review）"
    )
    actor = Column(
        String(100),
        nullable=True,
        comment="操作人（用户名）"
    )
    details = Column(
        JSON,
        nullable=True,
        comment="操作详情（JSON）"
    )

    # 关联
    expense = relationship("Expense", back_populates="audit_logs")

    def __repr__(self):
        return f"<AuditLog(id={self.id}, expense_id={self.expense_id}, action='{self.action}')>"
