"""
认证服务 - 用户注册、登录、个人信息管理
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token
from app.core.exceptions import (
    UnauthorizedException, ConflictException, BadRequestException, NotFoundException
)
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdateRequest, TokenResponse, UserResponse


class AuthService:
    """用户认证服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(self, user_data: UserCreate) -> TokenResponse:
        """
        用户注册

        Args:
            user_data: 注册信息

        Returns:
            TokenResponse: 注册成功后的登录Token

        Raises:
            ConflictException: 用户名或邮箱已存在
        """
        # 检查用户名是否已存在
        result = await self.db.execute(
            select(User).where(User.username == user_data.username)
        )
        if result.scalar_one_or_none():
            raise ConflictException(message=f"用户名 '{user_data.username}' 已被注册")

        # 检查邮箱是否已存在
        result = await self.db.execute(
            select(User).where(User.email == user_data.email)
        )
        if result.scalar_one_or_none():
            raise ConflictException(message=f"邮箱 '{user_data.email}' 已被注册")

        # 创建用户
        user = User(
            username=user_data.username,
            email=user_data.email,
            password_hash=hash_password(user_data.password),
            full_name=user_data.full_name,
            phone=user_data.phone,
            department=user_data.department,
            position=user_data.position,
            is_active=True,
            is_superuser=False,
            last_login_at=datetime.utcnow(),
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)

        # 为新注册用户生成Token
        return self._generate_token_response(user)

    async def login(self, username: str, password: str) -> TokenResponse:
        """
        用户登录

        Args:
            username: 用户名
            password: 明文密码

        Returns:
            TokenResponse: 登录Token

        Raises:
            UnauthorizedException: 用户名或密码错误
        """
        # 查找用户
        result = await self.db.execute(
            select(User).where(User.username == username)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise UnauthorizedException(message="用户名或密码错误")

        if not verify_password(password, user.password_hash):
            raise UnauthorizedException(message="用户名或密码错误")

        if not user.is_active:
            raise UnauthorizedException(message="用户已被禁用，请联系管理员")

        # 更新最后登录时间
        user.last_login_at = datetime.utcnow()
        await self.db.flush()

        return self._generate_token_response(user)

    async def update_user(
        self,
        user: User,
        update_data: UserUpdateRequest,
    ) -> UserResponse:
        """更新用户个人信息"""
        if update_data.full_name is not None:
            user.full_name = update_data.full_name
        if update_data.phone is not None:
            user.phone = update_data.phone
        if update_data.department is not None:
            user.department = update_data.department
        if update_data.position is not None:
            user.position = update_data.position

        await self.db.flush()
        await self.db.refresh(user)

        return UserResponse.model_validate(user)

    async def change_password(
        self,
        user: User,
        old_password: str,
        new_password: str,
    ) -> bool:
        """修改用户密码"""
        if not verify_password(old_password, user.password_hash):
            raise BadRequestException(message="旧密码不正确")

        user.password_hash = hash_password(new_password)
        await self.db.flush()
        return True

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """根据ID获取用户"""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    def _generate_token_response(self, user: User) -> TokenResponse:
        """生成Token响应"""
        access_token = create_access_token(
            data={"sub": user.id, "username": user.username, "role": user.role.value}
        )
        refresh_token = create_refresh_token(
            data={"sub": user.id, "type": "refresh"}
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=24 * 3600,
            user=UserResponse.model_validate(user),
        )
