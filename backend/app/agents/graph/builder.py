"""
StateGraph 构建器
构建报销审核工作流的 StateGraph: 条件路由 + Send 并行 + AsyncSqliteSaver

图结构:
  START -> document -> rule -> (条件路由)
    - 严重违规(>=2) 或异常: rule -> decision (跳过 risk+rag)
    - 正常: rule 直接 via Send fan-out -> [risk, rag] (并行) -> decision -> END

enabled_agents 支持:
  当 enabled_agents 不为 None 时，禁用的节点替换为 pass-through，
  条件路由自动调整：禁用的 risk/rag 不参与 fan-out。
"""
import logging
from typing import Optional, List

from langgraph.graph import StateGraph, START, END
from langgraph.types import Send

from app.agents.graph.state import AuditState
from app.agents.graph.nodes import (
    make_document_node,
    make_rule_node,
    make_risk_node,
    make_rag_node,
    make_decision_node,
)

logger = logging.getLogger(__name__)

# 严重违规阈值（与 RuleAgent._summarize_rules 和 DecisionAgent._fallback_decision 对齐）
SEVERE_FAIL_THRESHOLD = 2


def _is_enabled(enabled_agents: Optional[List[str]], name: str) -> bool:
    """判断指定 agent 是否启用"""
    if enabled_agents is None:
        return True
    return name in enabled_agents


def _make_passthrough(name: str):
    """创建一个 pass-through 节点：不做任何事，透传 state"""
    async def _passthrough(state: dict) -> dict:
        logger.info(f"[Graph] {name} 节点被禁用，透传跳过")
        return {}
    return _passthrough


def _make_route_factory(enabled_agents: Optional[List[str]]):
    """
    工厂函数：创建带 enabled_agents 感知的路由函数

    返回一个闭包 _route_after_rule(state)，在判断路由时考虑哪些节点被启用。
    """
    risk_enabled = _is_enabled(enabled_agents, "risk")
    rag_enabled = _is_enabled(enabled_agents, "rag")

    def _route_after_rule(state: AuditState):
        """
        规则校验后的条件路由

        返回:
        - list[Send]: fan-out 到启用的 risk/rag 并行
        - "decision": 严重违规/异常，或 risk+rag 均被禁用时
        """
        failed = state.get("failed_count", 0)
        errors = state.get("errors", [])

        has_critical_error = any(
            e.get("node") in ("document", "rule") for e in errors
        )

        if failed >= SEVERE_FAIL_THRESHOLD or has_critical_error:
            logger.info(
                f"[Graph] 条件路由: 短路跳过 risk+rag "
                f"(failed={failed}, errors={len(errors)})"
            )
            return "decision"

        # 正常路径：只 fan-out 到启用的节点
        targets = []
        if risk_enabled:
            targets.append(Send("risk", state))
        if rag_enabled:
            targets.append(Send("rag", state))

        if not targets:
            # risk 和 rag 都被禁用 → 直跳 decision
            return "decision"

        return targets

    return _route_after_rule


def build_audit_graph(
    db=None,
    user=None,
    enabled_agents: Optional[List[str]] = None,
    checkpointer=None,
):
    """
    构建并编译报销审核 StateGraph

    Args:
        db: 数据库会话（传给 RuleAgent）
        user: 当前用户（预留，暂未使用）
        enabled_agents: 启用的 Agent 列表（None=全部启用）
                       例: ["document", "rule", "decision"] → 禁用 risk+rag
        checkpointer: 可选的 checkpoint 存储器

    Returns:
        编译后的 CompiledStateGraph
    """
    # —— 创建节点（禁用的替换为 pass-through） ——
    if _is_enabled(enabled_agents, "document"):
        doc_node_fn = make_document_node()
    else:
        doc_node_fn = _make_passthrough("document")

    if _is_enabled(enabled_agents, "rule"):
        rule_node_fn = make_rule_node(db)
    else:
        rule_node_fn = _make_passthrough("rule")

    risk_node_fn = make_risk_node() if _is_enabled(enabled_agents, "risk") else _make_passthrough("risk")
    rag_node_fn = make_rag_node() if _is_enabled(enabled_agents, "rag") else _make_passthrough("rag")
    dec_node_fn = make_decision_node() if _is_enabled(enabled_agents, "decision") else _make_passthrough("decision")

    # —— 构建图 ——
    g = StateGraph(AuditState)

    g.add_node("document", doc_node_fn)
    g.add_node("rule", rule_node_fn)
    g.add_node("risk", risk_node_fn)
    g.add_node("rag", rag_node_fn)
    g.add_node("decision", dec_node_fn)

    # 主线: START -> document -> rule（始终执行）
    g.add_edge(START, "document")
    g.add_edge("document", "rule")

    # 条件路由: 使用 enabled_agents 感知的路由函数
    route_fn = _make_route_factory(enabled_agents)
    g.add_conditional_edges(
        "rule",
        route_fn,
        path_map=["risk", "rag", "decision"],
    )

    # fan-in: risk + rag 都完成后汇聚到 decision
    g.add_edge(["risk", "rag"], "decision")

    # decision -> END
    g.add_edge("decision", END)

    # —— 编译 ——
    return g.compile(checkpointer=checkpointer)
