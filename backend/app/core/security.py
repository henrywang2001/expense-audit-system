"""
安全认证模块
JWT Token 的创建和验证，密码哈希和校验
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from jose import jwt, JWTError
from passlib.context import CryptContext

from app.config import settings

# 密码哈希上下文 (bcrypt)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """对明文密码进行哈希处理 (bcrypt限制72字节)"""
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    return pwd_context.hash(password_bytes.decode("utf-8", errors="replace"))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证明文密码与哈希密码是否匹配"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    创建JWT访问令牌

    Args:
        data: 要编码到 Token 中的数据 (至少包含 'sub' 字段表示用户ID)
        expires_delta: Token 过期时间，默认使用配置中的 JWT_EXPIRATION_HOURS

    Returns:
        编码后的 JWT 字符串
    """
    to_encode = data.copy()
    # Convert sub (user_id) to string for JWT compliance
    if "sub" in to_encode and not isinstance(to_encode["sub"], str):
        to_encode["sub"] = str(to_encode["sub"])
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRATION_HOURS)

    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    解码并验证 JWT Token

    Args:
        token: JWT Token 字符串

    Returns:
        解码后的 payload 字典，如果 Token 无效则返回 None
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_sub": False, "verify_exp": True}
        )
        return payload
    except JWTError:
        return None


def create_refresh_token(data: Dict[str, Any]) -> str:
    """
    创建刷新 Token（有效期更长）

    Args:
        data: 要编码到 Token 中的数据

    Returns:
        编码后的 JWT 字符串
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=30)
    to_encode.update({"exp": expire, "iat": datetime.utcnow(), "type": "refresh"})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt
