"""
RuleEngine 单元测试

覆盖:
- 5 条默认规则在正常/超标单下的 pass/warn/fail/error
- custom_rules 合并 + 白名单拦截
- 脏枚举 fail-loud
- None 字段 / 空数组 / 未知运算符 / 未知字段 边界
- summarize_checks 与 graph/nodes.py 格式兼容
- RuleDef / RuleCreate / RuleUpdate / RuleResponse schema
- RuleBuilder 编译器
- validate_rule_ast 静态校验
"""
import sys
import pytest

# 确保项目路径可用
sys.path.insert(0, r"D:\python\agent项目\expense-audit-system\backend")

from app.core.rule_engine import (
    RuleEngine, build_data, validate_rule_ast,
    summarize_checks, RuleError, _age_days,
)
from app.core.rule_builder import build
from app.schemas.rule import (
    RuleDef, RuleCreate, RuleUpdate, RuleResponse, RuleListResponse,
)


# ============================================================
# Test Data Helpers
# ============================================================

class FakeItem:
    def __init__(self, amount, invoice_verified, expense_date):
        self.amount = amount
        self.invoice_verified = invoice_verified
        self.expense_date = expense_date
        self.description = ""
        self.invoice_no = ""


class FakeExpenseType:
    def __init__(self, value):
        self.value = value


class FakeExpense:
    def __init__(self, total_amount, expense_type_val, items):
        self.total_amount = total_amount
        self.expense_type = FakeExpenseType(expense_type_val)
        self.currency = "CNY"
        self.title = "测试报销单"
        self.description = ""
        self.items = items


# ============================================================
# 规则工厂
# ============================================================

def make_amount_rule(max_val=5000):
    """单笔金额上限规则"""
    return RuleDef(
        name="单笔金额上限", rule_type="amount_limit",
        logic={"<=": [{"var": "total_amount"}, max_val]},
        action="require_approval",
        message="单笔报销金额超过限制",
    )


def make_invoice_rule():
    """必须有发票规则"""
    return RuleDef(
        name="必须有发票", rule_type="compliance",
        logic={"!": [{"var": "has_unverified_invoice"}]},
        action="reject",
        message="存在未验证发票",
    )


def make_travel_rule(max_item=500):
    """差旅费标准规则 (every 语义)"""
    return RuleDef(
        name="差旅费标准", rule_type="amount_limit",
        logic={
            "_kind": "every", "_array": "items",
            "_item_rule": {"<=": [{"var": "amount"}, max_item]},
        },
        action="warn",
        message="差旅费超出标准",
    )


def make_invoice_age_rule(max_days=90):
    """发票时间规则"""
    return RuleDef(
        name="发票时间", rule_type="time",
        logic={"<=": [{"var": "max_invoice_age_days"}, max_days]},
        action="warn",
        message="存在超过期限的发票",
    )


ALL_5_RULES = [
    make_amount_rule(5000),
    make_invoice_rule(),
    make_travel_rule(500),
    RuleDef(name="招待费限制", rule_type="amount_limit",
            logic={"<=": [{"var": "total_amount"}, 2000]},
            action="require_approval", message="招待费超限"),
    make_invoice_age_rule(90),
]


# ============================================================
# build_data
# ============================================================

class TestBuildData:
    """build_data() 数据准备测试"""

    def test_normal_expense(self):
        e = FakeExpense(3000, "travel", [
            FakeItem(400, True, "2026-07-20"),
            FakeItem(100, True, "2026-07-25"),
        ])
        d = build_data(e, {"department": "技术部", "role": "employee"})
        assert d["total_amount"] == 3000
        assert d["expense_type"] == "travel"
        assert d["item_count"] == 2
        assert d["has_unverified_invoice"] is False
        assert d["max_invoice_age_days"] is not None
        assert d["max_invoice_age_days"] <= 30  # ~15天
        assert d["user_department"] == "技术部"
        print("PASS - test_normal_expense")

    def test_bad_expense(self):
        e = FakeExpense(8000, "travel", [
            FakeItem(600, False, "2026-04-01"),
        ])
        d = build_data(e)
        assert d["has_unverified_invoice"] is True
        assert d["max_invoice_age_days"] > 90  # 4月的发票
        print("PASS - test_bad_expense")

    def test_empty_items(self):
        e = FakeExpense(100, "office", [])
        d = build_data(e)
        assert d["item_count"] == 0
        assert d["items"] == []
        assert d["has_unverified_invoice"] is False  # 无未验证项
        assert d["max_invoice_age_days"] is None     # 无日期
        print("PASS - test_empty_items")

    def test_none_user_info(self):
        e = FakeExpense(100, "office", [])
        d = build_data(e, None)
        assert d["user_department"] == ""
        assert d["user_role"] == ""
        print("PASS - test_none_user_info")


# ============================================================
# RuleEngine.evaluate
# ============================================================

class TestRuleEngineEvaluate:
    """RuleEngine.evaluate() 核心求值测试"""

    def test_amount_lte_pass(self):
        d = build_data(FakeExpense(3000, "travel", []))
        engine = RuleEngine([make_amount_rule(5000)])
        r = engine.evaluate(d)
        assert r[0]["status"] == "pass"
        print("PASS - test_amount_lte_pass")

    def test_amount_lte_fail(self):
        d = build_data(FakeExpense(8000, "travel", []))
        engine = RuleEngine([make_amount_rule(5000)])
        r = engine.evaluate(d)
        assert r[0]["status"] == "warn"  # action=require_approval → warn
        print("PASS - test_amount_lte_fail")

    def test_invoice_verified_pass(self):
        d = build_data(FakeExpense(100, "travel", [
            FakeItem(50, True, "2026-08-01"),
        ]))
        engine = RuleEngine([make_invoice_rule()])
        r = engine.evaluate(d)
        assert r[0]["status"] == "pass"
        print("PASS - test_invoice_verified_pass")

    def test_invoice_verified_fail(self):
        d = build_data(FakeExpense(100, "travel", [
            FakeItem(50, False, "2026-08-01"),
        ]))
        engine = RuleEngine([make_invoice_rule()])
        r = engine.evaluate(d)
        assert r[0]["status"] == "fail"  # action=reject → fail
        print("PASS - test_invoice_verified_fail")

    def test_travel_item_pass(self):
        d = build_data(FakeExpense(100, "travel", [
            FakeItem(400, True, "2026-08-01"),
            FakeItem(100, True, "2026-08-02"),
        ]))
        engine = RuleEngine([make_travel_rule(500)])
        r = engine.evaluate(d)
        assert r[0]["status"] == "pass"
        print("PASS - test_travel_item_pass")

    def test_travel_item_exceeds(self):
        d = build_data(FakeExpense(100, "travel", [
            FakeItem(600, True, "2026-08-01"),  # 超标
        ]))
        engine = RuleEngine([make_travel_rule(500)])
        r = engine.evaluate(d)
        assert r[0]["status"] == "warn"
        print("PASS - test_travel_item_exceeds")

    def test_all_5_rules_normal(self):
        """正常报销单: 4 pass + 1 warn (招待费限制)"""
        d = build_data(FakeExpense(3000, "travel", [
            FakeItem(400, True, "2026-07-20"),
            FakeItem(100, True, "2026-07-25"),
        ]))
        engine = RuleEngine(ALL_5_RULES)
        checks = engine.evaluate(d)
        s = summarize_checks(checks)
        assert s["passed"] == 4
        assert s["warnings"] == 1
        assert s["failed"] == 0
        assert s["errors"] == 0
        print(f"PASS - test_all_5_rules_normal: {s}")

    def test_all_5_rules_bad(self):
        """超标报销单: 0 pass + 4 warn + 1 fail"""
        d = build_data(FakeExpense(8000, "travel", [
            FakeItem(600, False, "2026-04-01"),
        ]))
        engine = RuleEngine(ALL_5_RULES)
        checks = engine.evaluate(d)
        s = summarize_checks(checks)
        assert s["failed"] == 1     # 必须有发票
        assert s["warnings"] == 4   # 其余4条
        assert s["passed"] == 0
        print(f"PASS - test_all_5_rules_bad: {s}")

    def test_reject_action_yields_fail(self):
        """action=reject → status=fail"""
        r = RuleEngine([make_invoice_rule()])
        d = build_data(FakeExpense(100, "travel", [
            FakeItem(50, False, "2026-08-01"),
        ]))
        checks = r.evaluate(d)
        assert checks[0]["status"] == "fail"
        print("PASS - test_reject_action_yields_fail")

    def test_warn_action_yields_warn(self):
        """action=warn → status=warn"""
        r = RuleEngine([make_travel_rule(500)])
        d = build_data(FakeExpense(100, "travel", [
            FakeItem(600, True, "2026-08-01"),
        ]))
        checks = r.evaluate(d)
        assert checks[0]["status"] == "warn"
        print("PASS - test_warn_action_yields_warn")


# ============================================================
# 边界 / Fail-loud
# ============================================================

class TestEdgeCases:
    """边界情况 — fail-loud 而非静默吞掉"""

    def test_unknown_field_fail_loud(self):
        """白名单外字段 → validate_rule_ast 抛 RuleError"""
        bad = RuleDef(name="x", rule_type="custom",
                      logic={"==": [{"var": "hack_field"}, 1]},
                      action="warn", message="")
        with pytest.raises(RuleError):
            validate_rule_ast(bad.logic)
        print("PASS - test_unknown_field_fail_loud")

    def test_unknown_op_fail_loud(self):
        """白名单外运算符 → validate_rule_ast 抛 RuleError"""
        bad = RuleDef(name="x", rule_type="custom",
                      logic={"eval": [{"var": "total_amount"}, "5"]},
                      action="warn", message="")
        with pytest.raises(RuleError):
            validate_rule_ast(bad.logic)
        print("PASS - test_unknown_op_fail_loud")

    def test_dirty_enum_exposed(self):
        """expense_type=trip 但正确值是 travel → 引擎返回 warn/fail, 不被 LLM 猜"""
        rule = RuleDef(name="类型检查", rule_type="compliance",
                       logic={"==": [{"var": "expense_type"}, "travel"]},
                       action="warn", message="类型不匹配")
        engine = RuleEngine([rule])
        d = build_data(FakeExpense(100, "trip", []))
        checks = engine.evaluate(d)
        # == 返回 False → action=warn → status=warn
        assert checks[0]["status"] == "warn"
        print("PASS - test_dirty_enum_exposed")

    def test_none_comparison_error(self):
        """None vs 数值比较 → status=error (非静默)"""
        rule = make_invoice_age_rule(90)
        engine = RuleEngine([rule])
        d = build_data(FakeExpense(100, "office", []))  # 空 items → max_age=None
        checks = engine.evaluate(d)
        assert checks[0]["status"] == "error"
        print("PASS - test_none_comparison_error")

    def test_empty_array_every(self):
        """every 空数组 → True (all([])=True), 符合逻辑: 无不满足项"""
        rule = make_travel_rule(500)
        engine = RuleEngine([rule])
        d = build_data(FakeExpense(100, "travel", []))
        checks = engine.evaluate(d)
        assert checks[0]["status"] == "pass"
        print("PASS - test_empty_array_every")

    def test_semantic_rule_skipped(self):
        """exec_mode=semantic → 被引擎跳过 (留给 LLM)"""
        rule = RuleDef(name="语义规则", rule_type="custom",
                       logic={"==": [{"var": "total_amount"}, 999]},
                       action="warn", message="x",
                       exec_mode="semantic")
        engine = RuleEngine([rule])
        d = build_data(FakeExpense(100, "office", []))
        checks = engine.evaluate(d)
        assert len(checks) == 0  # semantic 被跳过
        print("PASS - test_semantic_rule_skipped")


# ============================================================
# custom_rules 合并
# ============================================================

class TestCustomRules:
    """custom_rules 合并与白名单拦截"""

    def test_valid_custom_merged(self):
        """合法的自定义规则应被加载"""
        custom = RuleDef(name="自定义-低金额", rule_type="custom",
                         logic={"<=": [{"var": "total_amount"}, 100]},
                         action="warn", message="金额过低")
        rules = ALL_5_RULES + [custom]
        engine = RuleEngine(rules)
        d = build_data(FakeExpense(3000, "office", []))
        checks = engine.evaluate(d)
        # 6 条规则: 5 + 1 custom (semantic 除外)
        assert len(checks) == 6
        custom_check = [c for c in checks if "自定义" in c["rule"]]
        assert len(custom_check) == 1
        assert custom_check[0]["status"] == "warn"  # 3000 > 100
        print("PASS - test_valid_custom_merged")

    def test_malicious_custom_blocked(self):
        """白名单外字段的自定义规则 → validate_rule_ast 拦截"""
        with pytest.raises(RuleError):
            validate_rule_ast({"==": [{"var": "password"}, "admin123"]})
        print("PASS - test_malicious_custom_blocked")


# ============================================================
# summarize_checks
# ============================================================

class TestSummarizeChecks:
    """summarize_checks 输出格式 (与 graph/nodes.py 兼容)"""

    def test_format_compatible(self):
        """返回 dict 必须包含 failed/passed/total_risk (graph 路由读 failed)"""
        s = summarize_checks([])
        assert "failed" in s
        assert "passed" in s
        assert "warnings" in s
        assert "errors" in s
        assert "total_risk" in s
        assert s["failed"] == 0
        assert s["passed"] == 0
        print("PASS - test_format_compatible")

    def test_high_risk(self):
        """failed > 2 → total_risk=high"""
        checks = [
            {"rule": "r1", "status": "fail"},
            {"rule": "r2", "status": "fail"},
            {"rule": "r3", "status": "fail"},
        ]
        s = summarize_checks(checks)
        assert s["total_risk"] == "high"
        print("PASS - test_high_risk")

    def test_medium_risk(self):
        """1 failed → medium"""
        checks = [
            {"rule": "r1", "status": "fail"},
            {"rule": "r2", "status": "pass"},
        ]
        s = summarize_checks(checks)
        assert s["total_risk"] == "medium"
        print("PASS - test_medium_risk")

    def test_error_elevates_to_high(self):
        """任何 error → total_risk=high"""
        checks = [
            {"rule": "r1", "status": "error"},
            {"rule": "r2", "status": "pass"},
        ]
        s = summarize_checks(checks)
        assert s["total_risk"] == "high"
        print("PASS - test_error_elevates_to_high")

    def test_graph_compatible_failed_count(self):
        """graph/nodes.py 的 make_rule_node 读 summary.failed"""
        d = build_data(FakeExpense(8000, "travel", [
            FakeItem(600, False, "2026-04-01"),
        ]))
        engine = RuleEngine(ALL_5_RULES)
        checks = engine.evaluate(d)
        s = summarize_checks(checks)
        # graph routing: failed_count = s["failed"]
        assert isinstance(s["failed"], int)
        assert s["failed"] >= 0
        print(f"PASS - test_graph_compatible_failed_count: failed={s['failed']}")


# ============================================================
# Schemas
# ============================================================

class TestSchemas:
    """Pydantic Schema 测试"""

    def test_rule_create_valid(self):
        rc = RuleCreate(
            name="测试", rule_type="amount_limit",
            logic={"<=": [{"var": "total_amount"}, 10000]},
            action="require_approval", message="测试",
        )
        assert rc.name == "测试"
        assert rc.exec_mode == "deterministic"  # 默认
        print("PASS - test_rule_create_valid")

    def test_rule_create_invalid_action(self):
        """action 必须是 reject/warn/require_approval 之一"""
        with pytest.raises(Exception):
            RuleCreate(
                name="x", rule_type="amount_limit",
                logic={"<=": [{"var": "total_amount"}, 100]},
                action="delete",  # 无效
                message="x",
            )
        print("PASS - test_rule_create_invalid_action")

    def test_rule_update_partial(self):
        """RuleUpdate 所有字段可选"""
        ru = RuleUpdate(name="新名字")
        assert ru.name == "新名字"
        assert ru.logic is None  # 不传 = 不更新
        assert ru.is_active is None
        print("PASS - test_rule_update_partial")

    def test_rule_response_construction(self):
        resp = RuleResponse(
            id=1, name="单笔金额上限", rule_type="amount_limit",
            logic={"<=": [{"var": "total_amount"}, 5000]},
            action="require_approval",
            message="单笔报销金额超过5000元",
            exec_mode="deterministic",
        )
        assert resp.id == 1
        assert resp.exec_mode == "deterministic"
        print("PASS - test_rule_response_construction")

    def test_rule_list_response(self):
        resp = RuleResponse(
            id=1, name="r1", rule_type="amount_limit",
            logic={"<=": [{"var": "total_amount"}, 5000]},
            action="require_approval", message="x",
        )
        lr = RuleListResponse(total=1, items=[resp])
        assert lr.total == 1
        assert len(lr.items) == 1
        print("PASS - test_rule_list_response")


# ============================================================
# RuleBuilder
# ============================================================

class TestRuleBuilder:
    """RuleBuilder: {field,operator,value} → json-logic"""

    def test_simple_lte(self):
        result = build({"field": "total_amount", "operator": "lte", "value": 5000})
        assert result == {"<=": [{"var": "total_amount"}, 5000]}
        print("PASS - test_simple_lte")

    def test_simple_eq(self):
        result = build({"field": "expense_type", "operator": "eq", "value": "travel"})
        assert result == {"==": [{"var": "expense_type"}, "travel"]}
        print("PASS - test_simple_eq")

    def test_items_wildcard(self):
        """items.*.amount → every 语义"""
        result = build({"field": "items.*.amount", "operator": "lte", "value": 500})
        assert result["_kind"] == "every"
        assert result["_array"] == "items"
        assert result["_rule"] == {"<=": [{"var": "amount"}, 500]}
        print("PASS - test_items_wildcard")

    def test_in_operator(self):
        result = build({"field": "expense_type", "operator": "in", "value": ["travel", "office"]})
        assert result == {"in": [{"var": "expense_type"}, ["travel", "office"]]}
        print("PASS - test_in_operator")

    def test_composite_all(self):
        result = build({
            "all": [
                {"field": "expense_type", "operator": "eq", "value": "travel"},
                {"field": "items.*.amount", "operator": "lte", "value": 500},
            ]
        })
        assert result["and"][0] == {"==": [{"var": "expense_type"}, "travel"]}
        assert result["and"][1]["_kind"] == "every"
        print("PASS - test_composite_all")

    def test_composite_any(self):
        result = build({
            "any": [
                {"field": "total_amount", "operator": "gt", "value": 10000},
                {"field": "expense_type", "operator": "eq", "value": "entertainment"},
            ]
        })
        assert "or" in result
        assert len(result["or"]) == 2
        print("PASS - test_composite_any")

    def test_unknown_operator_raises(self):
        with pytest.raises(ValueError, match="不支持的运算符"):
            build({"field": "total_amount", "operator": "unknown", "value": 1})
        print("PASS - test_unknown_operator_raises")


# ============================================================
# _age_days
# ============================================================

class TestAgeDays:
    def test_none(self):
        assert _age_days(None) is None
        print("PASS - test_none")

    def test_recent_date(self):
        days = _age_days("2026-08-01")
        assert isinstance(days, int)
        assert 0 <= days <= 5  # 如果今天在8月4日附近
        print(f"PASS - test_recent_date: {days} days")

    def test_old_date(self):
        days = _age_days("2026-01-01")
        assert days > 180
        print(f"PASS - test_old_date: {days} days")
