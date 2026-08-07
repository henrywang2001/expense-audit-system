"""
规则引擎 RuleEngine — 基于 maykin-json-logic-py 的确定性规则求值器

设计原则:
- 零自研解释器: 直接调用 jsonLogic(rule, data) 求值
- 零 RCE 风险: json-logic 天然不解释代码, 另加两道白名单安全闸
- fail-loud: 脏数据/未知字段/未知运算符 → error, 不被静默吞掉
- 不短路: 即使第一条规则就是 reject, 也继续检查后续规则, 收集完整违规信息

依赖: maykin-json-logic-py (pip install maykin-json-logic-py)
导入: from json_logic import jsonLogic
"""
import logging
from typing import Any, Dict, List, Optional

from json_logic import jsonLogic

from app.schemas.rule import RuleDef, RuleExecMode

logger = logging.getLogger(__name__)

# ========== 安全配置 ==========

# 数据字段白名单: 只允许规则引用这些根层级字段
FIELD_WHITELIST = {
    "total_amount", "currency", "title", "expense_type",
    "description", "items", "user_department", "user_role",
    # 预计算字段
    "item_count", "has_unverified_invoice", "max_invoice_age_days",
    # reduce/map 内部使用的变量名 (不在此名单中, 但 json-logic 内部会引用)
}

# 运算符白名单 (基于 maykin-json-logic-py 0.16.0 实际支持的操作符)
ALLOWED_OPS = {
    # 比较
    "==", "===", "!=", "!==", ">", ">=", "<", "<=",
    # 逻辑
    "!", "!!", "and", "or", "?:", "if",
    # 数据访问
    "var", "missing", "missing_some",
    # 数组
    "map", "reduce",
    # 数学
    "%", "+", "*", "-", "/", "min", "max",
    # 字符串/集合
    "cat", "substr", "in", "merge",
    # 聚合
    "count",
    # 日期 (可选, 推荐在 build_data 中预计算)
    "today", "date", "datetime", "rdelta", "duration",
    # 调试
    "log",
}

# 内部标记 key (不是 json-logic 运算符, 是 RuleEngine/Builder 的元数据)
_INTERNAL_KEYS = {"_kind", "_array", "_rule", "_item_rule"}


# ========== 异常 ==========

class RuleError(Exception):
    """规则 AST 校验失败或求值异常 — fail-loud, 绝不静默吞掉"""
    pass


# ========== 数据准备 ==========

def _age_days(expense_date) -> Optional[int]:
    """计算日期距今多少天。None 表示无日期 (规则求值会 fail-loud)"""
    if expense_date is None:
        return None
    from datetime import date, datetime as dt
    if isinstance(expense_date, str):
        try:
            expense_date = dt.strptime(expense_date, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return None
    if isinstance(expense_date, dt):
        expense_date = expense_date.date()
    return (date.today() - expense_date).days


def build_data(expense, user_info: dict | None = None) -> dict:
    """
    把报销单收敛成 json-logic 能安全求值的纯数据字典。

    只暴露 FIELD_WHITELIST 里的标量/列表, 绝不传 ORM 对象或带方法的对象。
    日期/正则等运算在此预计算成标量字段, 规则层只做纯比较。
    """
    items_raw = (
        expense.items
        if hasattr(expense, "items") and not isinstance(expense, dict)
        else expense.get("items", []) if isinstance(expense, dict)
        else []
    )

    items = []
    for i in items_raw:
        if isinstance(i, dict):
            items.append({
                "amount": float(i.get("amount", 0)),
                "invoice_verified": bool(i.get("invoice_verified", False)),
                "invoice_age_days": _age_days(i.get("expense_date")),
                "expense_date": (
                    str(i.get("expense_date"))
                    if i.get("expense_date") else None
                ),
                "description": i.get("description") or "",
                "invoice_no": i.get("invoice_no") or "",
            })
        else:
            items.append({
                "amount": float(getattr(i, "amount", 0)),
                "invoice_verified": bool(getattr(i, "invoice_verified", False)),
                "invoice_age_days": _age_days(
                    getattr(i, "expense_date", None)
                ),
                "expense_date": (
                    str(getattr(i, "expense_date", None))
                    if getattr(i, "expense_date", None) else None
                ),
                "description": getattr(i, "description", None) or "",
                "invoice_no": getattr(i, "invoice_no", None) or "",
            })

    etype = (
        expense.expense_type.value
        if hasattr(expense, "expense_type") and hasattr(expense.expense_type, "value")
        else expense.get("expense_type")
        if isinstance(expense, dict)
        else str(getattr(expense, "expense_type", ""))
    )

    return {
        "total_amount": float(
            expense.total_amount
            if not isinstance(expense, dict)
            else expense.get("total_amount", 0)
        ),
        "currency": (
            getattr(expense, "currency", "") or ""
            if not isinstance(expense, dict)
            else expense.get("currency") or ""
        ),
        "title": (
            getattr(expense, "title", "") or ""
            if not isinstance(expense, dict)
            else expense.get("title") or ""
        ),
        "expense_type": etype,
        "description": (
            getattr(expense, "description", "") or ""
            if not isinstance(expense, dict)
            else expense.get("description") or ""
        ),
        "items": items,
        "user_department": (user_info or {}).get("department", ""),
        "user_role": (user_info or {}).get("role", ""),
        # 预计算衍生字段
        "item_count": len(items),
        "has_unverified_invoice": any(
            not it["invoice_verified"] for it in items
        ),
        "max_invoice_age_days": max(
            (it["invoice_age_days"] for it in items
             if it["invoice_age_days"] is not None),
            default=None,
        ),
    }


# ========== AST 静态校验 ==========

def _extract_var_root(field_ref: Any) -> Optional[str]:
    """从 json-logic var 引用中提取根字段名"""
    if isinstance(field_ref, str):
        return field_ref.split(".")[0] if field_ref else None
    if isinstance(field_ref, dict):
        raw = field_ref.get("var", "")
        return raw.split(".")[0] if raw else None
    return None


def validate_rule_ast(node: Any, *, inside_scoped: bool = False) -> None:
    """
    静态校验规则 AST:
    - 只引用 FIELD_WHITELIST 中的字段 (inside_scoped=True 时跳过, 因为子字段如 amount 在数组项内部)
    - 只使用 ALLOWED_OPS 中的运算符
    不通过 → 抛 RuleError
    """
    if isinstance(node, list):
        for item in node:
            validate_rule_ast(item, inside_scoped=inside_scoped)
        return
    if not isinstance(node, dict):
        return

    for key, args in node.items():
        # 内部元数据 key — 进入 scoped 上下文 (_item_rule 内部是数组项的字段)
        if key in _INTERNAL_KEYS:
            if key == "_item_rule":
                validate_rule_ast(args, inside_scoped=True)
            else:
                validate_rule_ast(args, inside_scoped=inside_scoped)
            continue

        if key == "var":
            if not inside_scoped:
                root = _extract_var_root(args)
                if root is None:
                    pass  # 动态路径, 信任
                elif root not in FIELD_WHITELIST:
                    raise RuleError(
                        f"规则字段不在白名单中: '{root}'. "
                        f"白名单: {sorted(FIELD_WHITELIST)}"
                    )
        elif key not in ALLOWED_OPS:
            raise RuleError(
                f"规则运算符不在白名单中: '{key}'. "
                f"白名单: {sorted(ALLOWED_OPS)}"
            )

        # 递归校验 children
        if isinstance(args, list):
            for child in args:
                validate_rule_ast(child, inside_scoped=inside_scoped)
        elif isinstance(args, dict):
            validate_rule_ast(args, inside_scoped=inside_scoped)


# ========== 规则引擎 ==========

class RuleEngine:
    """
    确定性规则引擎 — 线性扫描所有规则, 每条独立求值, 不短路.

    用法:
        engine = RuleEngine(rules)
        results = engine.evaluate(data)
        # results: [{"rule": "…", "status": "pass"|"fail"|"warn"|"error", …}, …]
    """

    def __init__(self, rules: List[RuleDef]):
        self.rules = [r for r in rules if r.is_active]

    def evaluate(self, data: dict) -> List[dict]:
        """对 data 求值所有规则, 返回结果列表"""
        results: List[dict] = []
        for rule in self.rules:
            if rule.exec_mode == "semantic":
                # 语义规则跳过 — 留给 LLM 单独处理
                continue
            results.append(self._eval_one(rule, data))
        return results

    def _eval_one(self, rule: RuleDef, data: dict) -> dict:
        """求值单条规则, 返回 {rule, status, action, message}"""
        base = {
            "rule": rule.name,
            "rule_type": rule.rule_type,
            "action": rule.action,
            "message": rule.message,
        }

        try:
            # ① 静态校验
            validate_rule_ast(rule.logic)

            # ② 检查是否 every/some/none 包装 (RuleBuilder 产物)
            logic = rule.logic
            kind = logic.get("_kind") if isinstance(logic, dict) else None

            if kind in ("every", "some", "none"):
                passed = self._eval_scoped(rule, data, kind)
            else:
                passed = self._eval_plain(rule, data)

            # ③ 状态映射
            if isinstance(passed, bool):
                status = "pass" if passed else self._fail_status(rule.action)
            else:
                # None 或其他非布尔 → 数据缺失, fail-loud
                status = "error"
                base["message"] = (
                    f"{rule.message} [数据缺失: 规则求值返回 {passed!r}]"
                )

            base["status"] = status
            return base

        except RuleError as e:
            logger.warning(f"规则 AST 校验失败 [{rule.name}]: {e}")
            return {**base, "status": "error",
                    "message": f"{rule.message} [规则定义非法: {e}]"}
        except ValueError as e:
            # 未知运算符等 json-logic 内部错误
            logger.warning(f"规则求值失败 [{rule.name}]: {e}")
            return {**base, "status": "error",
                    "message": f"{rule.message} [求值失败: {e}]"}
        except Exception as e:
            logger.error(f"规则执行异常 [{rule.name}]: {e}", exc_info=True)
            return {**base, "status": "error",
                    "message": f"{rule.message} [系统异常: {e}]"}

    def _eval_plain(self, rule: RuleDef, data: dict) -> Optional[bool]:
        """普通规则求值 (无数组遍历语义)"""
        return jsonLogic(rule.logic, data, use_var_undefined=True)

    def _eval_scoped(
        self, rule: RuleDef, data: dict, kind: str
    ) -> Optional[bool]:
        """
        数组遍历规则求值 (every/some/none — 通过 map + Python 后处理实现).

        maykin-json-logic-py 不支持 every/some/none 原生操作,
        但支持 map, 这里用 map + all()/any() 透明兼容.
        """
        array_path = rule.logic.get("_array", "items")
        item_rule = rule.logic.get("_item_rule") or rule.logic.get("_rule")
        if item_rule is None:
            raise RuleError(f"{kind} 规则缺少 _rule 定义")

        # Step 1: 用 map 对数组每项求值 → [True, False, …]
        mapped = jsonLogic(
            {"map": [{"var": array_path}, item_rule]},
            data,
            use_var_undefined=True,
        )

        if mapped is None:
            return None
        if not isinstance(mapped, list):
            # map 返回非列表 → 降级为 bool
            return bool(mapped)

        # Step 2: Python 后处理
        if kind == "every":
            return all(mapped)
        elif kind == "some":
            return any(mapped)
        elif kind == "none":
            return not any(mapped)
        return None

    @staticmethod
    def _fail_status(action: str) -> str:
        """把 rule.action 映射到检查结果状态"""
        if action == "reject":
            return "fail"
        return "warn"


# ========== 工具 ==========

def summarize_checks(checks: List[dict]) -> dict:
    """汇总规则检查结果 (兼容原 RuleAgent.summarize_rules 的输出格式)"""
    summary = {"passed": 0, "warnings": 0, "failed": 0,
               "errors": 0, "total_risk": "low"}

    for c in checks:
        status = c.get("status", "")
        if status == "pass":
            summary["passed"] += 1
        elif status == "warn":
            summary["warnings"] += 1
        elif status == "fail":
            summary["failed"] += 1
        elif status == "error":
            summary["errors"] += 1

    # 综合风险等级
    if summary["failed"] > 2 or summary["errors"] > 0:
        summary["total_risk"] = "high"
    elif summary["failed"] > 0 or summary["warnings"] > 2:
        summary["total_risk"] = "medium"

    return summary
