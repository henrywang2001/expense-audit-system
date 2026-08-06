/** 后端 RuleType 八值 */
export const RuleTypeLabels: Record<string, string> = {
  amount_limit: '金额限制', frequency: '频率限制', category: '类别限制',
  department: '部门限制',   position: '职位限制',  time: '时间限制',
  compliance: '合规规则',   custom: '自定义规则'
}

export const RuleActionLabels: Record<string, string> = {
  reject: '拒绝', warn: '警告', require_approval: '需额外审批'
}
export const RuleActionColors: Record<string, string> = {
  reject: 'danger', warn: 'warning', require_approval: 'info'
}

export const RuleExecModeLabels: Record<string, string> = {
  deterministic: '确定性求值', pre_computed: '预计算求值', semantic: '语义(LLM)判断'
}

export type RuleAction   = 'reject' | 'warn' | 'require_approval'
export type RuleExecMode = 'deterministic' | 'pre_computed' | 'semantic'

/** 严格对齐后端 RuleResponse —— 注意：没有 created_at */
export interface Rule {
  id: number
  name: string
  rule_type: string
  logic: Record<string, any>      // 存量数据可能是 {}
  action: RuleAction
  message: string                 // 后端伪字段，恒为 `${name}不符合规则`
  description?: string | null     // 实际映射 ORM 的 condition 列
  exec_mode: RuleExecMode
  is_active: boolean
}

export interface RuleListResponse { total: number; items: Rule[] }

export interface RuleCreatePayload {
  name: string
  rule_type: string
  logic: Record<string, any>      // 必填且必须非空
  action: RuleAction
  message: string                 // 必填（否则 422），但后端不持久化
  description?: string
  exec_mode?: RuleExecMode
}

/** 全部可选；未传的字段后端不会动 —— logic 省略即跳过校验 */
export type RuleUpdatePayload = Partial<RuleCreatePayload> & { is_active?: boolean }

export interface RuleListParams {
  page?: number; page_size?: number
  rule_type?: string; is_active?: boolean; exec_mode?: string
}

/** 与后端 rule_engine.FIELD_WHITELIST 完全一致（用于前端预校验） */
export const RULE_FIELD_WHITELIST = [
  'total_amount', 'currency', 'title', 'expense_type', 'description', 'items',
  'user_department', 'user_role',
  'item_count', 'has_unverified_invoice', 'max_invoice_age_days'
] as const

/** 与后端 rule_engine.ALLOWED_OPS 完全一致 */
export const RULE_ALLOWED_OPS = [
  '==','===','!=','!==','>','>=','<','<=',
  '!','!!','and','or','?:','if',
  'var','missing','missing_some',
  'map','reduce',
  '%','+','*','-','/','min','max',
  'cat','substr','in','merge','count',
  'today','date','datetime','rdelta','duration','log'
] as const
