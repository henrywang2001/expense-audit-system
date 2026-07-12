"""
RAG 知识检索 Agent
检索相似的历史案例、相关财务规则和政策文档
"""
import json
import logging
from typing import Dict, Any, List, Optional

from app.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

RAG_AGENT_PROMPT = """你是一个知识检索助手，专门帮助检索与财务报销审核相关的信息和案例。

你的任务是：
1. 分析当前报销单的关键特征
2. 检索相似的历史报销案例
3. 查找适用的财务规则和政策
4. 提供相关法规和合规要求参考
5. 总结对当前报销单审核有参考价值的信息

请以JSON格式返回检索和总结的结果。"""


class RAGAgent(BaseAgent):
    """RAG 检索 Agent - 检索相似案例和知识"""

    def __init__(self, retriever=None):
        super().__init__(
            name="RAGAgent",
            system_prompt=RAG_AGENT_PROMPT,
            temperature=0.1,
        )
        self.retriever = retriever

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行知识检索

        Args:
            context: {
                "expense": Expense对象或字典,
                "query": 查询文本（可选，默认从expense构建）,
                "top_k": 返回结果数量
            }

        Returns:
            检索和总结结果
        """
        self._start_timer()
        logger.info(f"[{self.name}] 开始知识检索...")

        try:
            expense = context.get("expense", {})
            top_k = context.get("top_k", 5)

            # 构建查询文本
            if isinstance(expense, dict):
                query = context.get("query", "")
                if not query:
                    query = f"报销类型: {expense.get('expense_type', '')}, 金额: {expense.get('total_amount', 0)}, 描述: {expense.get('description', '')}"
            else:
                query = context.get("query", "")
                if not query:
                    query = f"报销类型: {expense.expense_type.value if hasattr(expense.expense_type, 'value') else expense.expense_type}, 金额: {expense.total_amount}, 描述: {expense.description or ''}"

            # 从向量数据库检索相关文档
            retrieved_docs = await self._retrieve_documents(query, top_k)

            # 加载知识库内容
            knowledge_texts = await self._load_knowledge(expense)

            # 用LLM总结检索结果
            if retrieved_docs or knowledge_texts:
                prompt = f"""查询内容：{query}

检索到的相似案例/规则：
{json.dumps(retrieved_docs, ensure_ascii=False, indent=2)}

相关知识库内容：
{chr(10).join(knowledge_texts[:5]) if knowledge_texts else '无'}

请总结这些信息对当前报销单审核的参考价值，以JSON格式返回。"""
                self.clear_memory()
                response = await self.chat(prompt)

                try:
                    json_start = response.find("{")
                    json_end = response.rfind("}") + 1
                    if json_start >= 0 and json_end > json_start:
                        summary = json.loads(response[json_start:json_end])
                    else:
                        summary = {"raw_response": response}
                except json.JSONDecodeError:
                    summary = {"raw_response": response}
            else:
                summary = {"note": "知识库暂无相关内容"}

            return self._build_result(
                status="success",
                result={
                    "retrieved_count": len(retrieved_docs),
                    "retrieved_docs": retrieved_docs,
                    "knowledge_summary": summary,
                },
                message=f"检索到 {len(retrieved_docs)} 条相关记录",
            )

        except Exception as e:
            logger.error(f"[{self.name}] 知识检索失败: {e}", exc_info=True)
            return self._build_result(
                status="failed",
                result={"error": str(e), "retrieved_docs": []},
                message=f"知识检索失败: {str(e)}",
            )

    async def _retrieve_documents(
        self, query: str, top_k: int = 5
    ) -> List[dict]:
        """从向量数据库检索文档"""
        docs = []
        try:
            if self.retriever:
                results = await self.retriever.search(query, top_k=top_k)
                for doc in results:
                    docs.append({
                        "content": doc.get("content", doc.get("text", "")),
                        "score": doc.get("score", doc.get("distance", 0)),
                        "metadata": doc.get("metadata", {}),
                    })
        except Exception as e:
            logger.warning(f"向量检索失败: {e}")

        return docs

    async def _load_knowledge(self, expense) -> List[str]:
        """加载知识库文本"""
        texts = []

        # 加载默认的财务知识
        expense_type = ""
        if isinstance(expense, dict):
            expense_type = expense.get("expense_type", "")
        else:
            expense_type = expense.expense_type.value if hasattr(expense.expense_type, 'value') else str(expense.expense_type)

        knowledge_base = {
            "travel": [
                "差旅费报销标准：国内出差住宿费一线城市不超过500元/天，其他城市不超过350元/天",
                "差旅交通费：高铁二等座、飞机经济舱为标准等级",
                "出差补贴：一线城市100元/天，其他城市80元/天",
                "需提供行程单、住宿发票、交通票据作为报销凭证",
            ],
            "entertainment": [
                "招待费需提前申请，单次标准不超过人均200元",
                "招待对象、事由、参与人员需在报销单中明确列出",
                "严禁以招待费名义报销个人消费",
                "单次招待费超过2000元需部门负责人和财务双重审批",
            ],
            "office": [
                "办公用品采购需走公司统一采购流程",
                "单价超过500元的设备需走固定资产登记",
                "办公耗材月度预算不超过部门人数*50元",
            ],
        }

        category = knowledge_base.get(expense_type, [])
        texts.extend(category)
        texts.extend([
            "所有报销单必须附有正规发票，发票信息需与国家税务系统一致",
            "报销单提交后需在3个工作日内完成审批",
            "单笔报销金额超过5000元需要部门经理审批",
            "同一发票不得重复报销，系统会自动检测重复发票号",
        ])

        return texts
