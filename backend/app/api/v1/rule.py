"""
规则管理接口 — 规则的增删改查

规则以 json-logic 对象存储, 通过 RuleEngine 确定性求值;
创建/更新时通过 validate_rule_ast 静态校验 logic 合法性。
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_admin_or_finance_user, get_current_user
from app.dependencies import get_db
from app.models.user import User
from app.models.rule import Rule, RuleType
from app.schemas.rule import (
    RuleCreate, RuleUpdate, RuleResponse,
    RuleDef, RuleListResponse,
)
from app.core.rule_engine import validate_rule_ast, RuleError
from app.core.exceptions import BadRequestException, NotFoundException

router = APIRouter()


# ========== 辅助 ==========

def _rule_to_response(rule: Rule) -> dict:
    """将 ORM 对象转为 response 字典 (含 computed 字段)"""
    logic = rule.structured_condition or {}
    if not isinstance(logic, dict):
        logic = {}
    return {
        "id": rule.id,
        "name": rule.name,
        "rule_type": (
            rule.rule_type.value
            if hasattr(rule.rule_type, "value")
            else str(rule.rule_type)
        ),
        "logic": logic,
        "action": rule.action,
        "message": f"{rule.name}不符合规则",
        "description": rule.condition,
        "exec_mode": (rule.exec_mode or "semantic"),
        "is_active": bool(rule.is_active),
    }


async def _get_rule_or_404(rule_id: int, db: AsyncSession) -> Rule:
    """根据 ID 获取规则, 不存在则 404"""
    result = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule = result.scalar_one_or_none()
    if rule is None:
        raise NotFoundException(message=f"规则不存在: id={rule_id}")
    return rule


def _validate_logic(logic: dict) -> None:
    """校验 json-logic 对象合法性, 不通过抛 BadRequestException"""
    if not isinstance(logic, dict) or not logic:
        raise BadRequestException(message="规则 logic 不能为空, 必须是 json-logic 对象")
    try:
        validate_rule_ast(logic)
    except RuleError as e:
        raise BadRequestException(message=f"规则定义非法: {e}")


# ========== CRUD ==========

@router.get("", response_model=RuleListResponse, summary="获取规则列表")
async def list_rules(
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=50, ge=1, le=200, description="每页数量"),
    rule_type: Optional[str] = Query(None, description="规则类型筛选"),
    is_active: Optional[bool] = Query(None, description="启用状态筛选"),
    exec_mode: Optional[str] = Query(None, description="执行模式筛选"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取规则列表, 支持分页和筛选.

    管理员/财务可查看全部, 普通用户只能看启用的规则.
    """
    query = select(Rule).order_by(Rule.id.desc())

    if rule_type:
        try:
            rt = RuleType(rule_type)
        except ValueError:
            raise BadRequestException(
                message=f"无效的规则类型: {rule_type}"
            )
        query = query.where(Rule.rule_type == rt)
    if is_active is not None:
        query = query.where(Rule.is_active == is_active)
    if exec_mode:
        query = query.where(Rule.exec_mode == exec_mode)

    # 计数
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # 分页
    offset = (page - 1) * page_size
    result = await db.execute(query.offset(offset).limit(page_size))
    rules = result.scalars().all()

    return RuleListResponse(
        total=total,
        items=[RuleResponse(**_rule_to_response(r)) for r in rules],
    )


@router.get("/{rule_id}", response_model=RuleResponse, summary="获取规则详情")
async def get_rule(
    rule_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取单条规则详情"""
    rule = await _get_rule_or_404(rule_id, db)
    return RuleResponse(**_rule_to_response(rule))


@router.post("", response_model=RuleResponse, summary="创建规则")
async def create_rule(
    rule_data: RuleCreate,
    current_user: User = Depends(get_admin_or_finance_user),
    db: AsyncSession = Depends(get_db),
):
    """
    创建新规则 (需要管理员/财务权限).

    logic 必须是合法的 json-logic 对象, 创建时自动静态校验.
    """
    _validate_logic(rule_data.logic)

    try:
        rt = RuleType(rule_data.rule_type)
    except ValueError:
        raise BadRequestException(
            message=f"无效的规则类型: {rule_data.rule_type}"
        )

    db_rule = Rule(
        name=rule_data.name,
        rule_type=rt,
        condition=rule_data.description or rule_data.name,
        action=rule_data.action,
        config=None,
        structured_condition=rule_data.logic,
        exec_mode=rule_data.exec_mode,
        is_active=True,
    )
    db.add(db_rule)
    await db.commit()
    await db.refresh(db_rule)

    return RuleResponse(**_rule_to_response(db_rule))


@router.put("/{rule_id}", response_model=RuleResponse, summary="更新规则")
async def update_rule(
    rule_id: int,
    rule_data: RuleUpdate,
    current_user: User = Depends(get_admin_or_finance_user),
    db: AsyncSession = Depends(get_db),
):
    """
    更新规则 (需要管理员/财务权限).

    只更新显式传了的字段, logic 的合法性会在更新时校验.
    """
    rule = await _get_rule_or_404(rule_id, db)

    if rule_data.name is not None:
        rule.name = rule_data.name
    if rule_data.rule_type is not None:
        try:
            rule.rule_type = RuleType(rule_data.rule_type)
        except ValueError:
            raise BadRequestException(
                message=f"无效的规则类型: {rule_data.rule_type}"
            )
    if rule_data.logic is not None:
        _validate_logic(rule_data.logic)
        rule.structured_condition = rule_data.logic
    if rule_data.action is not None:
        rule.action = rule_data.action
    if rule_data.message is not None:
        rule.message = rule_data.message
    if rule_data.description is not None:
        rule.condition = rule_data.description
    if rule_data.exec_mode is not None:
        rule.exec_mode = rule_data.exec_mode
    if rule_data.is_active is not None:
        rule.is_active = rule_data.is_active

    await db.commit()
    await db.refresh(rule)

    return RuleResponse(**_rule_to_response(rule))


@router.delete("/{rule_id}", response_model=dict, summary="停用规则(软删除)")
async def delete_rule(
    rule_id: int,
    current_user: User = Depends(get_admin_or_finance_user),
    db: AsyncSession = Depends(get_db),
):
    """
    停用规则 (软删除, 即 is_active=False).

    规则不会从数据库中删除, 只是不再被引擎加载.
    """
    rule = await _get_rule_or_404(rule_id, db)
    rule.is_active = False
    await db.commit()

    return {
        "success": True,
        "message": f"规则 '{rule.name}' 已停用",
        "rule_id": rule_id,
    }
