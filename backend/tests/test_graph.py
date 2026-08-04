"""
StateGraph 编译和结构测试

验证:
1. 图可以正常编译
2. 所有期望节点存在
3. 关键边存在（主线 + fan-out + fan-in + 短路）
4. Send fan-out 逻辑正确
"""
import pytest
from langgraph.graph import StateGraph, START, END


class TestGraphCompilation:
    """图编译测试"""

    def test_graph_compiles(self):
        """build_audit_graph() 返回可编译的图"""
        from app.agents.graph.builder import build_audit_graph

        app = build_audit_graph()
        assert app is not None
        # 检查编译后的类型
        from langgraph.graph.state import CompiledStateGraph
        assert isinstance(app, CompiledStateGraph), \
            f"Expected CompiledStateGraph, got {type(app)}"

    def test_graph_compiles_without_checkpointer(self):
        """不传 checkpointer 也能正常编译"""
        from app.agents.graph.builder import build_audit_graph

        app = build_audit_graph(checkpointer=None)
        assert app is not None

    def test_all_nodes_present(self):
        """所有 5 个业务节点 + __start__ + __end__ 都存在"""
        from app.agents.graph.builder import build_audit_graph

        app = build_audit_graph()
        nodes = app.get_graph().nodes
        expected = {"__start__", "__end__", "document", "rule", "risk", "rag", "decision"}
        actual = set(nodes.keys())
        assert actual == expected, f"Missing nodes: {expected - actual}, Extra: {actual - expected}"

    def test_mainline_edges(self):
        """主线: START → document → rule"""
        from app.agents.graph.builder import build_audit_graph

        app = build_audit_graph()
        edges = app.get_graph().edges

        edge_pairs = {(e.source, e.target) for e in edges}
        assert ("__start__", "document") in edge_pairs, "Missing START → document"
        assert ("document", "rule") in edge_pairs, "Missing document → rule"

    def test_fan_in_edges(self):
        """fan-in: risk → decision 和 rag → decision"""
        from app.agents.graph.builder import build_audit_graph

        app = build_audit_graph()
        edge_pairs = {(e.source, e.target) for e in app.get_graph().edges}

        assert ("risk", "decision") in edge_pairs, "Missing risk → decision"
        assert ("rag", "decision") in edge_pairs, "Missing rag → decision"

    def test_end_edge(self):
        """decision → END"""
        from app.agents.graph.builder import build_audit_graph

        app = build_audit_graph()
        edge_pairs = {(e.source, e.target) for e in app.get_graph().edges}

        assert ("decision", "__end__") in edge_pairs, "Missing decision → END"

    def test_conditional_edges_exist(self):
        """rule 节点有条件边（用于路由）"""
        from app.agents.graph.builder import build_audit_graph

        app = build_audit_graph()
        graph = app.get_graph()

        # rule 节点的出边应包含到 decision 和到 risk+rag 的路径
        edge_pairs = {(e.source, e.target) for e in graph.edges}
        assert ("rule", "decision") in edge_pairs, "Missing conditional edge: rule → decision"
        assert ("rule", "risk") in edge_pairs, "Missing conditional edge: rule → risk"
        assert ("rule", "rag") in edge_pairs, "Missing conditional edge: rule → rag"


class TestSendFanOut:
    """Send 并行分发测试"""

    def test_send_creates_two_tasks(self):
        """fan-out 应返回 2 个 Send 对象（enabled_agents=None）"""
        from app.agents.graph.builder import _make_route_factory
        from langgraph.types import Send

        route = _make_route_factory(enabled_agents=None)
        state = {"failed_count": 0, "errors": []}
        result = route(state)

        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(s, Send) for s in result)

    def test_send_targets_are_risk_and_rag(self):
        """Send 目标节点必须是 risk 和 rag"""
        from app.agents.graph.builder import _make_route_factory

        route = _make_route_factory(enabled_agents=None)
        state = {"failed_count": 0, "errors": []}
        result = route(state)

        targets = {s.node for s in result}
        assert targets == {"risk", "rag"}

    def test_send_carries_state(self):
        """每个 Send 携带当前 state"""
        from app.agents.graph.builder import _make_route_factory

        route = _make_route_factory(enabled_agents=None)
        state = {
            "failed_count": 0,
            "errors": [],
            "expense_id": 42,
            "document_result": {"extracted_data": {"invoice_no": "INV123"}},
        }
        result = route(state)

        for send in result:
            assert send.arg == state, f"Send should carry the original state"


class TestNodeFactories:
    """节点工厂函数测试"""

    def test_all_factories_return_callable(self):
        """5 个工厂函数都应返回可调用的 async 函数"""
        from app.agents.graph.nodes import (
            make_document_node, make_rule_node, make_risk_node,
            make_rag_node, make_decision_node,
        )
        import asyncio

        factories = [
            ("document", make_document_node()),
            ("rule", make_rule_node()),
            ("risk", make_risk_node()),
            ("rag", make_rag_node()),
            ("decision", make_decision_node()),
        ]

        for name, fn in factories:
            assert callable(fn), f"{name} node should be callable"
            assert asyncio.iscoroutinefunction(fn), \
                f"{name} node should be async"

    def test_node_returns_dict_with_agent_results(self):
        """节点执行后应返回包含 agent_results 的 dict"""
        import asyncio
        from app.agents.graph.nodes import make_document_node
        from unittest.mock import patch, AsyncMock

        async def _test():
            node = make_document_node()

            # Mock DocumentAgent.execute 避免真实 LLM 调用
            async def mock_execute(self, ctx):
                return {
                    "agent_name": "DocumentAgent",
                    "status": "success",
                    "result": {"extracted_data": {}},
                    "message": "ok",
                    "duration_ms": 1,
                }

            with patch("app.agents.graph.nodes.DocumentAgent.execute", mock_execute):
                state = {
                    "expense": {"id": 1, "title": "test"},
                    "user_info": {},
                    "document_texts": [],
                    "document_result": {},
                    "rule_result": {},
                    "risk_result": {},
                    "rag_result": {},
                    "history": [],
                    "custom_context": None,
                }
                result = await node(state)

            assert isinstance(result, dict), f"Expected dict, got {type(result)}"
            assert "agent_results" in result, "Missing agent_results key"
            assert len(result["agent_results"]) >= 1, "Should have at least 1 result"

        asyncio.run(_test())
