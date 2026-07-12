"""
API 依赖注入
提供数据库会话、当前用户等依赖
"""
from typing import AsyncGenerator, Optional
from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import UnauthorizedException, ForbiddenException
from app.core.security import decode_access_token
from app.models.user import User
from app.dependencies import get_db


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(None),
) -> User:
    """
    从 JWT Token 获取当前登录用户

    Args:
        db: 数据库会话
        authorization: HTTP Authorization 头部 (Bearer <token>)

    Returns:
        当前登录的用户对象

    Raises:
        UnauthorizedException: Token 无效或已过期
    """
    if not authorization:
        raise UnauthorizedException(message="缺少认证Token")

    # 提取 Token
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise UnauthorizedException(message="Token格式不正确，请使用 Bearer Token")

    # 解码 Token
    payload = decode_access_token(token)
    if payload is None:
        raise UnauthorizedException(message="Token无效或已过期")

    # 获取用户ID (JWT sub claim is always string)
    user_id_str = payload.get("sub")
    if user_id_str is None:
        raise UnauthorizedException(message="Token中缺少用户信息")

    user_id = int(user_id_str)

    # 查询用户
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()

    if user is None:
        raise UnauthorizedException(message="用户不存在")

    if not user.is_active:
        raise ForbiddenException(message="用户已被禁用")

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """获取当前活跃用户（仅检查激活状态）"""
    if not current_user.is_active:
        raise ForbiddenException(message="用户已被禁用")
    return current_user


async def get_current_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """获取当前超级管理员用户"""
    if not current_user.is_superuser:
        raise ForbiddenException(message="需要超级管理员权限")
    return current_user


async def get_admin_or_finance_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """获取管理员或财务人员用户"""
    allowed_roles = {"admin", "finance"}
    if current_user.role.value not in allowed_roles and not current_user.is_superuser:
        raise ForbiddenException(message="需要管理员或财务人员权限")
    return current_user
