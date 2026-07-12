"""
ChromaDB 向量存储管理
管理嵌入向量的存储和检索
"""
import logging
import os
from typing import List, Optional, Dict, Any

import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.utils import embedding_functions

from app.config import settings

logger = logging.getLogger(__name__)


class ChromaVectorStore:
    """
    ChromaDB 向量存储管理器

    提供文档的向量化存储和相似度检索功能
    """

    def __init__(self, collection_name: str = None):
        """
        初始化 ChromaDB 向量存储

        Args:
            collection_name: 集合名称，默认使用配置中的 CHROMA_COLLECTION
        """
        self.collection_name = collection_name or settings.CHROMA_COLLECTION
        self.persist_dir = settings.CHROMA_PERSIST_DIR

        # 确保持久化目录存在
        os.makedirs(self.persist_dir, exist_ok=True)

        # 初始化 ChromaDB 客户端
        self.client = chromadb.PersistentClient(
            path=self.persist_dir,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True,
            ),
        )

        self.collection = None
        logger.info(f"ChromaDB 初始化完成，持久化目录: {self.persist_dir}")

    def get_or_create_collection(self):
        """获取或创建集合"""
        if self.collection is None:
            try:
                self.collection = self.client.get_collection(
                    name=self.collection_name
                )
                logger.info(f"加载已有集合: {self.collection_name}")
            except Exception:
                self.collection = self.client.create_collection(
                    name=self.collection_name,
                    metadata={"description": "报销审核知识库"},
                )
                logger.info(f"创建新集合: {self.collection_name}")
        return self.collection

    def add_documents(
        self,
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
        embeddings: Optional[List[List[float]]] = None,
    ) -> List[str]:
        """
        添加文档到向量存储

        Args:
            documents: 文档文本列表
            metadatas: 元数据列表
            ids: 文档ID列表
            embeddings: 预计算的嵌入向量（可选）

        Returns:
            添加的文档ID列表
        """
        collection = self.get_or_create_collection()

        # 如果没有提供嵌入向量，使用 Chroma 默认的嵌入函数
        if ids is None:
            ids = [f"doc_{i}_{hash(doc) % 100000}" for i, doc in enumerate(documents)]

        try:
            if embeddings:
                collection.add(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids,
                    embeddings=embeddings,
                )
            else:
                collection.add(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids,
                )
            logger.info(f"成功添加 {len(documents)} 条文档到向量存储")
        except Exception as e:
            logger.error(f"添加文档失败: {e}")
            raise

        return ids

    def search(
        self,
        query: str,
        top_k: int = 5,
        where: Optional[Dict[str, Any]] = None,
        embeddings: Optional[List[float]] = None,
    ) -> List[Dict[str, Any]]:
        """
        相似度搜索

        Args:
            query: 查询文本
            top_k: 返回最相似的K条结果
            where: 元数据过滤条件
            embeddings: 查询的嵌入向量（可选）

        Returns:
            搜索结果列表，每项包含 id, content, metadata, distance
        """
        collection = self.get_or_create_collection()

        try:
            if embeddings:
                results = collection.query(
                    query_embeddings=[embeddings],
                    n_results=top_k,
                    where=where,
                )
            else:
                results = collection.query(
                    query_texts=[query],
                    n_results=top_k,
                    where=where,
                )

            # 格式化结果
            formatted = []
            if results.get("ids") and results["ids"][0]:
                for i in range(len(results["ids"][0])):
                    item = {
                        "id": results["ids"][0][i],
                        "content": results["documents"][0][i] if results.get("documents") else "",
                        "distance": results["distances"][0][i] if results.get("distances") else 0,
                        "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                    }
                    formatted.append(item)

            return formatted

        except Exception as e:
            logger.error(f"向量搜索失败: {e}")
            return []

    def delete_collection(self):
        """删除集合"""
        try:
            self.client.delete_collection(name=self.collection_name)
            self.collection = None
            logger.info(f"已删除集合: {self.collection_name}")
        except Exception as e:
            logger.warning(f"删除集合失败: {e}")

    def get_collection_stats(self) -> dict:
        """获取集合统计信息"""
        try:
            collection = self.get_or_create_collection()
            count = collection.count()
            return {
                "collection_name": self.collection_name,
                "document_count": count,
                "persist_dir": self.persist_dir,
            }
        except Exception as e:
            logger.warning(f"获取统计信息失败: {e}")
            return {"error": str(e)}

    def reset(self):
        """重置向量存储"""
        try:
            self.client.reset()
            self.collection = None
            logger.info("向量存储已重置")
        except Exception as e:
            logger.warning(f"重置失败: {e}")
