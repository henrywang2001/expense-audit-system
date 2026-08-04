"""
测试共享 fixtures

提供 mock LLM、测试数据、路由验证辅助函数
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch


# ===== 测试数据 =====

@pytest.fixture
def normal_expense_dict():
    """正常报销单（dict 格式，msgpack 兼容）"""
    return {
        "id": 1,
        "title": "差旅报销",
        "expense_type": "travel",
        "total_amount": 1500.00,
        "description": "北京出差交通住宿",
        "user_id": 1,
        "items": [
            {"description": "高铁票", "amount": 500, "invoice_no": "INV001"},
            {"description": "酒店", "amount": 1000, "invoice_no": "INV002"},
        ],
    }


@pytest.fixture
def severe_expense_dict():
    """严重违规报销单"""
    return {
        "id": 2,
        "title": "大额招待",
        "expense_type": "entertainment",
        "total_amount": 50000.00,
        "description": "无明细的高额招待费",
        "user_id": 1,
        "items": [],
    }


@pytest.fixture
def user_info_dict():
    """用户信息"""
    return {
        "id": 1,
        "username": "testuser",
        "full_name": "Test User",
        "department": "Engineering",
        "position": "Engineer",
        "role": "employee",
    }


@pytest.fixture
def empty_history():
    """空历史记录"""
    return []


# ===== 状态 fixtures =====

@pytest.fixture
def normal_initial_state(normal_expense_dict, user_info_dict, empty_history):
    """正常流程的初始状态"""
    return {
        "expense_id": 1,
        "expense": normal_expense_dict,
        "user_info": user_info_dict,
        "custom_context": None,
        "history": empty_history,
        "document_texts": [],
        "document_result": {},
        "rule_result": {},
        "risk_result": {},
        "rag_result": {},
        "decision_result": {},
        "agent_results": [],
        "failed_count": 0,
        "errors": [],
        "enabled_agents": None,
    }


@pytest.fixture
def severe_initial_state(severe_expense_dict, user_info_dict, empty_history):
    """严重违规的初始状态"""
    return {
        "expense_id": 2,
        "expense": severe_expense_dict,
        "user_info": user_info_dict,
        "custom_context": None,
        "history": empty_history,
        "document_texts": [],
        "document_result": {},
        "rule_result": {},
        "risk_result": {},
        "rag_result": {},
        "decision_result": {},
        "agent_results": [],
        "failed_count": 0,
        "errors": [],
        "enabled_agents": None,
    }


# ===== Mock Agent 工厂 =====

def make_mock_agent_result(agent_name: str) -> dict:
    """创建一个标准 Agent 执行结果"""
    return {
        "agent_name": agent_name,
        "status": "success",
        "result": {},
        "message": "",
        "duration_ms": 1,
    }


def make_mock_node(agent_name: str = "MockAgent"):
    """
    创建一个 mock 节点函数，返回标准的 agent_result

    使用方式:
        mock = make_mock_node("DocumentAgent")
        result = await mock(state_dict)
    """
    async def _mock(state):
        return {
            "agent_results": [make_mock_agent_result(agent_name)],
        }
    return _mock


def make_mock_rule_node(failed_count: int = 0):
    """创建一个 mock rule 节点，返回指定的 failed_count"""
    async def _mock(state):
        return {
            "rule_result": {
                "rule_checks": {},
                "summary": {
                    "passed": 5 - failed_count,
                    "warnings": failed_count,
                    "failed": failed_count,
                    "total_risk": "high" if failed_count >= 2 else "low",
                },
                "total_rules": 5,
                "passed": 5 - failed_count,
                "warnings": failed_count,
                "failed": failed_count,
            },
            "failed_count": failed_count,
            "agent_results": [make_mock_agent_result("RuleAgent")],
        }
    return _mock


# ===== Mock LLM =====

@pytest.fixture
def mock_llm_json():
    """Mock LLM 返回合法 JSON"""
    with patch("app.agents.base_agent.BaseAgent.chat_json", new_callable=AsyncMock) as mock:
        mock.return_value = {"status": "ok", "summary": "test response"}
        yield mock


# ===== Async 辅助 =====

def async_test(f):
    """装饰器：自动包装 async 测试函数"""
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))
    return wrapper
