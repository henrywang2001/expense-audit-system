"""
决策 Agent
综合分析所有Agent的结果，给出最终的审批决策建议
"""
import json
import logging
from typing import Dict, Any

from app.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

DECISION_AGENT_PROMPT = """你是一个资深的财务审批决策顾问。你需要综合分析文档解析、规则校验、风险评估和知识检索的结果，给出最终的审批决策。

决策类型：
1. "approve" - 建议通过：报销合规，风险可控
2. "reject" - 建议拒绝：存在严重违规或高风险
3. "review" - 建议人工复核：存在疑点或中等风险，需要人工进一步审查

决策依据：
- 规则违规的数量和严重程度
- 风险评分和风险等级
- 历史相似案例的处理方式
- 相关法规和政策要求
- 公司财务制度的合规要求

在决策时，请给出：
- decision: 决策结果 (approve/reject/review)
- reason: 主要决策理由
- confidence: 置信度 (0-100)
- key_findings: 关键发现
- suggestions: 后续建议（如果通过需要关注什么，如果拒绝需要补充什么，如果需要复核需要重点核查什么）
- risk_mitigation: 风险缓释措施

请以JSON格式返回决策结果。"""


class DecisionAgent(BaseAgent):
    """决策 Agent - 综合所有分析结果做出最终审批决策"""

    def __init__(self):
        super().__init__(
            name="DecisionAgent",
            system_prompt=DECISION_AGENT_PROMPT,
            temperature=0.0,
        )

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行最终决策

        Args:
            context: {
                "expense": 报销单信息,
                "document_result": 文档解析结果,
                "rule_result": 规则校验结果,
                "risk_result": 风险评估结果,
                "rag_result": 知识检索结果,
                "user_info": 用户信息
            }

        Returns:
            决策结果
        """
        self._start_timer()
        logger.info(f"[{self.name}] 开始最终决策分析...")

        try:
            expense = context.get("expense", {})
            document_result = context.get("document_result", {})
            rule_result = context.get("rule_result", {})
            risk_result = context.get("risk_result", {})
            rag_result = context.get("rag_result", {})

            # 提取关键信息
            risk_level = risk_result.get("risk_level", "low")
            risk_score = risk_result.get("risk_score", 0)
            rule_checks = rule_result.get("rule_checks", {})
            rule_summary = rule_result.get("summary", {})

            # 构建决策输入
            prompt = f"""请基于以下综合分析结果给出审批决策建议：

===== 报销单信息 =====
{json.dumps(self._safe_serialize(expense), ensure_ascii=False, indent=2)}

===== 规则校验结果 =====
{json.dumps({
    "summary": rule_summary,
    "checks": self._summarize_checks(rule_checks),
}, ensure_ascii=False, indent=2)}

===== 风险评估结果 =====
{json.dumps({
    "risk_level": risk_level,
    "risk_score": risk_score,
    "dimension_scores": risk_result.get("dimension_scores", {}),
    "risk_factors": risk_result.get("risk_factors", []),
}, ensure_ascii=False, indent=2)}

===== 知识检索参考 =====
{json.dumps(self._summarize_rag(rag_result), ensure_ascii=False, indent=2)}

请给出最终审批决策建议。"""

            self.clear_memory()
            response = await self.chat(prompt)

            # 解析决策结果
            try:
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    decision = json.loads(response[json_start:json_end])
                else:
                    decision = {"raw_response": response}
            except json.JSONDecodeError:
                decision = {"raw_response": response}

            # 如果LLM没有给出决策，基于规则计算
            if "decision" not in decision:
                decision = self._fallback_decision(risk_level, risk_score, rule_summary)

            return self._build_result(
                status="success",
                result=decision,
                message=f"决策完成: {decision.get('decision', 'unknown')}",
            )

        except Exception as e:
            logger.error(f"[{self.name}] 决策分析失败: {e}", exc_info=True)
            return self._build_result(
                status="failed",
                result={
                    "decision": "review",
                    "reason": f"决策分析异常: {str(e)}",
                    "confidence": 0,
                },
                message=f"决策分析失败: {str(e)}",
            )

    def _safe_serialize(self, obj) -> dict:
        """安全序列化对象"""
        if isinstance(obj, dict):
            return {k: self._safe_serialize(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._safe_serialize(item) for item in obj]
        elif obj is None:
            return None
        elif hasattr(obj, '__dict__'):
            result = {}
            for key, value in obj.__dict__.items():
                if not key.startswith('_'):
                    result[key] = self._safe_serialize(value)
            return result
        elif hasattr(obj, 'value'):
            return obj.value
        return str(obj)

    def _summarize_checks(self, rule_checks: dict) -> dict:
        """简化规则检查结果"""
        if isinstance(rule_checks, dict):
            checks = rule_checks.get("checks", rule_checks.get("rule_checks", []))
            if isinstance(checks, list):
                simplified = []
                for check in checks:
                    simplified.append({
                        "name": check.get("name", check.get("rule", "")),
                        "result": check.get("result", check.get("status", "")),
                        "reason": check.get("reason", check.get("message", "")),
                    })
                return {"checks": simplified, "total": len(simplified)}
        return rule_checks

    def _summarize_rag(self, rag_result: dict) -> dict:
        """简化知识检索结果"""
        return {
            "retrieved_count": rag_result.get("retrieved_count", 0),
            "summary": rag_result.get("knowledge_summary", {}),
        }

    def _fallback_decision(
        self, risk_level: str, risk_score: float, rule_summary: dict
    ) -> dict:
        """基于简单规则的兜底决策"""
        failed = rule_summary.get("failed", 0) if rule_summary else 0
        warnings = rule_summary.get("warnings", 0) if rule_summary else 0

        if risk_level == "critical" or risk_score > 80 or failed >= 2:
            return {
                "decision": "reject",
                "reason": f"风险等级{risk_level}, 风险评分{risk_score}, {failed}项规则违规",
                "confidence": 85,
                "key_findings": [f"{failed}项规则违规", f"风险评分{risk_score}"],
            }
        elif risk_level == "high" or risk_score > 60 or failed > 0:
            return {
                "decision": "review",
                "reason": f"风险等级{risk_level}, 存在{failed}项违规和{warnings}项警告",
                "confidence": 70,
                "key_findings": [f"{failed}项规则违规", "需要人工复核"],
            }
        elif warnings > 0 or risk_score > 20:
            return {
                "decision": "approve",
                "reason": f"基本合规，{warnings}项提醒事项",
                "confidence": 80,
                "key_findings": [f"{warnings}项提醒事项"],
            }
        else:
            return {
                "decision": "approve",
                "reason": "报销合规，无风险",
                "confidence": 95,
                "key_findings": ["所有检查通过"],
            }
