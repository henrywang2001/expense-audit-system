"""
自定义异常类和异常处理器
"""
from typing import Any, Dict, Optional
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppException(Exception):
    """应用基础异常类"""
    def __init__(self, message: str = "服务器内部错误", status_code: int = 500, detail: Any = None):
        self.message = message
        self.status_code = status_code
        self.detail = detail or {}
        super().__init__(message)


class NotFoundException(AppException):
    """资源未找到异常"""
    def __init__(self, message: str = "请求的资源不存在", detail: Any = None):
        super().__init__(message=message, status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class UnauthorizedException(AppException):
    """未授权异常"""
    def __init__(self, message: str = "认证失败，请先登录", detail: Any = None):
        super().__init__(message=message, status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


class ForbiddenException(AppException):
    """权限不足异常"""
    def __init__(self, message: str = "权限不足，无法执行此操作", detail: Any = None):
        super().__init__(message=message, status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class BadRequestException(AppException):
    """请求参数错误异常"""
    def __init__(self, message: str = "请求参数不合法", detail: Any = None):
        super().__init__(message=message, status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class ConflictException(AppException):
    """资源冲突异常（如重复创建）"""
    def __init__(self, message: str = "资源已存在", detail: Any = None):
        super().__init__(message=message, status_code=status.HTTP_409_CONFLICT, detail=detail)


class ValidationException(AppException):
    """业务逻辑校验异常"""
    def __init__(self, message: str = "校验失败", detail: Any = None):
        super().__init__(message=message, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)


class ExpenseStatusException(AppException):
    """报销单状态异常"""
    def __init__(self, message: str = "报销单状态不允许此操作", detail: Any = None):
        super().__init__(message=message, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)


class DatabaseException(AppException):
    """数据库操作异常"""
    def __init__(self, message: str = "数据库操作失败", detail: Any = None):
        super().__init__(message=message, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)


# ========== 全局异常处理器注册 ==========

async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """自定义应用异常处理器"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.message,
            "detail": exc.detail,
        },
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """HTTP异常处理器"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "detail": {},
        },
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """请求参数校验异常处理器"""
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"] if loc != "body")
        errors.append({"field": field, "message": error["msg"]})

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "message": "请求参数校验失败",
            "detail": {"errors": errors},
        },
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """通用未捕获异常处理器"""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "服务器内部错误",
            "detail": {"error": str(exc)},
        },
    )


def register_exception_handlers(app):
    """
    向 FastAPI 应用注册所有异常处理器

    Args:
        app: FastAPI 应用实例
    """
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
