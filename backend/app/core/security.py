"""
安全认证模块
JWT Token 的创建和验证，密码哈希和校验
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from jose import jwt, JWTError

from app.config import settings

# ===== 密码哈希 (绕过 passlib 的 bcrypt 5.x 不兼容) =====
# bcrypt 5.x 移除了 __about__，passlib 1.7.4 做检测时崩溃
# 直接使用 bcrypt 原生 API，避免 passlib。pip pin bcrypt==4.1.3


def hash_password(password: str) -> str:
    """对明文密码进行 bcrypt 哈希"""
    import bcrypt
    pwd = password.encode("utf-8")
    if len(pwd) > 72:
        pwd = pwd[:72]
    return bcrypt.hashpw(pwd, bcrypt.gensalt(12)).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码与哈希是否匹配"""
    import bcrypt
    pwd = plain_password.encode("utf-8")
    if len(pwd) > 72:
        pwd = pwd[:72]
    try:
        return bcrypt.checkpw(pwd, hashed_password.encode("utf-8"))
    except (ValueError, TypeError):
        return False


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
