"""
规则引擎 schema — RuleDef + CRUD 入参/出参

RuleDef: 规则的内部表示，logic 字段存 json-logic 对象
RuleCreate / RuleResponse: 规则管理 API 的入参/出参
"""
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


# ========== 规则执行模式 ==========

RuleExecMode = Literal["deterministic", "pre_computed", "semantic"]
"""
- deterministic: json-logic 直接求值, 零次 LLM 调用
- pre_computed: build_data 预计算后再 json-logic 求值, 零次 LLM 调用
- semantic:      LLM 语义判断 (招待费备注是否合理等)"
"""


# ========== 规则内部表示 (给 RuleEngine 用) ==========

class RuleDef(BaseModel):
    """一条可被 RuleEngine 求值的规则"""
    name: str = Field(..., description="规则名称")
    rule_type: str = Field(..., description="规则类型 (amount_limit/compliance/time/…)")
    logic: Dict[str, Any] = Field(
        ...,
        description="json-logic 对象, 真正被求值的部分。例: {'<=':[{'var':'total_amount'},5000]}"
    )
    action: Literal["reject", "warn", "require_approval"] = Field(
        ..., description="规则命中后的动作"
    )
    message: str = Field(..., description="规则命中后的提示文案")
    description: Optional[str] = Field(None, description="人类可读规则说明")
    exec_mode: RuleExecMode = Field(
        default="deterministic",
        description="执行模式: deterministic / pre_computed / semantic"
    )
    is_active: bool = Field(default=True, description="是否启用")

    class Config:
        # 允许直接传 dict 构造（方便从 DB/文件读取后转换）
        extra = "ignore"


# ========== CRUD Schema ==========

class RuleCreate(BaseModel):
    """创建规则请求"""
    name: str = Field(..., min_length=1, max_length=200, description="规则名称")
    rule_type: str = Field(
        ..., description="规则类型, 对应 RuleType 枚举值"
    )
    logic: Dict[str, Any] = Field(
        ..., description="json-logic 规则对象"
    )
    action: Literal["reject", "warn", "require_approval"] = Field(
        ..., description="规则动作"
    )
    message: str = Field(..., min_length=1, max_length=500, description="命中提示")
    description: Optional[str] = Field(None, max_length=500, description="人类可读说明")
    exec_mode: RuleExecMode = Field(
        default="deterministic", description="执行模式"
    )


class RuleUpdate(BaseModel):
    """更新规则请求 — 所有字段可选"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    rule_type: Optional[str] = None
    logic: Optional[Dict[str, Any]] = None
    action: Optional[Literal["reject", "warn", "require_approval"]] = None
    message: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = Field(None, max_length=500)
    exec_mode: Optional[RuleExecMode] = None
    is_active: Optional[bool] = None


class RuleResponse(BaseModel):
    """规则查询响应"""
    id: int
    name: str
    rule_type: str
    logic: Dict[str, Any]
    action: str
    message: str
    description: Optional[str] = None
    exec_mode: RuleExecMode = "deterministic"
    is_active: bool = True

    class Config:
        from_attributes = True


class RuleListResponse(BaseModel):
    """规则列表响应"""
    total: int
    items: List[RuleResponse]
