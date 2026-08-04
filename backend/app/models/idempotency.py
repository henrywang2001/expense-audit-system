"""
幂等缓存模型 — 存储 AI 审核结果的幂等缓存

设计：
- 存储介质：SQLite 表 ai_review_cache（零新依赖）
- TTL：5 分钟（超过后当作未命中，不主动清理旧行）
- 并发安全：依赖 UNIQUE(expense_id, idempotency_key) 约束
- 只缓存成功结果：失败不缓存，允许调用方重试
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, UniqueConstraint
from app.models.base import Base

# 缓存过期时间（分钟）
CACHE_TTL_MINUTES = 5


class AIReviewCache(Base):
    """AI审核幂等缓存表"""
    __tablename__ = "ai_review_cache"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    expense_id = Column(Integer, nullable=False, index=True, comment="报销单ID")
    idempotency_key = Column(String(255), nullable=False, comment="客户端生成的幂等键")
    result_json = Column(Text, nullable=False, comment="审核结果 JSON")
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        comment="创建时间"
    )

    __table_args__ = (
        UniqueConstraint(
            "expense_id", "idempotency_key",
            name="uq_expense_idempotency"
        ),
    )
