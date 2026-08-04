"""
风险评估 Agent
对报销单进行多维度风险评分
"""
import json
import logging
from typing import Dict, Any

from app.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

RISK_AGENT_PROMPT = """你是一个专业的财务风险评估分析师。你需要对报销单从多个维度进行风险评估。

评估维度及权重：
1. 金额异常 (25%) - 金额是否显著高于同类报销的历史平均水平
2. 频率异常 (20%) - 同类报销是否过于频繁
3. 时间异常 (15%) - 报销时间是否在非工作日/节假日
4. 合规风险 (20%) - 是否符合公司财务制度和法规要求
5. 发票风险 (10%) - 发票真伪、完整性、连号等
6. 行为模式 (10%) - 报销行为是否符合申请人历史模式

评分标准：
- 0-20分: 低风险 (正常报销)
- 21-40分: 中低风险 (建议关注)
- 41-60分: 中等风险 (需要仔细审核)
- 61-80分: 高风险 (需要重点审查)
- 81-100分: 极高风险 (建议拒绝)

请以JSON格式返回评估结果，包含：
- overall_score: 综合风险分数 (0-100)
- risk_level: 风险等级 (low/medium/high/critical)
- dimension_scores: 各维度评分
- risk_factors: 识别到的风险因素列表
- recommendations: 建议措施列表

请严格按照JSON格式返回结果，不要包含任何JSON之外的解释文字。"""


class RiskAgent(BaseAgent):
    """风险评估 Agent - 多维度风险评分"""

    def __init__(self):
        super().__init__(
            name="RiskAgent",
            system_prompt=RISK_AGENT_PROMPT,
            temperature=0.0,
        )

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行风险评估

        Args:
            context: {
                "expense": Expense对象或字典,
                "rule_result": 规则校验结果,
                "document_result": 文档解析结果,
                "user_info": 用户信息,
                "history": 用户历史报销记录
            }

        Returns:
            风险评估结果
        """
        self._start_timer()
        logger.info(f"[{self.name}] 开始风险评估...")

        try:
            expense = context.get("expense", {})
            rule_result = context.get("rule_result", {})
            document_result = context.get("document_result", {})
            user_info = context.get("user_info", {})
            history = context.get("history", [])

            # 构建评估输入
            if isinstance(expense, dict):
                expense_info = expense
            else:
                expense_info = {
                    "id": expense.id,
                    "title": expense.title,
                    "expense_type": expense.expense_type.value if hasattr(expense.expense_type, 'value') else expense.expense_type,
                    "total_amount": expense.total_amount,
                    "description": expense.description,
                    "status": expense.status.value if hasattr(expense.status, 'value') else expense.status,
                }

            prompt = f"""报销单信息：
{json.dumps(expense_info, ensure_ascii=False, indent=2)}

规则校验结果：
{json.dumps(rule_result, ensure_ascii=False, indent=2)}

用户信息：
{json.dumps(user_info, ensure_ascii=False, indent=2)}

历史报销记录（最近10条）：
{json.dumps(history[:10], ensure_ascii=False, indent=2) if history else "无历史记录"}

请对上述报销单进行全面的风险评估，按评分标准给出各维度评分和综合结论。"""

            self.clear_memory()
            try:
                parsed = await self.chat_json(prompt)
            except ValueError as e:
                logger.warning(f"[{self.name}] JSON 解析失败，使用兜底: {e}")
                parsed = {"raw_response": str(e)}

            # 提取风险等级和分数
            risk_level = parsed.get("risk_level", "low")
            risk_score = parsed.get("overall_score", 0)

            # 标准化风险等级
            if isinstance(risk_score, (int, float)):
                if risk_score <= 20:
                    risk_level = "low"
                elif risk_score <= 40:
                    risk_level = "medium"
                elif risk_score <= 60:
                    risk_level = "medium"
                elif risk_score <= 80:
                    risk_level = "high"
                else:
                    risk_level = "critical"

            return self._build_result(
                status="success",
                result={
                    "risk_level": risk_level,
                    "risk_score": risk_score,
                    "dimension_scores": parsed.get("dimension_scores", {}),
                    "risk_factors": parsed.get("risk_factors", []),
                    "recommendations": parsed.get("recommendations", []),
                    "full_analysis": parsed,
                },
                message=f"风险评估完成: 等级={risk_level}, 分数={risk_score}",
            )

        except Exception as e:
            logger.error(f"[{self.name}] 风险评估失败: {e}", exc_info=True)
            # fail-closed: 异常当最高风险，不低估风险
            return self._build_result(
                status="failed",
                result={
                    "error": str(e),
                    "risk_level": "critical",
                    "risk_score": 100,
                    "dimension_scores": {},
                    "risk_factors": [f"风险评估系统异常，自动标记为高风险需人工复核: {str(e)}"],
                    "recommendations": ["系统异常，建议人工逐一复核所有风险维度"],
                    "full_analysis": {},
                },
                message=f"风险评估异常(已标记为critical): {str(e)}",
            )
