# -*- coding: utf-8 -*-
"""
AI 审核结果展示层收敛（ai_review_presenter）单元测试

覆盖点：
- final_reason → summary 的映射与兜底
- agent_results → issues / suggestions 的映射规则
- risk_level / risk_score 的归一化与跳过 RiskAgent 时的兜底
- 向后兼容：workflow 原有键不被删除或篡改
- 健壮性：None / 残缺 / 脏数据输入不抛异常
"""
import pytest

from app.services.ai_review_presenter import (
    VALID_RISK_LEVELS,
    build_review_presentation,
    enrich_review_result,
    normalize_risk_level,
    normalize_risk_score,
)


# ===== 测试夹具 =====

def _full_workflow_result() -> dict:
    """一次成功的完整 workflow 返回（5 个 Agent 全部执行）"""
    return {
        "success": True,
        "workflow_status": "completed",
        "expense_id": 5,
        "final_decision": "review",
        "final_reason": "风险等级medium, 存在1项违规和1项警告",
        "risk_level": "medium",
        "risk_score": 45,
        "agent_results": [
            {"agent_name": "DocumentAgent", "status": "success",
             "result": {}, "message": "解析完成", "duration_ms": 10},
            {"agent_name": "RuleAgent", "status": "success", "result": {
                "rule_checks": [
                    {"rule": "单笔金额上限", "status": "fail",
                     "message": "单笔金额超过5000元上限"},
                    {"rule": "发票必须验真", "status": "warn",
                     "message": "存在未验真发票"},
                    {"rule": "时效性", "status": "pass", "message": "通过"},
                ],
                "summary": {"passed": 1, "warnings": 1, "failed": 1,
                            "errors": 0, "total_risk": "medium"},
            }, "message": "", "duration_ms": 20},
            {"agent_name": "RiskAgent", "status": "success", "result": {
                "risk_level": "medium", "risk_score": 45,
                "risk_factors": ["金额显著高于历史均值"],
                "recommendations": ["核验发票真伪"],
            }, "message": "", "duration_ms": 30},
            {"agent_name": "RAGAgent", "status": "success",
             "result": {"retrieved_docs": []}, "message": "", "duration_ms": 5},
            {"agent_name": "DecisionAgent", "status": "success", "result": {
                "decision": "review",
                "reason": "风险等级medium, 存在1项违规和1项警告",
                "confidence": 70,
                "key_findings": ["1项规则违规"],
                "suggestions": ["重点核查超限金额的业务合理性"],
                "risk_mitigation": "要求提供部门经理书面说明",
            }, "message": "", "duration_ms": 40},
        ],
        "message": "Agent工作流执行完成",
    }


# ===== 展示字段契约 =====

class TestPresentationContract:
    """前端 ExpenseDetail.vue 依赖的字段契约"""

    def test_all_display_fields_present_and_typed(self):
        out = build_review_presentation(_full_workflow_result())

        assert isinstance(out["summary"], str) and out["summary"]
        assert isinstance(out["issues"], list)
        assert isinstance(out["suggestions"], list)
        assert out["risk_level"] in VALID_RISK_LEVELS
        assert isinstance(out["risk_score"], float)

    def test_issue_item_shape(self):
        out = build_review_presentation(_full_workflow_result())

        assert out["issues"], "应至少识别出一条问题"
        for issue in out["issues"]:
            assert set(issue.keys()) == {"severity", "description", "type"}
            assert issue["severity"] in ("high", "medium", "low")
            assert isinstance(issue["description"], str) and issue["description"]
            assert issue["type"] in ("rule", "risk", "system")

    def test_suggestions_are_plain_strings(self):
        out = build_review_presentation(_full_workflow_result())

        assert out["suggestions"]
        assert all(isinstance(s, str) and s for s in out["suggestions"])


# ===== 映射规则 =====

class TestMappingRules:
    """final_reason / agent_results → 展示字段 的具体映射规则"""

    def test_final_reason_maps_to_summary(self):
        data = _full_workflow_result()
        out = build_review_presentation(data)
        assert out["summary"] == data["final_reason"]

    def test_generic_reason_falls_back_to_composed_summary(self):
        data = _full_workflow_result()
        data["final_reason"] = "工作流已完成"
        data["agent_results"][4]["result"]["reason"] = ""
        out = build_review_presentation(data)

        assert out["summary"] != "工作流已完成"
        assert "AI 审核结论" in out["summary"]

    def test_rule_status_maps_to_severity(self):
        out = build_review_presentation(_full_workflow_result())
        rule_issues = {
            i["description"]: i["severity"]
            for i in out["issues"] if i["type"] == "rule"
        }
        # fail → high, warn → medium, pass → 不产出 issue
        assert rule_issues["单笔金额上限：单笔金额超过5000元上限"] == "high"
        assert rule_issues["发票必须验真：存在未验真发票"] == "medium"
        assert not any("时效性" in d for d in rule_issues)

    def test_risk_factors_map_to_issues(self):
        out = build_review_presentation(_full_workflow_result())
        risk_issues = [i for i in out["issues"] if i["type"] == "risk"]
        assert [i["description"] for i in risk_issues] == ["金额显著高于历史均值"]

    def test_failed_agent_becomes_system_issue(self):
        data = _full_workflow_result()
        data["agent_results"].append({
            "agent_name": "RAGAgent", "status": "failed",
            "result": {}, "message": "检索服务不可用", "duration_ms": 0,
        })
        out = build_review_presentation(data)
        system_issues = [i for i in out["issues"] if i["type"] == "system"]

        assert len(system_issues) == 1
        assert system_issues[0]["severity"] == "high"
        assert "检索服务不可用" in system_issues[0]["description"]

    def test_suggestions_merged_in_priority_order(self):
        out = build_review_presentation(_full_workflow_result())
        # 决策建议 → 风险缓释 → 风险处置建议
        assert out["suggestions"] == [
            "重点核查超限金额的业务合理性",
            "要求提供部门经理书面说明",
            "核验发票真伪",
        ]

    def test_suggestions_deduplicated(self):
        data = _full_workflow_result()
        data["agent_results"][2]["result"]["recommendations"] = [
            "重点核查超限金额的业务合理性", "核验发票真伪",
        ]
        out = build_review_presentation(data)
        assert len(out["suggestions"]) == len(set(out["suggestions"]))

    def test_empty_suggestions_get_decision_fallback(self):
        data = _full_workflow_result()
        data["agent_results"][2]["result"]["recommendations"] = []
        data["agent_results"][4]["result"]["suggestions"] = []
        data["agent_results"][4]["result"]["risk_mitigation"] = ""
        out = build_review_presentation(data)

        assert len(out["suggestions"]) == 1
        assert out["suggestions"][0]


# ===== 风险等级/分数归一化 =====

class TestRiskNormalization:

    @pytest.mark.parametrize("raw,expected", [
        ("low", "low"), ("LOW", "low"), ("medium", "medium"),
        ("high", "high"), ("critical", "critical"),
        ("中", "medium"), ("高风险", "high"), ("严重", "critical"),
        ("very high", "critical"), (None, "low"), ("莫名其妙", "low"),
    ])
    def test_normalize_risk_level(self, raw, expected):
        assert normalize_risk_level(raw) == expected

    @pytest.mark.parametrize("raw,level,expected", [
        (45, "medium", 45.0), ("70", "high", 70.0), (150, "high", 100.0),
        (-5, "low", 0.0), (None, "high", 75.0), ("bad", "critical", 95.0),
    ])
    def test_normalize_risk_score(self, raw, level, expected):
        assert normalize_risk_score(raw, level) == expected

    def test_risk_level_always_valid_enum_value(self):
        """写入 expenses.risk_level(Enum) 前必须落在合法枚举取值内"""
        data = _full_workflow_result()
        data["agent_results"][2]["result"]["risk_level"] = "极高"
        out = build_review_presentation(data)
        assert out["risk_level"] == "critical"
        assert out["risk_level"] in VALID_RISK_LEVELS

    def test_skipped_risk_agent_falls_back_to_rule_total_risk(self):
        """
        严重违规时 RiskAgent 被条件路由跳过，workflow 顶层给的是硬编码
        low/0，此时应改用规则汇总的 total_risk，避免高危单被误报为低风险。
        """
        data = {
            "success": True, "workflow_status": "completed", "expense_id": 9,
            "final_decision": "reject", "final_reason": "严重违规",
            "risk_level": "low", "risk_score": 0,
            "agent_results": [
                {"agent_name": "RuleAgent", "status": "success", "result": {
                    "rule_checks": [
                        {"rule": "A", "status": "fail", "message": "A 违规"},
                        {"rule": "B", "status": "fail", "message": "B 违规"},
                        {"rule": "C", "status": "error", "message": "C 求值失败"},
                    ],
                    "summary": {"passed": 0, "warnings": 0, "failed": 2,
                                "errors": 1, "total_risk": "high"},
                }, "message": "", "duration_ms": 5},
            ],
        }
        out = build_review_presentation(data)

        assert out["risk_level"] == "high"
        assert out["risk_score"] > 0
        assert len([i for i in out["issues"] if i["type"] == "rule"]) == 3

    def test_never_downgrades_top_level_risk(self):
        """兜底只上调不下调：顶层 critical 不应被规则汇总的 low 拉低"""
        data = {
            "final_decision": "review", "final_reason": "x",
            "risk_level": "critical", "risk_score": 0,
            "agent_results": [
                {"agent_name": "RuleAgent", "status": "success", "result": {
                    "summary": {"total_risk": "low"}}, "message": ""},
            ],
        }
        assert build_review_presentation(data)["risk_level"] == "critical"


# ===== 向后兼容 & 健壮性 =====

class TestBackwardCompatibility:

    def test_workflow_keys_preserved(self):
        """B1 修复产出的键必须原样保留（前端/其它调用方仍在用）"""
        data = _full_workflow_result()
        out = enrich_review_result(data)

        assert out["success"] is True
        assert out["workflow_status"] == "completed"
        assert out["expense_id"] == 5
        assert out["final_decision"] == "review"
        assert out["final_reason"] == data["final_reason"]
        assert out["message"] == "Agent工作流执行完成"
        assert len(out["agent_results"]) == 5

    def test_input_not_mutated(self):
        data = _full_workflow_result()
        enrich_review_result(data)
        assert "summary" not in data
        assert "issues" not in data

    def test_only_adds_declared_display_fields(self):
        data = _full_workflow_result()
        added = set(enrich_review_result(data)) - set(data)
        assert added == {"summary", "issues", "suggestions"}


class TestRobustness:

    @pytest.mark.parametrize("bad_input", [
        None, {}, {"agent_results": None}, {"agent_results": "not-a-list"},
        {"agent_results": [None, "x", {}]},
        {"final_reason": None, "risk_level": object()},
    ])
    def test_never_raises_on_bad_input(self, bad_input):
        out = enrich_review_result(bad_input)
        assert isinstance(out["summary"], str) and out["summary"]
        assert isinstance(out["issues"], list)
        assert isinstance(out["suggestions"], list)
        assert out["risk_level"] in VALID_RISK_LEVELS
        assert isinstance(out["risk_score"], float)

    def test_workflow_error_response_still_renderable(self):
        """workflow 引擎异常时（final_decision=error）也要能渲染"""
        out = enrich_review_result({
            "success": False, "workflow_status": "failed", "expense_id": 1,
            "final_decision": "error", "final_reason": "报销单不存在",
            "agent_results": [], "message": "报销单不存在",
        })
        assert out["summary"] == "报销单不存在"
        assert out["suggestions"]
        assert out["workflow_status"] == "failed"

    def test_dict_shaped_risk_factor_is_flattened(self):
        """LLM 可能把字符串包成 dict，需要拍平而不是丢弃"""
        out = build_review_presentation({
            "final_decision": "review", "final_reason": "x",
            "agent_results": [
                {"agent_name": "RiskAgent", "status": "success", "result": {
                    "risk_level": "high",
                    "risk_factors": [{"factor": "疑似虚开发票"}, None, ""],
                }, "message": ""},
            ],
        })
        descriptions = [i["description"] for i in out["issues"]]
        assert descriptions == ["疑似虚开发票"]
