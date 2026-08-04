"""
API v1 主路由 - 注册所有子路由
"""
from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.expense import router as expense_router
from app.api.v1.approval import router as approval_router
from app.api.v1.agent import router as agent_router
from app.api.v1.report import router as report_router
from app.api.v1.rule import router as rule_router

api_v1_router = APIRouter(prefix="/api/v1")

# 注册各模块路由
api_v1_router.include_router(auth_router, prefix="/auth", tags=["认证"])
api_v1_router.include_router(expense_router, prefix="/expenses", tags=["报销管理"])
api_v1_router.include_router(approval_router, prefix="/approvals", tags=["审批管理"])
api_v1_router.include_router(agent_router, prefix="/agent", tags=["AI智能审核"])
api_v1_router.include_router(report_router, prefix="/reports", tags=["报表统计"])
api_v1_router.include_router(rule_router, prefix="/rules", tags=["规则管理"])
