"""
文档解析 Agent
使用 LLM 从 OCR 文本和发票信息中提取结构化的费用数据
"""
import json
import logging
from typing import Dict, Any

from app.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

DOCUMENT_AGENT_PROMPT = """你是一个专业的财务文档解析助手。你需要从发票、收据和其他财务文档的文本信息中提取结构化的费用数据。

请仔细分析提供的文档内容，提取以下信息：
1. 发票号码 - 发票的唯一标识号
2. 开票日期 - 费用发生的日期
3. 销售方名称 - 商家/供应商名称
4. 购买方名称 - 报销人/公司名称
5. 商品/服务明细 - 每一项的名称、数量、单价、金额
6. 总金额 - 发票总金额
7. 税额 - 增值税额
8. 发票类型 - 增值税专用发票、普通发票、收据等
9. 备注信息 - 发票上的备注

请以JSON格式返回提取结果。如果某个字段无法识别，请标注为 null。

注意事项：
- 金额统一转换为数字类型
- 日期格式统一为 YYYY-MM-DD
- 如果有多项商品，请以数组形式返回
- 请严格按照JSON格式返回结果，不要包含任何JSON之外的解释文字。
"""


class DocumentAgent(BaseAgent):
    """文档解析 Agent - 从 OCR/文档文本中提取结构化费用数据"""

    def __init__(self):
        super().__init__(
            name="DocumentAgent",
            system_prompt=DOCUMENT_AGENT_PROMPT,
            temperature=0.0,
        )

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析报销单中的文档信息

        Args:
            context: {
                "expense": Expense对象或字典,
                "document_texts": [{"filename": str, "content": str}, ...]
            }

        Returns:
            解析结果
        """
        self._start_timer()
        logger.info(f"[{self.name}] 开始解析文档...")

        try:
            expense = context.get("expense", {})
            document_texts = context.get("document_texts", [])

            if isinstance(expense, dict):
                expense_info = expense
            else:
                expense_info = {
                    "id": expense.id,
                    "title": expense.title,
                    "expense_type": expense.expense_type.value if hasattr(expense.expense_type, 'value') else expense.expense_type,
                    "total_amount": expense.total_amount,
                    "description": expense.description,
                }

            # 构建解析提示
            prompt = f"""报销单信息：
{json.dumps(expense_info, ensure_ascii=False, indent=2)}

需要解析的文档内容：
"""
            for doc in document_texts:
                prompt += f"\n--- 文件: {doc.get('filename', 'unknown')} ---\n"
                prompt += doc.get("content", "")[:3000]  # 限制长度

            prompt += "\n\n请提取所有发票和费用信息，以JSON格式返回。"

            # 调用LLM解析
            self.clear_memory()
            try:
                parsed_result = await self.chat_json(prompt)
            except ValueError as e:
                logger.warning(f"[{self.name}] JSON 解析失败，使用兜底: {e}")
                parsed_result = {"raw_response": str(e)}

            return self._build_result(
                status="success",
                result={
                    "extracted_data": parsed_result,
                    "document_count": len(document_texts),
                },
                message=f"成功解析 {len(document_texts)} 个文档",
            )

        except Exception as e:
            logger.error(f"[{self.name}] 解析失败: {e}", exc_info=True)
            return self._build_result(
                status="failed",
                result={"error": str(e), "extracted_data": {}},
                message=f"文档解析失败: {str(e)}",
            )
