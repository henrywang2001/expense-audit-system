"""
LangGraph StateGraph 工作流状态定义

使用 TypedDict + Annotated reducer 定义 AuditState，
替代 Phase 1 的 WorkflowState dataclass

设计原则:
- 所有字段必须有默认值（TypedDict 约束）
- Annotated reducer 控制并行节点的合并行为
- 与旧 WorkflowState 的 as_dict 兼容，确保 Agent.execute() 不变
"""
from typing import TypedDict, Annotated, List, Any, Optional


def _merge_agent_results(left: list, right: list) -> list:
    """
    Annotated reducer: 按 agent_name 去重合并 agent_results

    并行节点（risk/rag）同时写 agent_results 时，
    此 reducer 确保按 agent_name 去重，后者覆盖前者。
    """
    merged = {}
    for r in left:
        name = r.get("agent_name", "")
        if name:
            merged[name] = r
    for r in right:
        name = r.get("agent_name", "")
        if name:
            merged[name] = r
    return list(merged.values())


class AuditState(TypedDict, total=False):
    """
    StateGraph 审计状态

    所有字段使用 total=False（均为可选），
    允许节点只返回部分字段的更新。
    """

    # ===== 输入（facade 预加载，节点只读） =====
    expense_id: int
    expense: Any                                          # Expense ORM 或 dict
    user_info: dict                                       # 用户信息
    custom_context: Optional[dict]                        # 自定义上下文
    history: List[dict]                                   # 用户历史报销记录
    document_texts: List[dict]                            # OCR 文本

    # ===== Agent 输出 =====
    document_result: dict                                 # DocumentAgent 输出
    rule_result: dict                                     # RuleAgent 输出
    risk_result: dict                                     # RiskAgent 输出
    rag_result: dict                                      # RAGAgent 输出
    decision_result: dict                                 # DecisionAgent 输出

    # ===== 控制字段 =====
    agent_results: Annotated[List[dict], _merge_agent_results]  # 聚合结果
    failed_count: int                                     # 规则违规数
    errors: List[dict]                                    # 节点错误记录
    enabled_agents: Optional[List[str]]                   # 启用的 Agent 列表

    # ===== 辅助 =====
    def as_dict(self) -> dict:
        """
        转为 dict 传给 Agent.execute(context)

        与旧 context dict 结构兼容，确保 5 个 Agent 的 execute() 无需修改
        """
        return {
            "expense": self.get("expense"),
            "user_info": self.get("user_info", {}),
            "document_texts": self.get("document_texts", []),
            "document_result": self.get("document_result", {}),
            "rule_result": self.get("rule_result", {}),
            "risk_result": self.get("risk_result", {}),
            "rag_result": self.get("rag_result", {}),
            "history": self.get("history", []),
            "custom": self.get("custom_context"),
        }
