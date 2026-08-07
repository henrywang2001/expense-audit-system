"""
规则校验 Agent
检查报销单是否符合数据库中的财务审核规则

v2 (json-logic): 规则校验分两阶段
  阶段1 — 确定性引擎 (RuleEngine, 零次 LLM): 硬规则 + 半硬规则
  阶段2 — LLM 语义补充 (可选): 仅当存在 exec_mode=semantic 的规则时调用
"""
import json
import logging
from typing import Dict, Any, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base_agent import BaseAgent
from app.models.rule import Rule, RuleType
from app.models.expense import ExpenseStatus
from app.schemas.rule import RuleDef
from app.core.rule_engine import (
    RuleEngine, build_data, validate_rule_ast,
    summarize_checks, RuleError,
)

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
        执行规则校验（确定性引擎 + LLM 语义补充）

        Args:
            context: {
                "expense": Expense对象或字典,
                "document_result": 文档解析结果,
                "user_info": 用户信息,
                "custom": 自定义规则列表 (修复静默丢弃)
            }
        """
        self._start_timer()
        logger.info(f"[{self.name}] 开始规则校验 (json-logic 确定性引擎)...")

        try:
            expense = context.get("expense", {})
            document_result = context.get("document_result", {})
            user_info = context.get("user_info", {})
            custom_rules_raw = context.get("custom", []) or []  # ★ 修复静默丢弃

            # ── 阶段1: 数据准备 ──
            data = build_data(expense, user_info)

            # ── 阶段2: 加载规则 (DB + 默认 + custom) ──
            all_rules = await self._load_rules(custom_rules_raw)

            # 分流: 确定规则走引擎, 语义规则留给 LLM
            hard_rules = [r for r in all_rules if r.exec_mode != "semantic"]
            semantic_rules = [r for r in all_rules if r.exec_mode == "semantic"]

            # ── 阶段3: 确定性引擎求值 (零次 LLM) ──
            engine = RuleEngine(hard_rules)
            checks = engine.evaluate(data)

            # ── 阶段4: LLM 语义补充 (仅当有语义规则时才调 LLM) ──
            if semantic_rules:
                semantic_checks = await self._evaluate_semantic(
                    data, semantic_rules, expense, document_result, user_info
                )
                checks += semantic_checks

            # ── 汇总 ──
            summary = summarize_checks(checks)

            return self._build_result(
                status="success",
                result={
                    "rule_checks": checks,
                    "summary": summary,
                    "total_rules": len(all_rules),
                    "engine_rules": len(hard_rules),
                    "semantic_rules": len(semantic_rules),
                    "passed": summary.get("passed", 0),
                    "warnings": summary.get("warnings", 0),
                    "failed": summary.get("failed", 0),
                },
                message=(
                    f"规则校验完成: {summary.get('passed', 0)}通过, "
                    f"{summary.get('warnings', 0)}警告, "
                    f"{summary.get('failed', 0)}违规"
                    + (f", {summary.get('errors', 0)}异常"
                       if summary.get("errors", 0) else "")
                ),
            )

        except Exception as e:
            logger.error(f"[{self.name}] 规则校验失败: {e}", exc_info=True)
            return self._build_result(
                status="failed",
                result={
                    "error": str(e),
                    "rule_checks": [],
                    "summary": {"passed": 0, "warnings": 0,
                                "failed": 0, "errors": 1, "total_risk": "high"},
                    "total_rules": 0,
                    "passed": 0, "warnings": 0, "failed": 0,
                },
                message=f"规则校验失败，无法确定合规状态: {str(e)}",
            )

    async def _load_rules(
        self, custom_rules_raw: list | None = None
    ) -> List[RuleDef]:
        """加载活跃规则: DB 优先 → 默认规则兜底 → 合并自定义规则

        优先使用 DB 中 structured_condition 不为空的规则（确定性引擎可执行）;
        若 DB 中 structured_condition 为空, 退化到默认规则。
        """
        rules: List[RuleDef] = []

        # ① 从数据库加载
        if self.db:
            try:
                result = await self.db.execute(
                    select(Rule).where(Rule.is_active == True)
                )
                db_rules = result.scalars().all()

                for r in db_rules:
                    sc = r.structured_condition  # json-logic 对象
                    if sc and isinstance(sc, dict) and sc != {}:
                        # 有可执行的 json-logic
                        rules.append(RuleDef(
                            name=r.name,
                            rule_type=(
                                r.rule_type.value
                                if hasattr(r.rule_type, "value")
                                else str(r.rule_type)
                            ),
                            logic=sc,
                            action=r.action,
                            message=self._rule_message(r),
                            description=r.condition,  # 原文作人类可读描述
                            exec_mode=getattr(r, "exec_mode", "deterministic") or "deterministic",
                        ))
                    else:
                        # structured_condition 空 → 该行仍走 LLM
                        rules.append(RuleDef(
                            name=r.name,
                            rule_type=(
                                r.rule_type.value
                                if hasattr(r.rule_type, "value")
                                else str(r.rule_type)
                            ),
                            logic={},
                            action=r.action,
                            message=self._rule_message(r),
                            description=r.condition,
                            exec_mode="semantic",
                        ))

                if rules:
                    logger.info(f"从 DB 加载 {len(rules)} 条规则")
            except Exception as e:
                logger.warning(f"加载 DB 规则失败: {e}")

        # ② DB 无规则或无结构化规则 → 用默认规则
        deterministic_count = sum(1 for r in rules if r.exec_mode != "semantic")
        if deterministic_count == 0:
            logger.info("DB 无确定性规则, 使用默认 5 条 json-logic 规则")
            rules = self._get_default_rules() + [
                r for r in rules if r.exec_mode == "semantic"
            ]

        # ③ 合并自定义规则 ★ 修复静默丢弃
        for cr in (custom_rules_raw or []):
            if isinstance(cr, dict) and cr.get("logic"):
                try:
                    logic = cr["logic"]
                    # 安全检查: 只允许白名单字段和运算符
                    if cr.get("_skip_validation"):
                        pass  # 内部注入的规则可跳过
                    else:
                        validate_rule_ast(logic)
                    rules.append(RuleDef(
                        name=cr.get("name", "自定义规则"),
                        rule_type=cr.get("rule_type", "custom"),
                        logic=logic,
                        action=cr.get("action", "warn"),
                        message=cr.get("message", "自定义规则触发"),
                        description=cr.get("description"),
                        exec_mode=cr.get("exec_mode", "deterministic"),
                    ))
                except RuleError as e:
                    logger.warning(f"自定义规则校验不通过, 跳过: {cr.get('name')}: {e}")
                except Exception as e:
                    logger.warning(f"自定义规则解析失败, 跳过: {e}")

        return rules

    @staticmethod
    def _rule_message(rule: Rule) -> str:
        """取规则命中文案：优先库中自定义 message，为空则回退默认文案。

        与 ``app/api/v1/rule.py::_resolve_rule_message`` 保持一致语义，
        保证「规则管理页展示的文案」与「AI 审核实际输出的文案」一致。
        """
        custom = getattr(rule, "message", None)
        if custom and str(custom).strip():
            return str(custom)
        return f"{rule.name}不符合规则"

    @staticmethod
    def _build_user_context(user_info: Dict[str, Any] | None) -> str:
        """构造提交人上下文片段，供语义规则 prompt 使用。

        缺少用户信息时返回空提示串，避免 prompt 出现 ``None`` 字面量。

        Args:
            user_info: 形如 {"full_name": ..., "department": ...,
                            "position": ..., "role": ...} 的用户信息字典

        Returns:
            可直接嵌入 prompt 的中文上下文段落
        """
        if not user_info or not isinstance(user_info, dict):
            return "提交人信息：未提供。"

        field_labels = (
            ("full_name", "姓名"),
            ("username", "账号"),
            ("department", "部门"),
            ("position", "职位"),
            ("role", "角色"),
        )
        parts = [
            f"{label}: {user_info.get(key)}"
            for key, label in field_labels
            if user_info.get(key)
        ]
        if not parts:
            return "提交人信息：未提供。"
        return "提交人信息：\n" + "\n".join(f"- {p}" for p in parts)

    def _get_default_rules(self) -> List[RuleDef]:
        """获取默认审核规则 (json-logic 形式, 兼容 maykin-json-logic-py)"""
        return [
            RuleDef(
                name="单笔金额上限", rule_type="amount_limit",
                logic={"<=": [{"var": "total_amount"}, 5000]},
                action="require_approval",
                message="单笔报销金额超过 5000 元，需上级审批",
                description="单笔报销金额不超过5000元",
            ),
            RuleDef(
                name="必须有发票", rule_type="compliance",
                logic={"!": [{"var": "has_unverified_invoice"}]},
                action="reject",
                message="存在未验证发票的明细项",
                description="所有报销项目必须提供有效发票",
            ),
            RuleDef(
                name="差旅费标准", rule_type="amount_limit",
                logic={
                    "_kind": "every", "_array": "items",
                    "_item_rule": {"<=": [{"var": "amount"}, 500]},
                },
                action="warn",
                message="差旅住宿费/交通费超出标准",
                description="差旅住宿费不超过500元/天，交通费不超过300元/天",
            ),
            RuleDef(
                name="招待费限制", rule_type="amount_limit",
                logic={"<=": [{"var": "total_amount"}, 2000]},
                action="require_approval",
                message="单次招待费超过2000元，需注明对象与事由",
                description="单次招待费不超过2000元",
            ),
            RuleDef(
                name="发票时间", rule_type="time",
                logic={"<=": [{"var": "max_invoice_age_days"}, 90]},
                action="warn",
                message="存在超过3个月的发票",
                description="发票日期必须在3个月以内",
            ),
        ]

    async def _evaluate_semantic(
        self, data: dict, semantic_rules: List[RuleDef],
        expense, document_result: dict, user_info: dict,
    ) -> List[dict]:
        """LLM 语义规则补充判断 — 仅当存在 exec_mode=semantic 的规则时才调用"""
        if not semantic_rules:
            return []

        expense_info = data  # build_data 已转为纯 dict

        prompt = f"""你是一个专业的财务规则审核助手。以下报销单已经通过了确定性规则引擎的检查,
但仍有一些需要语义判断的规则需要你审核。

当前报销单信息：
{json.dumps(expense_info, ensure_ascii=False, indent=2, default=str)}

需要语义判断的规则：
{json.dumps([{"name": r.name, "description": r.description, "action": r.action}
             for r in semantic_rules], ensure_ascii=False, indent=2)}

{self._build_user_context(user_info)}

请逐条判断, 返回 JSON 格式:
{{"checks": [{{"rule": "规则名", "result": "pass"|"warn"|"fail", "reason": "判断依据"}}]}}"""

        self.clear_memory()
        try:
            parsed = await self.chat_json(prompt)
        except ValueError as e:
            logger.warning(f"[{self.name}] 语义规则 LLM 解析失败: {e}")
            # 兜底: 全部标记为 warn
            return [
                {"rule": r.name, "status": "warn",
                 "action": r.action,
                 "message": f"{r.message} [LLM异常, 默认warn]"}
                for r in semantic_rules
            ]

        checks_raw = parsed.get("checks", [])
        result = []
        for sr in semantic_rules:
            matched = next(
                (c for c in checks_raw if c.get("rule") == sr.name), None
            )
            if matched:
                raw_result = (matched.get("result") or "").lower()
                status = (
                    "pass" if raw_result == "pass"
                    else "fail" if raw_result == "fail"
                    else "warn"
                )
                result.append({
                    "rule": sr.name, "status": status,
                    "action": sr.action,
                    "message": f"{sr.message} [LLM: {matched.get('reason', '无')}]",
                })
            else:
                result.append({
                    "rule": sr.name, "status": "warn",
                    "action": sr.action,
                    "message": f"{sr.message} [LLM未返回此规则结果]",
                })
        return result
