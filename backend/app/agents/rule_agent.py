"""
规则校验 Agent
检查报销单是否符合数据库中的财务审核规则
"""
import json
import logging
from typing import Dict, Any, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base_agent import BaseAgent
from app.models.rule import Rule
from app.models.expense import ExpenseStatus

logger = logging.getLogger(__name__)

RULE_AGENT_PROMPT = """你是一个专业的财务规则审核助手。你需要根据提供的财务规则，对报销单进行合规性检查。

审核维度包括但不限于：
1. 金额限制 - 单笔/累计金额是否超出规定上限
2. 类别匹配 - 报销项目是否与费用类别匹配
3. 发票要求 - 是否有有效发票，发票信息是否完整
4. 时间合规 - 费用发生时间是否在允许范围内
5. 频次限制 - 同类报销是否过于频繁
6. 重复报销 - 是否存在同一发票重复报销
7. 政策合规 - 是否符合公司差旅/招待等政策

对于每项检查，请给出：
- 规则名称
- 检查结果: pass / warn / fail
- 违规原因（如果未通过）
- 风险等级: low / medium / high
- 建议处理方式

请以JSON格式返回检查结果。

请严格按照JSON格式返回结果，不要包含任何JSON之外的解释文字。"""


class RuleAgent(BaseAgent):
    """规则校验 Agent - 根据数据库中的规则检查报销单合规性"""

    def __init__(self, db: AsyncSession = None):
        super().__init__(
            name="RuleAgent",
            system_prompt=RULE_AGENT_PROMPT,
            temperature=0.0,
        )
        self.db = db

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行规则校验

        Args:
            context: {
                "expense": Expense对象或字典,
                "document_result": 文档解析结果,
                "user_info": 用户信息
            }

        Returns:
            规则校验结果
        """
        self._start_timer()
        logger.info(f"[{self.name}] 开始规则校验...")

        try:
            expense = context.get("expense", {})
            document_result = context.get("document_result", {})
            user_info = context.get("user_info", {})

            # 从数据库加载活跃规则
            active_rules = await self._load_rules()

            # 构建校验输入
            if isinstance(expense, dict):
                expense_info = expense
            else:
                expense_info = {
                    "id": expense.id,
                    "title": expense.title,
                    "expense_type": expense.expense_type.value if hasattr(expense.expense_type, 'value') else expense.expense_type,
                    "total_amount": expense.total_amount,
                    "currency": expense.currency,
                    "description": expense.description,
                    "items": [
                        {
                            "description": item.description,
                            "amount": item.amount,
                            "expense_date": str(item.expense_date) if item.expense_date else None,
                            "invoice_no": item.invoice_no,
                            "invoice_verified": item.invoice_verified,
                        }
                        for item in (expense.items if hasattr(expense, 'items') else expense.get("items", []))
                    ],
                }

            prompt = f"""当前报销单信息：
{json.dumps(expense_info, ensure_ascii=False, indent=2)}

适用规则列表：
{json.dumps(active_rules, ensure_ascii=False, indent=2)}

{self._build_user_context(user_info)}

文档解析结果（如有）：
{json.dumps(document_result, ensure_ascii=False, indent=2) if document_result else "无"}

请逐条检查报销单是否符合上述规则，并给出详细的检查报告。以JSON格式返回。"""

            # 调用LLM进行规则校验
            self.clear_memory()
            try:
                parsed = await self.chat_json(prompt)
            except ValueError as e:
                logger.warning(f"[{self.name}] JSON 解析失败，使用兜底: {e}")
                parsed = {"raw_response": str(e)}

            # 汇总规则检查结果
            summary = self._summarize_rules(parsed)

            return self._build_result(
                status="success",
                result={
                    "rule_checks": parsed,
                    "summary": summary,
                    "total_rules": len(active_rules),
                    "passed": summary.get("passed", 0),
                    "warnings": summary.get("warnings", 0),
                    "failed": summary.get("failed", 0),
                },
                message=f"规则校验完成: {summary.get('passed', 0)}通过, {summary.get('warnings', 0)}警告, {summary.get('failed', 0)}违规",
            )

        except Exception as e:
            logger.error(f"[{self.name}] 规则校验失败: {e}", exc_info=True)
            # 异常时無法确定违规情况，返回空结果，由编排层根据 has_severe_violation 判断
            return self._build_result(
                status="failed",
                result={
                    "error": str(e),
                    "rule_checks": {},
                    "summary": {"passed": 0, "warnings": 0, "failed": 0, "total_risk": "unknown"},
                    "total_rules": 0,
                    "passed": 0,
                    "warnings": 0,
                    "failed": 0,
                },
                message=f"规则校验失败，无法确定合规状态: {str(e)}",
            )

    async def _load_rules(self) -> List[dict]:
        """从数据库加载活跃规则"""
        if not self.db:
            return self._get_default_rules()

        try:
            result = await self.db.execute(
                select(Rule).where(Rule.is_active == True)
            )
            rules = result.scalars().all()
            return [
                {
                    "id": r.id,
                    "name": r.name,
                    "rule_type": r.rule_type.value if hasattr(r.rule_type, 'value') else r.rule_type,
                    "condition": r.condition,
                    "action": r.action,
                    "config": r.config,
                }
                for r in rules
            ]
        except Exception as e:
            logger.warning(f"加载规则失败，使用默认规则: {e}")
            return self._get_default_rules()

    def _get_default_rules(self) -> List[dict]:
        """获取默认审核规则"""
        return [
            {
                "id": 1,
                "name": "单笔金额上限",
                "rule_type": "amount_limit",
                "condition": "单笔报销金额不超过5000元",
                "action": "require_approval",
                "config": {"max_amount": 5000, "currency": "CNY"},
            },
            {
                "id": 2,
                "name": "必须有发票",
                "rule_type": "compliance",
                "condition": "所有报销项目必须提供有效发票",
                "action": "reject",
                "config": {"require_invoice": True},
            },
            {
                "id": 3,
                "name": "差旅费标准",
                "rule_type": "amount_limit",
                "condition": "差旅住宿费不超过500元/天，交通费不超过300元/天",
                "action": "warn",
                "config": {"hotel_max": 500, "transport_max": 300},
            },
            {
                "id": 4,
                "name": "招待费限制",
                "rule_type": "amount_limit",
                "condition": "单次招待费不超过2000元，需注明招待对象和事由",
                "action": "require_approval",
                "config": {"max_amount": 2000},
            },
            {
                "id": 5,
                "name": "发票时间",
                "rule_type": "time",
                "condition": "发票日期必须在3个月以内",
                "action": "warn",
                "config": {"max_age_days": 90},
            },
        ]

    def _build_user_context(self, user_info: dict) -> str:
        """构建用户上下文描述"""
        if not user_info:
            return ""

        parts = []
        if isinstance(user_info, dict):
            if user_info.get("department"):
                parts.append(f"所属部门: {user_info['department']}")
            if user_info.get("position"):
                parts.append(f"职位: {user_info['position']}")
            if user_info.get("role"):
                role = user_info['role']
                if hasattr(role, 'value'):
                    role = role.value
                parts.append(f"角色: {role}")

        if parts:
            return "\n用户信息：\n" + "\n".join(parts)
        return ""

    def _summarize_rules(self, parsed: dict) -> dict:
        """汇总规则检查结果"""
        summary = {"passed": 0, "warnings": 0, "failed": 0, "total_risk": "low"}

        checks = parsed.get("checks", parsed.get("rule_checks", []))
        if isinstance(checks, list):
            for check in checks:
                result = check.get("result", check.get("status", "")).lower()
                if result == "pass":
                    summary["passed"] += 1
                elif result == "warn":
                    summary["warnings"] += 1
                elif result == "fail":
                    summary["failed"] += 1

        # 综合风险等级
        if summary["failed"] > 2:
            summary["total_risk"] = "high"
        elif summary["failed"] > 0 or summary["warnings"] > 2:
            summary["total_risk"] = "medium"

        return summary
