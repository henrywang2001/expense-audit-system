"""
RAG 检索器
提供混合检索功能，结合向量相似度搜索和关键词匹配
"""
import logging
import re
from typing import List, Dict, Any, Optional

from app.rag.embeddings import DashScopeEmbeddings
from app.rag.vectorstore import ChromaVectorStore

logger = logging.getLogger(__name__)


class HybridRetriever:
    """
    混合检索器

    结合向量相似度检索和BM25关键词检索，
    提供更准确的检索结果
    """

    def __init__(self, vector_store: ChromaVectorStore = None):
        """
        初始化检索器

        Args:
            vector_store: ChromaDB 向量存储实例
        """
        self.vector_store = vector_store or ChromaVectorStore()
        self.embeddings = DashScopeEmbeddings()

    async def search(
        self,
        query: str,
        top_k: int = 5,
        alpha: float = 0.7,
        filter_metadata: Optional[Dict[str, Any]] = None,
        use_keyword_search: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        混合检索

        Args:
            query: 查询文本
            top_k: 返回结果数量
            alpha: 向量搜索权重 (0-1)，1表示仅用向量搜索，0表示仅用关键词搜索
            filter_metadata: 元数据过滤条件
            use_keyword_search: 是否启用关键词搜索

        Returns:
            排序后的检索结果列表
        """
        results = []

        # 1. 向量语义搜索
        try:
            query_embedding = await self.embeddings.aembed_query(query)
            vector_results = self.vector_store.search(
                query=query,
                top_k=top_k * 2,  # 获取更多候选
                embeddings=query_embedding,
                where=filter_metadata,
            )

            # 为每个结果添加向量分数
            for item in vector_results:
                item["vector_score"] = 1.0 - item.get("distance", 0)
                item["source"] = "vector"

            results.extend(vector_results)
            logger.debug(f"向量检索返回 {len(vector_results)} 条结果")

        except Exception as e:
            logger.warning(f"向量检索失败: {e}")

        # 2. 关键词匹配搜索
        if use_keyword_search:
            try:
                keyword_results = self._keyword_search(query, top_k)
                for item in keyword_results:
                    item["keyword_score"] = item.get("score", 0)
                    item["source"] = "keyword"

                results.extend(keyword_results)
                logger.debug(f"关键词检索返回 {len(keyword_results)} 条结果")

            except Exception as e:
                logger.warning(f"关键词检索失败: {e}")

        # 3. 结果融合和去重
        merged = self._merge_results(results, alpha)
        return merged[:top_k]

    def _keyword_search(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """
        基于关键词的搜索

        使用简单的 TF-IDF 风格关键词匹配
        """
        # 提取中文/英文关键词
        keywords = self._extract_keywords(query)

        # 从向量存储获取所有文档进行关键词匹配
        all_docs = []
        try:
            # 使用一个宽泛的查询获取更多文档
            all_results = self.vector_store.search(query=query, top_k=50)
            all_docs = all_results
        except Exception:
            pass

        scored_results = []
        for doc in all_docs:
            content = doc.get("content", "")
            if not content:
                continue

            # 计算关键词匹配分数
            score = 0
            for keyword in keywords:
                # 精确匹配
                count = len(re.findall(re.escape(keyword), content, re.IGNORECASE))
                score += count * 2

                # 部分匹配
                for word in content:
                    if keyword in word:
                        score += 0.5

            if score > 0:
                scored_results.append({
                    **doc,
                    "score": min(score / 10, 1.0),  # 归一化分数
                })

        # 按分数排序
        scored_results.sort(key=lambda x: x.get("score", 0), reverse=True)
        return scored_results[:top_k]

    def _extract_keywords(self, text: str) -> List[str]:
        """提取查询文本中的关键词"""
        keywords = []

        # 提取中文关键词（按常见分隔符分词）
        # 简单的基于字符和常见分隔的分词
        segments = re.split(r'[，。；！？、\s,;!?\n]+', text)
        for seg in segments:
            seg = seg.strip()
            if len(seg) >= 2:  # 至少2个字符
                keywords.append(seg)

        # 提取英文单词
        english_words = re.findall(r'[a-zA-Z]{2,}', text)
        keywords.extend(english_words)

        # 提取数字相关
        numbers = re.findall(r'\d+', text)
        keywords.extend(numbers)

        # 去重
        seen = set()
        unique_keywords = []
        for kw in keywords:
            if kw.lower() not in seen:
                seen.add(kw.lower())
                unique_keywords.append(kw)

        return unique_keywords[:20]  # 限制关键词数量

    def _merge_results(
        self, results: List[Dict[str, Any]], alpha: float
    ) -> List[Dict[str, Any]]:
        """
        合并和去重检索结果

        Args:
            results: 所有检索结果
            alpha: 向量搜索权重

        Returns:
            排序后的合并结果
        """
        # 按ID去重，融合分数
        merged = {}
        for item in results:
            item_id = item.get("id", item.get("content", ""))
            if item_id not in merged:
                merged[item_id] = item
                # 计算综合分数
                vector_score = item.get("vector_score", 0)
                keyword_score = item.get("keyword_score", 0)
                item["combined_score"] = alpha * vector_score + (1 - alpha) * keyword_score
            else:
                # 合并分数
                existing = merged[item_id]
                vector_score = max(item.get("vector_score", 0), existing.get("vector_score", 0))
                keyword_score = max(item.get("keyword_score", 0), existing.get("keyword_score", 0))
                existing["vector_score"] = vector_score
                existing["keyword_score"] = keyword_score
                existing["combined_score"] = alpha * vector_score + (1 - alpha) * keyword_score
                existing["source"] = "hybrid"

        # 按综合分数排序
        sorted_results = sorted(
            merged.values(),
            key=lambda x: x.get("combined_score", 0),
            reverse=True,
        )

        return sorted_results

    async def add_documents(
        self,
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
    ) -> List[str]:
        """添加文档到检索器"""
        return self.vector_store.add_documents(
            documents=documents,
            metadatas=metadatas,
        )

    def get_stats(self) -> dict:
        """获取检索器统计信息"""
        return {
            **self.vector_store.get_collection_stats(),
            "retriever_type": "hybrid",
        }
