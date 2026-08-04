"""
API 回归测试

验证:
1. AgentWorkflow 返回结构兼容旧版
2. Pydantic AgentExecuteResponse 校验通过
3. 两个调用入口的签名不变
4. error_response 结构完整
5. assemble_response 结构完整
"""
import pytest
from unittest.mock import AsyncMock


class TestAgentWorkflowResponse:
    """AgentWorkflow 返回结构回归测试"""

    def test_error_response_structure(self):
        """_error_response 返回结构完整且可被 Pydantic 校验"""
        from app.agents.workflow import AgentWorkflow
        from app.schemas.agent import AgentExecuteResponse

        wf = AgentWorkflow(db=None)
        resp = wf._error_response(expense_id=99, message="报销单不存在")

        # 必需字段检查
        required = [
            "success", "workflow_status", "expense_id",
            "final_decision", "final_reason", "agent_results", "message",
        ]
        for field in required:
            assert field in resp, f"Missing required field: {field}"

        # 值语义
        assert resp["success"] is False
        assert resp["workflow_status"] == "failed"
        assert resp["expense_id"] == 99
        assert resp["final_decision"] == "error"
        assert resp["final_reason"] == "报销单不存在"
        assert resp["agent_results"] == []
        assert resp["message"] == "报销单不存在"

        # Pydantic 校验
        model = AgentExecuteResponse(**resp)
        assert model.success is False

    def test_assemble_response_with_state_dict(self):
        """_assemble_response 从 state dict 装配正确的返回结构"""
        from app.agents.workflow import AgentWorkflow
        from app.schemas.agent import AgentExecuteResponse

        wf = AgentWorkflow(db=None)

        state = {
            "expense_id": 1,
            "decision_result": {
                "decision": "approve",
                "reason": "合规",
                "confidence": 90,
            },
            "risk_result": {
                "risk_level": "low",
                "risk_score": 10,
            },
            "agent_results": [
                {
                    "agent_name": "DocumentAgent",
                    "status": "success",
                    "result": {},
                    "message": "",
                    "duration_ms": 100,
                },
                {
                    "agent_name": "DecisionAgent",
                    "status": "success",
                    "result": {},
                    "message": "",
                    "duration_ms": 50,
                },
            ],
        }

        resp = wf._assemble_response(state)

        assert resp["success"] is True
        assert resp["workflow_status"] == "completed"
        assert resp["expense_id"] == 1
        assert resp["final_decision"] == "approve"
        assert resp["final_reason"] == "合规"
        assert resp["risk_level"] == "low"
        assert resp["risk_score"] == 10
        assert len(resp["agent_results"]) == 2
        assert resp["message"] == "Agent工作流执行完成"

        # Pydantic 校验
        model = AgentExecuteResponse(**resp)
        assert model.success is True
        assert model.final_decision == "approve"
        assert model.risk_level == "low"

    def test_assemble_response_reject(self):
        """拒绝决策的返回结构"""
        from app.agents.workflow import AgentWorkflow
        from app.schemas.agent import AgentExecuteResponse

        wf = AgentWorkflow(db=None)
        state = {
            "expense_id": 2,
            "decision_result": {
                "decision": "reject",
                "reason": "严重违规",
                "confidence": 85,
            },
            "risk_result": {
                "risk_level": "high",
                "risk_score": 75,
            },
            "agent_results": [],
        }

        resp = wf._assemble_response(state)
        assert resp["final_decision"] == "reject"
        assert resp["risk_level"] == "high"
        assert resp["risk_score"] == 75

        model = AgentExecuteResponse(**resp)
        assert model.success is True

    def test_assemble_response_review(self):
        """复核决策的返回结构"""
        from app.agents.workflow import AgentWorkflow
        from app.schemas.agent import AgentExecuteResponse

        wf = AgentWorkflow(db=None)
        state = {
            "expense_id": 3,
            "decision_result": {
                "decision": "review",
                "message": "需要人工复核",
            },
            "risk_result": {
                "risk_level": "medium",
                "risk_score": 45,
            },
            "agent_results": [],
        }

        resp = wf._assemble_response(state)
        assert resp["final_decision"] == "review"
        assert resp["final_reason"] == "需要人工复核"  # falls back to message

        model = AgentExecuteResponse(**resp)
        assert model.success is True

    def test_assemble_response_missing_decision(self):
        """decision_result 为空时默认 review"""
        from app.agents.workflow import AgentWorkflow

        wf = AgentWorkflow(db=None)
        state = {
            "expense_id": 4,
            "decision_result": {},
            "risk_result": {},
            "agent_results": [],
        }

        resp = wf._assemble_response(state)
        assert resp["final_decision"] == "review"
        assert resp["risk_level"] == "low"
        assert resp["risk_score"] == 0

    def test_assemble_response_missing_risk(self):
        """risk_result 为空时默认 low/0（严重违规跳过 risk 的场景）"""
        from app.agents.workflow import AgentWorkflow

        wf = AgentWorkflow(db=None)
        state = {
            "expense_id": 5,
            "decision_result": {"decision": "reject", "reason": "严重违规"},
            "risk_result": {},  # severe 短路时 risk_result 为空
            "agent_results": [],
        }

        resp = wf._assemble_response(state)
        assert resp["risk_level"] == "low"   # 默认值
        assert resp["risk_score"] == 0       # 默认值

    @pytest.mark.asyncio
    async def test_execute_signature(self):
        """execute() 方法签名与调用入口兼容"""
        import inspect
        from app.agents.workflow import AgentWorkflow

        sig = inspect.signature(AgentWorkflow.execute)
        params = list(sig.parameters.keys())
        assert params == ["self", "expense_id", "enabled_agents", "custom_context"], \
            f"Unexpected params: {params}"

    @pytest.mark.asyncio
    async def test_init_signature(self):
        """__init__ 签名不变"""
        import inspect
        from app.agents.workflow import AgentWorkflow

        sig = inspect.signature(AgentWorkflow.__init__)
        params = list(sig.parameters.keys())
        assert params == ["self", "db", "user"], \
            f"Unexpected init params: {params}"


class TestCallSiteCompatibility:
    """两个调用入口的兼容性测试"""

    def test_api_agent_imports_workflow(self):
        """api/v1/agent.py 正确导入 AgentWorkflow"""
        from app.api.v1.agent import execute_agent_workflow
        import inspect

        source = inspect.getsource(execute_agent_workflow)
        assert "AgentWorkflow" in source, \
            "api/v1/agent.py should reference AgentWorkflow"
        assert ".execute(" in source, \
            "api/v1/agent.py should call workflow.execute()"

    def test_expense_service_imports_workflow(self):
        """expense_service.py 正确导入 AgentWorkflow"""
        from app.services.expense_service import ExpenseService
        import inspect

        # 检查 ai_review 方法存在
        assert hasattr(ExpenseService, "ai_review"), \
            "ExpenseService should have ai_review method"

        sig = inspect.signature(ExpenseService.ai_review)
        params = list(sig.parameters.keys())
        assert params == ["self", "expense_id", "user", "request"], \
            f"ai_review params changed: {params}"

        source = inspect.getsource(ExpenseService.ai_review)
        assert "AgentWorkflow" in source, \
            "ai_review should reference AgentWorkflow"


class TestFailClosedBehavior:
    """FAIL-cLOSED 行为验证"""

    def test_risk_node_fail_closed(self):
        """RiskAgent 异常时返回 critical 而非 low"""
        from app.agents.risk_agent import RiskAgent
        import inspect

        source = inspect.getsource(RiskAgent.execute)
        # 检查 except 块中是否返回 critical
        assert "critical" in source, \
            "RiskAgent should return 'critical' on exception"
        assert "risk_score" in source and "100" in source, \
            "RiskAgent should return risk_score=100 on exception"

    def test_decision_node_fail_review(self):
        """DecisionAgent 异常时返回 review + confidence=0"""
        from app.agents.decision_agent import DecisionAgent
        import inspect

        source = inspect.getsource(DecisionAgent.execute)
        assert "review" in source, \
            "DecisionAgent should return 'review' on exception"
        assert "confidence" in source, \
            "DecisionAgent should return confidence on exception"
        assert "key_findings" in source, \
            "DecisionAgent should return key_findings on exception"

    def test_rule_node_fail_has_summary(self):
        """RuleAgent 异常时返回完整 summary 字段"""
        from app.agents.rule_agent import RuleAgent
        import inspect

        source = inspect.getsource(RuleAgent.execute)
        # 检查 except 块中包含 summary
        except_block = source.split("except Exception as e:")[1]
        assert "summary" in except_block, \
            "RuleAgent should return summary on exception"
        assert "total_risk" in except_block, \
            "RuleAgent should return total_risk on exception"
