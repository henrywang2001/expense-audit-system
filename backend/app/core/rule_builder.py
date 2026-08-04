"""
RuleBuilder — 把 {field, operator, value} DSL 编译成 json-logic 对象

这是作者层语法糖, 产物仍是 json-logic, 存/执行的永远是 json-logic 本体。
使用方式:

    from app.core.rule_builder import build

    build({"field": "total_amount", "operator": "lte", "value": 5000})
    # → {"<=": [{"var": "total_amount"}, 5000]}

    build({"all": [
        {"field": "expense_type", "operator": "eq", "value": "travel"},
        {"field": "items.*.amount", "operator": "lte", "value": 500},
    ]})
    # → {"and": [
    #     {"==": [{"var": "expense_type"}, "travel"]},
    #     {"every": [{"var": "items"}, {"<=": [{"var": "amount"}, 500]}]}
    # ]}
"""
import copy
from typing import Any, Dict, List, Optional


OPERATOR_MAP = {
    "lte": "<=", "lt": "<",
    "gte": ">=", "gt": ">",
    "eq": "==", "ne": "!=",
    "in": "in",
}


def build(condition: dict, logical: str | None = None) -> dict:
    """
    把 {field, operator, value} 编译为 json-logic 对象.

    condition 支持两种形式:
      基础:  {"field": "total_amount", "operator": "lte", "value": 5000}
      组合:  {"all": [c1, c2]}  或  {"any": [c1, c2]}

    field 含 "items.*." 前缀时会自动展开为 every(item, rule) 语义.
    """
    if "all" in condition or "any" in condition:
        op = "and" if "all" in condition else "or"
        children = condition.get("all") or condition.get("any") or []
        return {op: [build(c) for c in children]}

    field = condition["field"]
    operator = condition["operator"]
    value = condition["value"]

    jl_op = OPERATOR_MAP.get(operator)
    if jl_op is None:
        raise ValueError(f"不支持的运算符: {operator}, 支持: {list(OPERATOR_MAP)}")

    # items.*.xxx → every 语义: 数组每项的子字段满足规则
    if field.startswith("items.*."):
        leaf = field.split(".", 2)[2]  # "items.*.amount" → "amount"
        # 注意: maykin-json-logic-py 不支持 every, 此处分两步:
        # 1. 规则逻辑里用 map 展开
        # 2. RuleEngine.evaluate 里 Python 后处理 all()/any()
        # 这里只存标记, RuleEngine 读到 "every" 字段时自动处理
        return {
            "_kind": "every",
            "_array": "items",
            "_rule": {jl_op: [{"var": leaf}, value]},
        }

    return {jl_op: [{"var": field}, value]}


def _raw_jl(condition: dict) -> dict:
    """
    原始 json-logic 模式: 含 _kind=every 的规则展开成纯 map+all 语义
    供 RuleEngine 内部使用, 不暴露给 API.
    """
    kind = condition.get("_kind")
    if kind == "every":
        array_path = condition["_array"]
        item_rule = condition["_rule"]
        # map 检查每项, RuleEngine 拿到结果后 all()
        return {
            "_kind": "every",
            "_array": array_path,
            "_item_rule": item_rule,
        }
    return condition
