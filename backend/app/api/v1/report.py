"""
报表统计接口 - 报销数据的多维度统计和分析
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_admin_or_finance_user
from app.dependencies import get_db
from app.models.user import User
from app.services.report_service import ReportService

router = APIRouter()


@router.get("/summary", summary="报销总览")
async def get_summary(
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    department: Optional[str] = Query(None, description="部门筛选"),
    current_user: User = Depends(get_admin_or_finance_user),
    db: AsyncSession = Depends(get_db),
):
    """获取报销总览数据 - 总金额、总笔数、各状态分布等"""
    service = ReportService(db)
    result = await service.get_summary(
        current_user,
        start_date=start_date,
        end_date=end_date,
        department=department,
    )
    return {"success": True, "data": result, "message": "获取成功"}


@router.get("/by-type", summary="按报销类型统计")
async def get_by_type(
    start_date: Optional[str] = Query(None, description="开始日期"),
    end_date: Optional[str] = Query(None, description="结束日期"),
    current_user: User = Depends(get_admin_or_finance_user),
    db: AsyncSession = Depends(get_db),
):
    """按报销类型分组统计金额和笔数"""
    service = ReportService(db)
    result = await service.get_by_type(
        current_user,
        start_date=start_date,
        end_date=end_date,
    )
    return {"success": True, "data": result, "message": "获取成功"}


@router.get("/by-department", summary="按部门统计")
async def get_by_department(
    start_date: Optional[str] = Query(None, description="开始日期"),
    end_date: Optional[str] = Query(None, description="结束日期"),
    current_user: User = Depends(get_admin_or_finance_user),
    db: AsyncSession = Depends(get_db),
):
    """按部门分组统计报销情况"""
    service = ReportService(db)
    result = await service.get_by_department(
        current_user,
        start_date=start_date,
        end_date=end_date,
    )
    return {"success": True, "data": result, "message": "获取成功"}


@router.get("/trend", summary="报销趋势")
async def get_trend(
    months: int = Query(default=12, ge=1, le=36, description="统计最近N个月"),
    current_user: User = Depends(get_admin_or_finance_user),
    db: AsyncSession = Depends(get_db),
):
    """获取报销金额的月度趋势"""
    service = ReportService(db)
    result = await service.get_trend(current_user, months=months)
    return {"success": True, "data": result, "message": "获取成功"}
