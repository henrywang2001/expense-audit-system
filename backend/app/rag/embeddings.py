"""
自定义 Embedding 类
使用千问 DashScope API (OpenAI 兼容接口) 进行文本向量化
"""
import logging
from typing import List, Optional

from langchain_openai import OpenAIEmbeddings

from app.config import settings

logger = logging.getLogger(__name__)


def create_embeddings() -> OpenAIEmbeddings:
    """
    创建千问 Embedding 实例

    使用 DashScope 的 OpenAI 兼容 API 接口

    Returns:
        OpenAIEmbeddings 实例，配置为千问 text-embedding-v1
    """
    logger.info(f"创建 Embedding 实例: model={settings.EMBEDDING_MODEL}")

    embeddings = OpenAIEmbeddings(
        model=settings.EMBEDDING_MODEL,
        openai_api_key=settings.DASHSCOPE_API_KEY,
        openai_api_base=settings.DASHSCOPE_API_BASE,
        # 千问 embedding 维度为 1536
        dimensions=1536,
    )

    return embeddings


class DashScopeEmbeddings:
    """
    千问 Embedding 封装类

    提供 embed_documents 和 embed_query 接口，
    与 LangChain Chroma 集成
    """

    def __init__(self):
        self._embeddings = create_embeddings()
        self.model = settings.EMBEDDING_MODEL

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        批量文本向量化

        Args:
            texts: 文本列表

        Returns:
            向量列表
        """
        try:
            vectors = self._embeddings.embed_documents(texts)
            logger.info(f"成功向量化 {len(texts)} 条文本")
            return vectors
        except Exception as e:
            logger.error(f"文本向量化失败: {e}")
            raise

    def embed_query(self, text: str) -> List[float]:
        """
        查询文本向量化

        Args:
            text: 查询文本

        Returns:
            向量
        """
        try:
            vector = self._embeddings.embed_query(text)
            return vector
        except Exception as e:
            logger.error(f"查询向量化失败: {e}")
            raise

    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        """异步批量文本向量化"""
        try:
            vectors = await self._embeddings.aembed_documents(texts)
            return vectors
        except Exception as e:
            logger.error(f"异步文本向量化失败: {e}")
            # 回退到同步方法
            return self.embed_documents(texts)

    async def aembed_query(self, text: str) -> List[float]:
        """异步查询文本向量化"""
        try:
            vector = await self._embeddings.aembed_query(text)
            return vector
        except Exception as e:
            logger.error(f"异步查询向量化失败: {e}")
            return self.embed_query(text)
