"""
条件路由逻辑测试

测试路由函数的三种场景:
1. 正常报销 (failed=0, no errors) → fan-out 到 risk+rag
2. 严重违规 (failed>=2) → 短路到 decision
3. 前置节点异常 → 短路到 decision

enabled_agents 测试:
4. 禁用 risk/rag → 路由自动调整
"""
import pytest
from langgraph.types import Send


def _get_router(enabled_agents=None):
    """获取带指定 enabled_agents 的路由函数"""
    from app.agents.graph.builder import _make_route_factory
    return _make_route_factory(enabled_agents)


class TestRouteAfterRule:
    """条件路由函数单元测试（enabled_agents=None，全部启用）"""

    def test_normal_fan_out(self):
        """正常报销: failed=0, 无错误 → 返回 Send list fan-out"""
        route = _get_router(None)
        state = {"failed_count": 0, "errors": []}
        result = route(state)

        assert isinstance(result, list), f"Expected list, got {type(result)}"
        assert len(result) == 2, f"Expected 2 Send objects, got {len(result)}"
        assert all(isinstance(s, Send) for s in result), \
            "All items should be Send objects"
        assert [s.node for s in result] == ["risk", "rag"], \
            f"Expected ['risk','rag'], got {[s.node for s in result]}"

    def test_severe_violation_shortcut(self):
        """严重违规: failed>=2 → 直跳 decision"""
        route = _get_router(None)
        state = {"failed_count": 2, "errors": []}
        result = route(state)
        assert result == "decision", f"Expected 'decision', got {result}"

    def test_severe_violation_gt_2(self):
        """failed>2 也应短路"""
        route = _get_router(None)
        state = {"failed_count": 5, "errors": []}
        result = route(state)
        assert result == "decision"

    def test_document_error_shortcut(self):
        """document 节点异常 → 短路跳过 risk+rag"""
        route = _get_router(None)
        state = {
            "failed_count": 0,
            "errors": [{"node": "document", "error": "document parse error"}],
        }
        result = route(state)
        assert result == "decision", \
            f"Document error should shortcut, got {result}"

    def test_rule_error_shortcut(self):
        """rule 节点异常 → 短路跳过 risk+rag"""
        route = _get_router(None)
        state = {
            "failed_count": 0,
            "errors": [{"node": "rule", "error": "rule check error"}],
        }
        result = route(state)
        assert result == "decision", \
            f"Rule error should shortcut, got {result}"

    def test_non_critical_error_no_shortcut(self):
        """非前置节点错误不影响路由"""
        route = _get_router(None)
        state = {
            "failed_count": 0,
            "errors": [{"node": "rag", "error": "retrieval failed"}],
        }
        result = route(state)
        assert isinstance(result, list), \
            f"Non-critical error should not shortcut, got {result}"

    def test_failed_1_normal_path(self):
        """failed=1 (<2) → 正常路径"""
        route = _get_router(None)
        state = {"failed_count": 1, "errors": []}
        result = route(state)
        assert isinstance(result, list), \
            f"failed=1 should not trigger shortcut, got {result}"

    def test_failed_0_with_warning(self):
        """failed=0 即使有 warnings 也正常执行"""
        route = _get_router(None)
        state = {"failed_count": 0, "errors": []}
        result = route(state)
        assert isinstance(result, list)
        assert len(result) == 2

    def test_and_edge_case(self):
        """极端情况: failed_count 缺失 → 默认 0"""
        route = _get_router(None)
        state = {"errors": []}
        result = route(state)
        assert isinstance(result, list), \
            f"Missing failed_count should default to 0, got {result}"


class TestEnabledAgentsRouting:
    """enabled_agents 过滤路由测试"""

    def test_disable_risk_only(self):
        """禁用 risk → fan-out 只含 rag"""
        route = _get_router(["document", "rule", "rag", "decision"])
        state = {"failed_count": 0, "errors": []}
        result = route(state)
        assert isinstance(result, list) and len(result) == 1
        assert result[0].node == "rag"

    def test_disable_rag_only(self):
        """禁用 rag → fan-out 只含 risk"""
        route = _get_router(["document", "rule", "risk", "decision"])
        state = {"failed_count": 0, "errors": []}
        result = route(state)
        assert isinstance(result, list) and len(result) == 1
        assert result[0].node == "risk"

    def test_disable_both_parallel(self):
        """禁用 risk+rag → 直跳 decision"""
        route = _get_router(["document", "rule", "decision"])
        state = {"failed_count": 0, "errors": []}
        result = route(state)
        assert result == "decision"

    def test_severe_takes_priority_over_enabled(self):
        """严重违规优先于 enabled_agents 过滤"""
        route = _get_router(["document", "rule", "risk", "rag", "decision"])
        state = {"failed_count": 3, "errors": []}
        result = route(state)
        assert result == "decision"
