"""
SQLAlchemy 基础模型
提供所有模型共用的字段和方法
"""
from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, func
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class TimestampMixin:
    """时间戳混入类，为模型提供创建时间和更新时间"""
    created_at = Column(
        DateTime,
        default=func.now(),  # 使用数据库函数获取当前时间
        nullable=False,
        comment="创建时间"
    )
    updated_at = Column(
        DateTime,
        default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="更新时间"
    )


class BaseModel(Base, TimestampMixin):
    """所有模型的抽象基类"""
    __abstract__ = True

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        index=True,
        comment="主键ID"
    )

    def to_dict(self) -> dict:
        """
        将模型实例转换为字典

        Returns:
            包含所有非私有字段的字典
        """
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if isinstance(value, datetime):
                value = value.isoformat()
            result[column.name] = value
        return result


def init_db():
    """初始化数据库，创建所有表"""
    from sqlalchemy import create_engine, inspect, text
    from app.config import settings
    import os

    # 将 async sqlite URL 转换为 sync URL
    db_url = settings.DATABASE_URL
    if db_url.startswith("sqlite+aiosqlite"):
        db_url = db_url.replace("sqlite+aiosqlite:///", "sqlite:///")

    # 确保目录存在
    if db_url.startswith("sqlite:///"):
        db_path = db_url.replace("sqlite:///", "")
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

    engine = create_engine(db_url, echo=False)

    # 导入所有模型以确保它们注册到 Base
    import app.models.user  # noqa
    import app.models.expense  # noqa
    import app.models.rule  # noqa
    import app.models.idempotency  # noqa

    Base.metadata.create_all(bind=engine)

    # —— 迁移：为旧数据库补加缺失的列（幂等操作） ——
    _migrate_expense_columns(engine)
    _migrate_rule_columns(engine)

    return engine


def _migrate_expense_columns(engine):
    """为旧数据库补加缺失的列（幂等：存在则跳过）"""
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    if "expenses" not in insp.get_table_names():
        return

    existing_cols = {c["name"] for c in insp.get_columns("expenses")}

    with engine.connect() as conn:
        if "version" not in existing_cols:
            conn.execute(text(
                "ALTER TABLE expenses ADD COLUMN version INTEGER NOT NULL DEFAULT 1"
            ))
        if "ai_review_status" not in existing_cols:
            conn.execute(text(
                "ALTER TABLE expenses ADD COLUMN ai_review_status VARCHAR(20)"
            ))
        conn.commit()


def _migrate_rule_columns(engine):
    """为 rules 表补加 json-logic 相关列（幂等：存在则跳过）"""
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    if "rules" not in insp.get_table_names():
        return

    existing_cols = {c["name"] for c in insp.get_columns("rules")}

    with engine.connect() as conn:
        if "structured_condition" not in existing_cols:
            conn.execute(text(
                "ALTER TABLE rules ADD COLUMN structured_condition JSON"
            ))
        if "exec_mode" not in existing_cols:
            conn.execute(text(
                "ALTER TABLE rules ADD COLUMN exec_mode "
                "VARCHAR(20) NOT NULL DEFAULT 'semantic'"
            ))
        if "message" not in existing_cols:
            # 规则命中提示文案（可定制并落库）；旧行默认空串，读取时回退为
            # f"{name}不符合规则"
            conn.execute(text(
                "ALTER TABLE rules ADD COLUMN message VARCHAR(500) DEFAULT ''"
            ))
        conn.commit()
