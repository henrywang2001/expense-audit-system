"""
认证接口 - 登录、注册、个人信息等
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.dependencies import get_db
from app.models.user import User
from app.schemas.user import (
    UserCreate, UserLogin, UserResponse, TokenResponse,
    LoginResponse, UserUpdateRequest, PasswordChangeRequest,
)
from app.services.auth_service import AuthService

router = APIRouter()


@router.post("/login", response_model=LoginResponse, summary="用户登录")
async def login(
    login_data: UserLogin,
    db: AsyncSession = Depends(get_db),
):
    """用户使用用户名和密码登录，返回 JWT Token"""
    auth_service = AuthService(db)
    result = await auth_service.login(login_data.username, login_data.password)
    return LoginResponse(
        success=True,
        data=result,
        message="登录成功",
    )


@router.post("/register", response_model=LoginResponse, summary="用户注册")
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """新用户注册，注册成功后自动返回登录Token"""
    auth_service = AuthService(db)
    result = await auth_service.register(user_data)
    return LoginResponse(
        success=True,
        data=result,
        message="注册成功",
    )


@router.get("/me", response_model=UserResponse, summary="获取当前用户信息")
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    """获取当前登录用户的详细信息"""
    return current_user


@router.put("/me", response_model=UserResponse, summary="更新个人信息")
async def update_current_user(
    update_data: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新当前登录用户的个人信息"""
    auth_service = AuthService(db)
    result = await auth_service.update_user(current_user, update_data)
    return result


@router.post("/me/change-password", summary="修改密码")
async def change_password(
    password_data: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """修改当前用户的登录密码"""
    auth_service = AuthService(db)
    result = await auth_service.change_password(
        current_user,
        password_data.old_password,
        password_data.new_password,
    )
    return {"success": True, "message": "密码修改成功"}


@router.post("/logout", summary="用户退出")
async def logout(
    current_user: User = Depends(get_current_user),
):
    """用户退出登录（客户端需清除Token）"""
    # JWT是无状态的，退出主要通过客户端删除Token实现
    return {"success": True, "message": "退出成功"}
