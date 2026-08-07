/** 严格对齐后端 ExpenseStatus 七态 */
export enum ExpenseStatus {
  DRAFT = 'draft',
  SUBMITTED = 'submitted',
  PENDING = 'pending',
  APPROVED = 'approved',
  REJECTED = 'rejected',
  PAID = 'paid',
  CANCELLED = 'cancelled'
}

/** 严格对齐后端 ExpenseType 八值 */
export enum ExpenseType {
  TRAVEL = 'travel',
  OFFICE = 'office',
  ENTERTAINMENT = 'entertainment',
  TRAINING = 'training',
  MEAL = 'meal',
  TRANSPORT = 'transport',
  EQUIPMENT = 'equipment',
  OTHER = 'other'
}

export const ExpenseStatusLabels: Record<string, string> = {
  draft: '草稿',
  submitted: '已提交',
  pending: '待审批',
  approved: '已通过',
  rejected: '已驳回',
  paid: '已支付',
  cancelled: '已取消'
}

export const ExpenseStatusColors: Record<string, string> = {
  draft: 'info',
  submitted: 'primary',
  pending: 'warning',
  approved: 'success',
  rejected: 'danger',
  paid: 'success',
  cancelled: 'info'
}

export const ExpenseTypeLabels: Record<string, string> = {
  travel: '差旅费',
  office: '办公费',
  entertainment: '招待费',
  training: '培训费',
  meal: '餐饮费',
  transport: '交通费',
  equipment: '设备费',
  other: '其他'
}

/** 对齐后端 ExpenseItemResponse */
export interface ExpenseItem {
  id: number
  expense_id: number
  category_id?: number | null
  description: string
  amount: number
  expense_date: string
  invoice_no?: string | null
  invoice_url?: string | null
  invoice_verified?: boolean
  created_at: string
}

export interface ExpenseItemCreate {
  category_id?: number
  description: string
  amount: number
  expense_date: string
  /** 后端 ExpenseItemCreate.invoice_no（Optional[str], max_length=100），创建时可提交 */
  invoice_no?: string
  invoice_url?: string
}

export interface AIReviewIssue {
  type: string
  severity: 'low' | 'medium' | 'high'
  description: string
  item_index?: number
}

export interface AIReviewResult {
  risk_level: 'low' | 'medium' | 'high' | 'critical'
  risk_score: number
  /** 后端可能返回结构化对象而非字符串 */
  summary: string | Record<string, any>
  issues?: AIReviewIssue[]
  suggestions?: string[]
  reviewed_at?: string
}

/** 审批记录状态（对齐后端 ApprovalStatus） */
export type ApprovalStatus = 'pending' | 'approved' | 'rejected' | 'returned'

export const ApprovalStatusLabels: Record<string, string> = {
  pending: '待审',
  approved: '通过',
  rejected: '驳回',
  returned: '退回'
}

export const ApprovalStatusColors: Record<string, string> = {
  pending: 'info',
  approved: 'success',
  rejected: 'danger',
  returned: 'warning'
}

/**
 * 对齐后端 ApprovalResponse。
 * 注意：后端**没有** `action` 字段，审批动作体现在 `status` 上。
 * expense_no / title / expense_type / total_amount / expense_status 是列表接口
 * 附带的报销单冗余字段，详情/历史接口可能不返回，故全部可选。
 */
export interface ApprovalRecord {
  id: number
  expense_id: number
  approver_id: number
  flow_id?: number | null
  status: ApprovalStatus
  level: number
  comment?: string | null
  approver_name?: string | null
  expense_no?: string
  title?: string
  expense_type?: string
  total_amount?: number
  expense_status?: string
  created_at?: string
  updated_at?: string
}

/** 严格对齐后端 ExpenseResponse */
export interface Expense {
  id: number
  user_id: number
  expense_no: string
  title: string
  expense_type: ExpenseType | string
  total_amount: number
  currency: string
  status: ExpenseStatus | string
  description: string
  remark?: string | null
  submitted_at?: string | null
  approved_at?: string | null
  paid_at?: string | null
  risk_level?: string | null
  risk_score?: number | null
  ai_review_result?: AIReviewResult | Record<string, any> | null
  items: ExpenseItem[]
  created_at: string
  updated_at: string
}

export interface ExpenseCreate {
  title: string
  expense_type: string
  description: string
  items: ExpenseItemCreate[]
}

export interface ExpenseUpdate {
  title?: string
  expense_type?: string
  description?: string
}

export interface ExpenseListParams {
  page?: number
  page_size?: number
  status?: ExpenseStatus | string
  expense_type?: string
  keyword?: string
  sort_by?: string
  sort_order?: string
}

export interface AIReviewResponse {
  risk_level: 'low' | 'medium' | 'high' | 'critical'
  risk_score: number
  summary: string | Record<string, any>
  issues?: AIReviewIssue[]
  suggestions?: string[]
}

/** by_status / by_type 的桶结构 */
export interface StatisticsBucket {
  count: number
  amount: number
}

/**
 * GET /expenses/statistics/overview 的**真实** payload 形状。
 * 与下面的视图模型 `Statistics` 不同：后端返回的是 total_count + 两个按维度聚合的字典，
 * 由页面自行映射为视图模型。
 */
export interface StatisticsOverview {
  total_count: number
  total_amount: number
  by_status: Record<string, StatisticsBucket>
  by_type: Record<string, StatisticsBucket>
}

/** 页面侧的统计视图模型（由 StatisticsOverview 映射而来，非接口原始形状） */
export interface Statistics {
  total_expenses: number
  total_amount: number
  pending_count: number
  approved_count: number
  rejected_count: number
  draft_count: number
  monthly_stats: MonthlyStat[]
  type_stats: TypeStat[]
  department_stats: DepartmentStat[]
}

export interface MonthlyStat {
  month: string
  count: number
  total_amount: number
}

export interface TypeStat {
  type: string
  count: number
  total_amount: number
}

export interface DepartmentStat {
  department: string
  count: number
  total_amount: number
}
