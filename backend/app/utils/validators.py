"""
验证工具
常用的数据校验函数
"""
import re
from typing import Optional, List, Tuple


def validate_email(email: str) -> bool:
    """验证邮箱格式"""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def validate_phone(phone: str) -> bool:
    """验证中国手机号格式"""
    pattern = r"^1[3-9]\d{9}$"
    return bool(re.match(pattern, phone))


def validate_username(username: str) -> Tuple[bool, str]:
    """
    验证用户名格式

    Returns:
        (是否合法, 错误信息)
    """
    if not username:
        return False, "用户名不能为空"

    if len(username) < 3:
        return False, "用户名长度不能少于3个字符"

    if len(username) > 50:
        return False, "用户名长度不能超过50个字符"

    # 只允许字母、数字、下划线、中文
    pattern = r"^[a-zA-Z0-9_一-鿿]+$"
    if not re.match(pattern, username):
        return False, "用户名只能包含字母、数字、下划线和中文"

    return True, ""


def validate_password(password: str) -> Tuple[bool, str]:
    """
    验证密码强度

    Returns:
        (是否合法, 错误信息)
    """
    if not password:
        return False, "密码不能为空"

    if len(password) < 6:
        return False, "密码长度不能少于6个字符"

    if len(password) > 100:
        return False, "密码长度不能超过100个字符"

    # 至少包含字母和数字
    if not re.search(r"[a-zA-Z]", password):
        return False, "密码必须包含至少一个字母"

    if not re.search(r"\d", password):
        return False, "密码必须包含至少一个数字"

    return True, ""


def validate_amount(amount: float) -> Tuple[bool, str]:
    """验证金额"""
    if amount <= 0:
        return False, "金额必须大于0"

    if amount > 10000000:
        return False, "金额不能超过1000万元"

    return True, ""


def validate_invoice_no(invoice_no: str) -> Tuple[bool, str]:
    """验证发票号格式"""
    if not invoice_no:
        return True, ""  # 发票号可选

    # 中国增值税发票号一般为8-20位数字或字母数字组合
    pattern = r"^[a-zA-Z0-9]{8,20}$"
    if not re.match(pattern, invoice_no):
        return False, "发票号格式不正确"

    return True, ""


def validate_date_range(
    start_date: Optional[str],
    end_date: Optional[str],
) -> Tuple[bool, str]:
    """验证日期范围"""
    if not start_date and not end_date:
        return True, ""

    from datetime import datetime

    date_format = "%Y-%m-%d"

    start = None
    end = None

    if start_date:
        try:
            start = datetime.strptime(start_date, date_format)
        except ValueError:
            return False, "开始日期格式不正确，请使用 YYYY-MM-DD"

    if end_date:
        try:
            end = datetime.strptime(end_date, date_format)
        except ValueError:
            return False, "结束日期格式不正确，请使用 YYYY-MM-DD"

    if start and end and start > end:
        return False, "开始日期不能晚于结束日期"

    return True, ""


def validate_file_extension(
    filename: str,
    allowed_extensions: Optional[List[str]] = None,
) -> Tuple[bool, str]:
    """验证文件扩展名"""
    import os

    if not filename:
        return False, "文件名不能为空"

    _, ext = os.path.splitext(filename)
    ext = ext.lower()

    if allowed_extensions is None:
        allowed_extensions = [".pdf", ".jpg", ".jpeg", ".png"]

    if ext not in allowed_extensions:
        return False, f"不支持的文件格式: {ext}，仅支持: {', '.join(allowed_extensions)}"

    return True, ""


def validate_file_size(file_size: int, max_size: Optional[int] = None) -> Tuple[bool, str]:
    """验证文件大小"""
    from app.config import settings

    if max_size is None:
        max_size = settings.MAX_FILE_SIZE

    if file_size <= 0:
        return False, "文件大小不能为0"

    if file_size > max_size:
        max_mb = max_size / 1048576
        return False, f"文件大小不能超过 {max_mb:.0f}MB"

    return True, ""


def is_valid_json(json_str: str) -> bool:
    """验证JSON字符串"""
    import json

    try:
        json.loads(json_str)
        return True
    except (json.JSONDecodeError, TypeError):
        return False
