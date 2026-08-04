"""
StateGraph 节点函数
将 5 个 Agent 调用封装为 StateGraph 兼容的节点（接收/返回 dict）

设计原则:
- 节点函数签名: (state: dict) -> dict（LangGraph 标准）
- 从 state 构建 context dict → 调 Agent → 返回状态更新 dict
- 异常不抛出，返回 errors 和兜底值
- RiskAgent fail-closed, DecisionAgent fail-review
- 复用 Phase 1 workflow_nodes.py 的异常处理逻辑
"""
import logging
from typing import Dict, Any, Optional

from app.agents.base_agent import BaseAgent
from app.agents.document_agent import DocumentAgent
from app.agents.rule_agent import RuleAgent
from app.agents.risk_agent import RiskAgent
from app.agents.rag_agent import RAGAgent
from app.agents.decision_agent import DecisionAgent

logger = logging.getLogger(__name__)


# ===== 辅助函数 =====

def _state_to_context(state: dict) -> dict:
    """将 AuditState dict 转为 Agent 兼容的 context"""
    return {
        "expense": state.get("expense"),
        "user_info": state.get("user_info", {}),
        "document_texts": state.get("document_texts", []),
        "document_result": state.get("document_result", {}),
        "rule_result": state.get("rule_result", {}),
        "risk_result": state.get("risk_result", {}),
        "rag_result": state.get("rag_result", {}),
        "history": state.get("history", []),
        "custom": state.get("custom_context"),
    }


def _to_ar(result: dict) -> dict:
    """将 Agent 返回转为 agent_results 条目"""
    return {
        "agent_name": result.get("agent_name", "unknown"),
        "status": result.get("status", "unknown"),
        "result": result.get("result", {}),
        "message": result.get("message", ""),
        "duration_ms": result.get("duration_ms", 0),
    }


def _error_ar(agent_name: str, error_msg: str) -> dict:
    """构造异常时的 agent_results 条目"""
    return {
        "agent_name": agent_name,
        "status": "failed",
        "result": {},
        "message": error_msg,
        "duration_ms": 0,
    }


# ===== 可配置的节点工厂 =====

def make_document_node():
    """工厂函数：创建 document 节点（无状态依赖）"""

    async def document_node(state: dict) -> dict:
        try:
            agent = DocumentAgent()
            result = await agent.execute(_state_to_context(state))
        except Exception as e:
            logger.error(f"[DocumentAgent] 异常: {e}", exc_info=True)
            return {
                "document_result": {},
                "errors": [{"node": "document", "error": str(e)}],
                "agent_results": [_error_ar("DocumentAgent", str(e))],
            }
        return {
            "document_result": result.get("result", {}),
            "agent_results": [_to_ar(result)],
        }

    return document_node


def make_rule_node(db=None):
    """工厂函数：创建 rule 节点（需要 db 连接）"""

    async def rule_node(state: dict) -> dict:
        try:
            agent = RuleAgent(db)
            result = await agent.execute(_state_to_context(state))
        except Exception as e:
            logger.error(f"[RuleAgent] 异常: {e}", exc_info=True)
            return {
                "rule_result": {},
                "failed_count": 0,
                "errors": [{"node": "rule", "error": str(e)}],
                "agent_results": [_error_ar("RuleAgent", str(e))],
            }
        summary = result.get("result", {}).get("summary", {})
        return {
            "rule_result": result.get("result", {}),
            "failed_count": summary.get("failed", 0),
            "agent_results": [_to_ar(result)],
        }

    return rule_node


def make_risk_node():
    """工厂函数：创建 risk 节点（fail-closed）"""

    async def risk_node(state: dict) -> dict:
        try:
            agent = RiskAgent()
            result = await agent.execute(_state_to_context(state))
            risk_result = result.get("result", {})
            return {
                "risk_result": risk_result,
                "agent_results": [_to_ar(result)],
            }
        except Exception as e:
            # fail-closed: 异常当最高风险
            logger.error(f"[RiskAgent] 异常(fail-closed): {e}", exc_info=True)
            risk_result = {
                "risk_level": "critical",
                "risk_score": 100,
                "risk_factors": [f"系统异常: {str(e)}"],
                "recommendations": ["系统异常，建议人工复核"],
            }
            return {
                "risk_result": risk_result,
                "agent_results": [{
                    "agent_name": "RiskAgent",
                    "status": "failed",
                    "result": risk_result,
                    "message": f"异常(已兜底critical): {str(e)}",
                    "duration_ms": 0,
                }],
            }

    return risk_node


def make_rag_node(retriever=None):
    """工厂函数：创建 rag 节点"""

    async def rag_node(state: dict) -> dict:
        try:
            agent = RAGAgent(retriever=retriever)
            result = await agent.execute(_state_to_context(state))
        except Exception as e:
            logger.error(f"[RAGAgent] 异常: {e}", exc_info=True)
            return {
                "rag_result": {"retrieved_docs": [], "error": str(e)},
                "agent_results": [_error_ar("RAGAgent", str(e))],
            }
        return {
            "rag_result": result.get("result", {}),
            "agent_results": [_to_ar(result)],
        }

    return rag_node


def make_decision_node():
    """工厂函数：创建 decision 节点（fail-review）"""

    async def decision_node(state: dict) -> dict:
        try:
            agent = DecisionAgent()
            result = await agent.execute(_state_to_context(state))
            decision_result = result.get("result", {})
        except Exception as e:
            logger.error(f"[DecisionAgent] 异常: {e}", exc_info=True)
            decision_result = {
                "decision": "review",
                "reason": f"系统异常: {str(e)}",
                "confidence": 0,
                "key_findings": ["决策模块异常，需人工判断"],
            }
            return {
                "decision_result": decision_result,
                "agent_results": [{
                    "agent_name": "DecisionAgent",
                    "status": "failed",
                    "result": decision_result,
                    "message": f"异常(已兜底review): {str(e)}",
                    "duration_ms": 0,
                }],
            }
        return {
            "decision_result": decision_result,
            "agent_results": [_to_ar(result)],
        }

    return decision_node
