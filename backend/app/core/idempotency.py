"""
幂等缓存工具 — AI 审核结果的去重缓存

设计:
- 存储介质：SQLite 表 ai_review_cache（零新依赖）
- TTL：5 分钟（超过后当作未命中，不主动清理旧行）
- 并发安全：依赖 UNIQUE(expense_id, idempotency_key) 约束
  - 先查后写的竞态：第二个 INSERT 触发 IntegrityError → catch 后静默忽略
- 只缓存成功结果：失败不缓存，允许调用方重试
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.models.idempotency import AIReviewCache, CACHE_TTL_MINUTES

logger = logging.getLogger(__name__)


async def get_cached_review(
    db: AsyncSession, expense_id: int, idempotency_key: str
) -> Optional[dict]:
    """
    查询幂等缓存。命中且未过期返回结果，否则返回 None。

    注意：此函数不 commit，仅执行 SELECT。
    """
    cutoff = datetime.utcnow() - timedelta(minutes=CACHE_TTL_MINUTES)
    result = await db.execute(
        select(AIReviewCache.result_json).where(
            AIReviewCache.expense_id == expense_id,
            AIReviewCache.idempotency_key == idempotency_key,
            AIReviewCache.created_at > cutoff,
        )
    )
    row = result.scalar_one_or_none()
    if row:
        logger.info(
            f"[Idempotency] 缓存命中 expense={expense_id} "
            f"key={idempotency_key[:8]}..."
        )
        return json.loads(row)
    return None


async def cache_review(
    db: AsyncSession, expense_id: int, idempotency_key: str, result: dict
) -> None:
    """
    写入幂等缓存。如果并发写入同一 key（UNIQUE 冲突），静默忽略。

    调用前需确保 db 的当前事务已提交（或新建独立 commit）。
    此函数内部自己 commit，不依赖外部事务状态。
    """
    cache = AIReviewCache(
        expense_id=expense_id,
        idempotency_key=idempotency_key,
        result_json=json.dumps(result, ensure_ascii=False, default=str),
    )
    db.add(cache)
    try:
        await db.commit()
        logger.info(
            f"[Idempotency] 缓存写入 expense={expense_id} "
            f"key={idempotency_key[:8]}..."
        )
    except IntegrityError:
        await db.rollback()
        logger.info(
            f"[Idempotency] 缓存已存在（并发写入）expense={expense_id}"
        )


async def purge_expired_cache(db: AsyncSession) -> int:
    """
    清理过期缓存。建议在应用启动时或定时任务中调用。

    Returns:
        删除的行数
    """
    cutoff = datetime.utcnow() - timedelta(minutes=CACHE_TTL_MINUTES)
    result = await db.execute(
        delete(AIReviewCache).where(AIReviewCache.created_at <= cutoff)
    )
    await db.commit()
    deleted = result.rowcount
    if deleted:
        logger.info(f"[Idempotency] 清理过期缓存 {deleted} 条")
    return deleted
