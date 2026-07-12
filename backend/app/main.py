"""
FastAPI 应用入口
AI Agent 财务报销审核系统
"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.core.exceptions import register_exception_handlers

# 配置日志
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(settings.LOG_FILE, encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


# ========== 应用生命周期管理 ==========

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用启动和关闭时的生命周期管理

    启动时：初始化数据库和向量存储
    关闭时：清理资源
    """
    logger.info("=" * 50)
    logger.info(f"应用启动: {settings.APP_NAME}")
    logger.info(f"环境: {settings.APP_ENV}")
    logger.info(f"LLM模型: {settings.MODEL_NAME}")
    logger.info(f"Embedding模型: {settings.EMBEDDING_MODEL}")
    logger.info(f"调试模式: {settings.DEBUG}")
    logger.info("=" * 50)

    # 确保必要的目录存在
    data_dir = Path("./data")
    data_dir.mkdir(parents=True, exist_ok=True)

    chroma_dir = Path(settings.CHROMA_PERSIST_DIR)
    chroma_dir.mkdir(parents=True, exist_ok=True)

    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    log_dir = Path(settings.LOG_FILE).parent
    log_dir.mkdir(parents=True, exist_ok=True)

    # 启动时：初始化数据库
    await init_database()

    # 启动时：初始化向量存储和知识库
    await init_vectorstore()

    logger.info("应用启动完成，等待请求...")

    yield  # 应用运行期间

    # 关闭时清理
    logger.info("应用正在关闭...")


async def init_database():
    """初始化数据库 - 创建所有表"""
    try:
        from app.models.base import init_db

        engine = init_db()
        engine.dispose()

        logger.info("数据库表创建/检查完成")
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise


async def init_vectorstore():
    """初始化向量存储和知识库"""
    try:
        from app.rag.vectorstore import ChromaVectorStore
        from app.rag.knowledge_base import KnowledgeBaseManager

        vector_store = ChromaVectorStore()
        kb_manager = KnowledgeBaseManager(vector_store)
        doc_count = kb_manager.initialize_knowledge_base()

        logger.info(f"向量存储初始化完成，知识库文档数: {doc_count}")
    except Exception as e:
        logger.warning(f"向量存储初始化失败（非致命错误）: {e}")


# ========== 创建 FastAPI 应用 ==========

app = FastAPI(
    title=settings.APP_NAME,
    description="AI Agent 财务报销审核系统 - 基于 DeepSeek LLM 的智能报销审核平台",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ========== CORS 中间件 ==========

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== 注册异常处理器 ==========

register_exception_handlers(app)

# ========== 注册 API 路由 ==========

from app.api.v1.router import api_v1_router

app.include_router(api_v1_router)

# ========== 静态文件服务（上传文件访问） ==========

import os

uploads_dir = Path(settings.UPLOAD_DIR)
if uploads_dir.exists():
    try:
        app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")
    except Exception as e:
        logger.warning(f"静态文件挂载失败: {e}")


# ========== 健康检查端点 ==========

@app.get("/", tags=["系统"])
async def root():
    """根路由 - 服务状态检查"""
    return {
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "status": "running",
        "env": settings.APP_ENV,
        "llm_model": settings.MODEL_NAME,
        "embedding_model": settings.EMBEDDING_MODEL,
        "docs": "/docs",
    }


@app.get("/health", tags=["系统"])
async def health_check():
    """健康检查端点"""
    health_status = {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "environment": settings.APP_ENV,
        "llm_model": settings.MODEL_NAME,
        "embedding_model": settings.EMBEDDING_MODEL,
        "database": "unknown",
        "vectorstore": "unknown",
    }

    # 检查数据库连接
    try:
        from app.dependencies import engine
        async with engine.connect() as conn:
            from sqlalchemy import text
            await conn.execute(text("SELECT 1"))
        health_status["database"] = "connected"
    except Exception as e:
        health_status["database"] = f"error: {str(e)}"
        health_status["status"] = "degraded"

    # 检查向量存储
    try:
        from app.rag.vectorstore import ChromaVectorStore
        vector_store = ChromaVectorStore()
        stats = vector_store.get_collection_stats()
        health_status["vectorstore"] = f"connected ({stats.get('document_count', 0)} docs)"
    except Exception as e:
        health_status["vectorstore"] = f"unavailable: {str(e)}"

    return health_status


# ========== 启动入口 ==========

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
