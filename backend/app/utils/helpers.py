"""
工具函数
常用的辅助方法
"""
import uuid
import json
import hashlib
from datetime import datetime, date
from typing import Any, Optional, Dict, List


def generate_uuid() -> str:
    """生成UUID字符串"""
    return uuid.uuid4().hex


def generate_short_id(length: int = 8) -> str:
    """生成短ID"""
    return uuid.uuid4().hex[:length]


def hash_text(text: str, algorithm: str = "md5") -> str:
    """计算文本哈希值"""
    h = hashlib.new(algorithm)
    h.update(text.encode("utf-8"))
    return h.hexdigest()


def safe_json_loads(text: str, default: Any = None) -> Any:
    """安全的JSON解析"""
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return default if default is not None else {}


def safe_json_dumps(obj: Any, default: Any = None, **kwargs) -> str:
    """安全的JSON序列化"""
    try:
        return json.dumps(obj, ensure_ascii=False, default=str, **kwargs)
    except (TypeError, ValueError):
        if default is not None:
            return default
        return "{}"


def format_datetime(dt: Optional[datetime], fmt: str = "%Y-%m-%d %H:%M:%S") -> Optional[str]:
    """格式化日期时间"""
    if dt is None:
        return None
    return dt.strftime(fmt)


def format_date(d: Optional[date], fmt: str = "%Y-%m-%d") -> Optional[str]:
    """格式化日期"""
    if d is None:
        return None
    return d.strftime(fmt)


def parse_datetime(dt_str: Optional[str]) -> Optional[datetime]:
    """解析日期时间字符串"""
    if not dt_str:
        return None

    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%d",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(dt_str, fmt)
        except ValueError:
            continue

    return None


def truncate_text(text: str, max_length: int = 200, suffix: str = "...") -> str:
    """截断文本"""
    if not text or len(text) <= max_length:
        return text or ""
    return text[:max_length - len(suffix)] + suffix


def mask_sensitive(text: str, start_keep: int = 3, end_keep: int = 4) -> str:
    """脱敏处理 - 保留首尾字符，中间用*代替"""
    if not text or len(text) <= start_keep + end_keep:
        return text or ""
    return text[:start_keep] + "*" * (len(text) - start_keep - end_keep) + text[-end_keep:]


def calculate_total(items: List[Dict[str, Any]], key: str = "amount") -> float:
    """计算金额总和"""
    return sum(item.get(key, 0) for item in items)


def human_readable_size(size_bytes: int) -> str:
    """将字节数转换为可读的格式"""
    if size_bytes < 0:
        return "0 B"

    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(size_bytes)
    unit_index = 0

    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1

    return f"{size:.1f} {units[unit_index]}"


def paginate(
    items: List[Any],
    page: int = 1,
    page_size: int = 20,
) -> Dict[str, Any]:
    """
    内存分页

    Args:
        items: 数据列表
        page: 页码
        page_size: 每页数量

    Returns:
        分页结果
    """
    total = len(items)
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    start = (page - 1) * page_size
    end = start + page_size

    return {
        "data": items[start:end],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


def dict_exclude_none(d: Dict[str, Any]) -> Dict[str, Any]:
    """从字典中移除值为 None 的键"""
    return {k: v for k, v in d.items() if v is not None}


def normalize_expense_type(expense_type: str) -> str:
    """标准化报销类型"""
    type_map = {
        "差旅": "travel",
        "旅游": "travel",
        "出差": "travel",
        "travel": "travel",
        "办公": "office",
        "办公用品": "office",
        "office": "office",
        "招待": "entertainment",
        "宴请": "entertainment",
        "entertainment": "entertainment",
        "交通": "transport",
        "transport": "transport",
        "餐饮": "meal",
        "餐费": "meal",
        "meal": "meal",
        "培训": "training",
        "training": "training",
        "设备": "equipment",
        "设备采购": "equipment",
        "equipment": "equipment",
    }
    return type_map.get(expense_type, "other")
