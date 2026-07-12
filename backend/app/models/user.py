"""
用户模型
"""
import enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
from app.models.base import BaseModel


class UserRole(str, enum.Enum):
    """用户角色枚举"""
    ADMIN = "admin"
    FINANCE = "finance"
    MANAGER = "manager"
    EMPLOYEE = "employee"


class User(BaseModel):
    """用户表"""
    __tablename__ = "users"

    username = Column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="用户名（唯一）"
    )
    email = Column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="邮箱（唯一）"
    )
    password_hash = Column(
        String(255),
        nullable=False,
        comment="密码哈希值"
    )
    full_name = Column(
        String(100),
        nullable=True,
        comment="姓名"
    )
    phone = Column(
        String(20),
        nullable=True,
        comment="电话号码"
    )
    department = Column(
        String(100),
        nullable=True,
        index=True,
        comment="部门"
    )
    position = Column(
        String(100),
        nullable=True,
        comment="职位"
    )
    role = Column(
        Enum(UserRole),
        default=UserRole.EMPLOYEE,
        nullable=False,
        comment="用户角色"
    )
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        comment="是否激活"
    )
    is_superuser = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="是否为超级管理员"
    )
    last_login_at = Column(
        DateTime,
        nullable=True,
        comment="最后登录时间"
    )

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"
