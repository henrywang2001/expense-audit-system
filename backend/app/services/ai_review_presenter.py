"""
AI 审核结果展示层收敛（presenter）

职责
----
把 ``AgentWorkflow.execute()`` 返回的「工作流原始结构」
（``final_reason`` / ``agent_results`` / ``risk_level`` / ``risk_score``）
收敛为前端 AI 审核卡片直接消费的展示字段：

============  ==========  ====================================================
字段            类型        说明
============  ==========  ====================================================
summary       str         审核摘要（非空）
issues        list[dict]  发现的问题，每项 ``{severity, description, type}``
suggestions   list[str]   改进建议
risk_level    str         ``low`` / ``medium`` / ``high`` / ``critical``
risk_score    float       0-100
============  ==========  ====================================================

设计约束
--------
1. **纯函数、无副作用**：不依赖 DB / ORM / 网络，便于单测。
2. **只加不减**：``enrich_review_result`` 返回 ``{**原结果, **展示字段}``，
   绝不删除或改写 workflow 已有的键（``workflow_status`` /
   ``final_decision`` / ``agent_results`` 等原样保留）→ 向后兼容。
3. **对残缺输入必须给出合法输出**：agent 输出来自 LLM，键名/类型均不可信，
   任何缺字段、类型错乱、中文枚举值都要能兜底成合法展示数据。

数据来源（agent_results 中各 Agent 的 ``result`` 字段）
------------------------------------------------------
- ``RuleAgent.result.rule_checks``  → issues（status: fail/error→high, warn→medium）
- ``RiskAgent.result.risk_factors`` → issues（severity 由 risk_level 推导）
- ``RiskAgent.result.risk_level/risk_score/recommendations``
- ``DecisionAgent.result.suggestions/risk_mitigation``
- 任何 ``status == "failed"`` 的 Agent → 一条 system 类型的 issue
"""
import logging
from typing import Any, Dict, Iterable, List, Optional

logger = logging.getLogger(__name__)

# ===== 常量 =====

#: 合法风险等级（与前端 getRiskLabel / getRiskTagType 的映射保持一致）
VALID_RISK_LEVELS: tuple = ("low", "medium", "high", "critical")

#: 风险等级 → 兜底分数（当 risk_score 缺失或非数值时使用）
_LEVEL_TO_SCORE: Dict[str, float] = {
    "low": 10.0,
    "medium": 45.0,
    "high": 75.0,
    "critical": 95.0,
}

#: 风险等级严重度排序（用于"只上调不下调"的兜底比较）
_LEVEL_ORDER: Dict[str, int] = {
    "low": 0, "medium": 1, "high": 2, "critical": 3,
}

#: 风险等级 → issue severity（前端只识别 high / medium / 其它按"轻微"渲染）
_LEVEL_TO_SEVERITY: Dict[str, str] = {
    "low": "low",
    "medium": "medium",
    "high": "high",
    "critical": "high",
}

#: 规则校验 status → issue severity
_RULE_STATUS_TO_SEVERITY: Dict[str, str] = {
    "fail": "high",
    "error": "high",
    "warn": "medium",
}

#: 风险等级别名归一化（LLM 可能返回中文或非标准写法）
_RISK_LEVEL_ALIASES: Dict[str, str] = {
    "low": "low", "l": "low", "低": "low", "低风险": "low", "轻微": "low",
    "minor": "low", "none": "low", "safe": "low",
    "medium": "medium", "mid": "medium", "middle": "medium",
    "moderate": "medium", "中": "medium", "中等": "medium",
    "中风险": "medium", "一般": "medium", "normal": "medium",
    "high": "high", "h": "high", "高": "high", "高风险": "high",
    "较高": "high",
    "critical": "critical", "very_high": "critical", "very high": "critical",
    "extreme": "critical", "severe": "critical", "极高": "critical",
    "极高风险": "critical", "重大": "critical", "危急": "critical",
    "严重": "critical", "严重风险": "critical",
}

#: 决策 → 无建议时的兜底建议
_DECISION_FALLBACK_SUGGESTIONS: Dict[str, str] = {
    "approve": "本单未发现明显问题，归档前请留存发票原件以备抽查。",
    "reject": "请补充完整的合规凭证与说明后重新提交。",
    "review": "建议人工复核报销明细与发票真实性后再做审批决定。",
    "error": "AI 审核未能正常完成，请人工复核该报销单。",
}

#: 输出体积上限，防止 JSON 列膨胀
_MAX_ISSUES: int = 20
_MAX_SUGGESTIONS: int = 10
_MAX_TEXT_LEN: int = 500


# ===== 基础工具 =====

def _clean_text(value: Any) -> str:
    """把任意值收敛为去空白、限长的字符串；非法值返回空串。"""
    if value is None:
        return ""
    if isinstance(value, str):
        text = value.strip()
    elif isinstance(value, (int, float, bool)):
        text = str(value)
    elif isinstance(value, dict):
        # LLM 常把字符串包成 {"description": "..."} / {"factor": "..."}
        for key in ("description", "desc", "factor", "message", "reason",
                    "content", "text", "name", "suggestion", "item"):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.strip():
                text = candidate.strip()
                break
        else:
            return ""
    elif isinstance(value, (list, tuple)):
        parts = [_clean_text(v) for v in value]
        text = "；".join(p for p in parts if p)
    else:
        text = str(value).strip()

    if len(text) > _MAX_TEXT_LEN:
        text = text[:_MAX_TEXT_LEN - 1] + "…"
    return text


def _as_str_list(value: Any) -> List[str]:
    """把任意值收敛为非空字符串列表。"""
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, dict):
        text = _clean_text(value)
        return [text] if text else []
    if isinstance(value, Iterable):
        out: List[str] = []
        for item in value:
            text = _clean_text(item)
            if text:
                out.append(text)
        return out
    text = _clean_text(value)
    return [text] if text else []


def normalize_risk_level(value: Any, default: str = "low") -> str:
    """把任意风险等级值归一化为 low / medium / high / critical。"""
    if value is None:
        return default
    raw = value.value if hasattr(value, "value") else value
    key = str(raw).strip().lower()
    if key in VALID_RISK_LEVELS:
        return key
    return _RISK_LEVEL_ALIASES.get(key, default)


def normalize_risk_score(value: Any, risk_level: str = "low") -> float:
    """把风险分数收敛为 0-100 的 float；非数值时按等级兜底。"""
    try:
        if isinstance(value, bool):
            raise TypeError("bool 不是合法分数")
        score = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return _LEVEL_TO_SCORE.get(risk_level, 0.0)

    if score != score:  # NaN
        return _LEVEL_TO_SCORE.get(risk_level, 0.0)
    return max(0.0, min(100.0, round(score, 2)))


def _index_agent_results(agent_results: Any) -> Dict[str, dict]:
    """把 agent_results 列表按 agent_name 建索引（同名取最后一次执行结果）。"""
    indexed: Dict[str, dict] = {}
    if not isinstance(agent_results, (list, tuple)):
        return indexed
    for entry in agent_results:
        if not isinstance(entry, dict):
            continue
        name = _clean_text(entry.get("agent_name")) or "unknown"
        indexed[name] = entry
    return indexed


def _agent_payload(indexed: Dict[str, dict], agent_name: str) -> dict:
    """取某个 Agent 的 ``result`` 字典，缺失时返回空字典。"""
    entry = indexed.get(agent_name) or {}
    payload = entry.get("result")
    return payload if isinstance(payload, dict) else {}


def _make_issue(severity: str, description: str, issue_type: str) -> dict:
    """构造一条标准 issue。"""
    return {
        "severity": severity if severity in ("high", "medium", "low") else "low",
        "description": description,
        "type": issue_type,
    }


# ===== issues 收集 =====

def _collect_rule_issues(rule_payload: dict) -> List[dict]:
    """RuleAgent.rule_checks → issues（只收 fail / error / warn）。"""
    issues: List[dict] = []
    checks = rule_payload.get("rule_checks")
    if not isinstance(checks, (list, tuple)):
        return issues

    for check in checks:
        if not isinstance(check, dict):
            continue
        # 引擎产物用 status，LLM 语义规则历史上可能落到 result 键
        status = _clean_text(
            check.get("status") or check.get("result")
        ).lower()
        severity = _RULE_STATUS_TO_SEVERITY.get(status)
        if not severity:
            continue  # pass 或未知状态不算问题

        rule_name = _clean_text(check.get("rule") or check.get("rule_name"))
        detail = _clean_text(
            check.get("message") or check.get("reason") or check.get("detail")
        )
        if rule_name and detail and rule_name not in detail:
            description = f"{rule_name}：{detail}"
        else:
            description = detail or rule_name or "规则校验未通过"

        issues.append(_make_issue(severity, description, "rule"))
    return issues


def _collect_risk_issues(risk_payload: dict, risk_level: str) -> List[dict]:
    """RiskAgent.risk_factors → issues（severity 由整体风险等级推导）。"""
    severity = _LEVEL_TO_SEVERITY.get(risk_level, "medium")
    return [
        _make_issue(severity, factor, "risk")
        for factor in _as_str_list(risk_payload.get("risk_factors"))
    ]


def _collect_failure_issues(agent_results: Any) -> List[dict]:
    """执行失败的 Agent → system 类型 issue（让前端能看见降级情况）。"""
    issues: List[dict] = []
    if not isinstance(agent_results, (list, tuple)):
        return issues

    for entry in agent_results:
        if not isinstance(entry, dict):
            continue
        if _clean_text(entry.get("status")).lower() != "failed":
            continue
        name = _clean_text(entry.get("agent_name")) or "未知模块"
        message = _clean_text(entry.get("message")) or "执行失败"
        issues.append(
            _make_issue("high", f"{name} 执行异常：{message}", "system")
        )
    return issues


def _dedupe_issues(issues: List[dict]) -> List[dict]:
    """按 description 去重并保序，同时截断到上限。"""
    seen: set = set()
    out: List[dict] = []
    for issue in issues:
        description = issue.get("description", "")
        if not description or description in seen:
            continue
        seen.add(description)
        out.append(issue)
        if len(out) >= _MAX_ISSUES:
            break
    return out


# ===== suggestions 收集 =====

def _collect_suggestions(
    decision_payload: dict,
    risk_payload: dict,
    final_decision: str,
) -> List[str]:
    """汇总各 Agent 的建议：决策建议 → 风险缓释 → 风险处置建议。"""
    raw: List[str] = []
    raw += _as_str_list(decision_payload.get("suggestions"))
    raw += _as_str_list(decision_payload.get("risk_mitigation"))
    raw += _as_str_list(risk_payload.get("recommendations"))

    seen: set = set()
    out: List[str] = []
    for text in raw:
        if text in seen:
            continue
        seen.add(text)
        out.append(text)
        if len(out) >= _MAX_SUGGESTIONS:
            break

    if not out:
        fallback = _DECISION_FALLBACK_SUGGESTIONS.get(
            final_decision, _DECISION_FALLBACK_SUGGESTIONS["review"]
        )
        out.append(fallback)
    return out


# ===== summary 生成 =====

def _compose_summary(
    final_decision: str,
    risk_level: str,
    risk_score: float,
    rule_payload: dict,
    issue_count: int,
) -> str:
    """当 final_reason 缺失或过于笼统时，用结构化信息拼一句摘要。"""
    decision_label = {
        "approve": "建议通过",
        "reject": "建议驳回",
        "review": "建议人工复核",
        "error": "审核未完成",
    }.get(final_decision, "建议人工复核")

    level_label = {
        "low": "低风险",
        "medium": "中风险",
        "high": "高风险",
        "critical": "严重风险",
    }.get(risk_level, "低风险")

    summary_stat = rule_payload.get("summary")
    if not isinstance(summary_stat, dict):
        summary_stat = {}
    failed = summary_stat.get("failed", rule_payload.get("failed", 0)) or 0
    warnings = summary_stat.get("warnings", rule_payload.get("warnings", 0)) or 0

    return (
        f"AI 审核结论：{decision_label}。"
        f"风险等级 {level_label}（评分 {risk_score:g}），"
        f"规则校验 {failed} 项违规、{warnings} 项警告，"
        f"共识别 {issue_count} 个待关注问题。"
    )


#: 被视为"无有效内容"的占位摘要
_GENERIC_REASONS = {"", "工作流已完成", "无", "none", "n/a", "null"}


# ===== 对外主入口 =====

def build_review_presentation(result: Optional[dict]) -> Dict[str, Any]:
    """
    从 workflow 原始结果构建前端展示字段。

    Args:
        result: ``AgentWorkflow.execute()`` 的返回字典（允许为 None / 残缺）

    Returns:
        仅包含展示字段的字典::

            {"summary": str, "issues": list[dict],
             "suggestions": list[str], "risk_level": str, "risk_score": float}
    """
    data: dict = result if isinstance(result, dict) else {}

    agent_results = data.get("agent_results")
    indexed = _index_agent_results(agent_results)

    rule_payload = _agent_payload(indexed, "RuleAgent")
    risk_payload = _agent_payload(indexed, "RiskAgent")
    decision_payload = _agent_payload(indexed, "DecisionAgent")

    final_decision = _clean_text(data.get("final_decision")).lower() or "review"

    # —— 风险等级/分数 ——
    # RiskAgent 有产出时以它为准；被条件路由跳过（严重违规直达决策）或未启用时，
    # workflow 顶层会给出硬编码默认值 "low"/0，直接采信会把高危单误报为低风险，
    # 因此改用规则汇总的 total_risk 兜底，并取两者中的较高者（只上调不下调）。
    risk_reported = ("risk_level" in risk_payload) or ("risk_score" in risk_payload)
    top_level = normalize_risk_level(data.get("risk_level"), default="low")

    if risk_reported:
        risk_level = normalize_risk_level(
            risk_payload.get("risk_level"), default=top_level
        )
        risk_score = normalize_risk_score(
            risk_payload.get("risk_score", data.get("risk_score")), risk_level
        )
    else:
        rule_summary = rule_payload.get("summary")
        rule_summary = rule_summary if isinstance(rule_summary, dict) else {}
        rule_level = normalize_risk_level(
            rule_summary.get("total_risk"), default="low"
        )
        risk_level = max(
            (top_level, rule_level), key=lambda lv: _LEVEL_ORDER.get(lv, 0)
        )
        # 顶层分数此时同样是硬编码默认值，按等级映射给出可解释的分数
        risk_score = normalize_risk_score(None, risk_level)

    # —— issues：规则违规 + 风险因素 + Agent 失败 ——
    issues = _dedupe_issues(
        _collect_rule_issues(rule_payload)
        + _collect_risk_issues(risk_payload, risk_level)
        + _collect_failure_issues(agent_results)
    )

    # —— suggestions ——
    suggestions = _collect_suggestions(
        decision_payload, risk_payload, final_decision
    )

    # —— summary：final_reason 优先，笼统/缺失时结构化兜底 ——
    summary = _clean_text(
        data.get("final_reason")
        or decision_payload.get("reason")
        or data.get("message")
    )
    if summary.lower() in _GENERIC_REASONS:
        summary = _compose_summary(
            final_decision, risk_level, risk_score, rule_payload, len(issues)
        )

    return {
        "summary": summary,
        "issues": issues,
        "suggestions": suggestions,
        "risk_level": risk_level,
        "risk_score": risk_score,
    }


def enrich_review_result(result: Optional[dict]) -> Dict[str, Any]:
    """
    在 workflow 原始结果之上叠加展示字段，返回新字典（不修改入参）。

    workflow 原有键（``success`` / ``workflow_status`` / ``final_decision`` /
    ``final_reason`` / ``agent_results`` / ``message``）全部原样保留，
    仅 ``risk_level`` / ``risk_score`` 会被归一化为合法取值。

    Args:
        result: ``AgentWorkflow.execute()`` 的返回字典

    Returns:
        叠加了 summary / issues / suggestions / risk_level / risk_score 的新字典
    """
    base: dict = dict(result) if isinstance(result, dict) else {}
    try:
        presentation = build_review_presentation(base)
    except Exception as exc:  # 展示层绝不能拖垮审核主链路
        logger.error(f"[AIReviewPresenter] 展示字段构建失败: {exc}", exc_info=True)
        fallback_level = normalize_risk_level(base.get("risk_level"), "low")
        presentation = {
            "summary": _clean_text(base.get("final_reason")) or "AI 审核已完成",
            "issues": [],
            "suggestions": [_DECISION_FALLBACK_SUGGESTIONS["review"]],
            "risk_level": fallback_level,
            "risk_score": normalize_risk_score(
                base.get("risk_score"), fallback_level
            ),
        }

    base.update(presentation)
    return base
