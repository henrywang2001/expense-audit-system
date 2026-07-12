export enum ExpenseStatus {
  DRAFT = 'draft',
  PENDING = 'pending',
  APPROVED = 'approved',
  REJECTED = 'rejected',
  WITHDRAWN = 'withdrawn'
}

export enum ExpenseType {
  TRAVEL = 'travel',
  OFFICE = 'office',
  ENTERTAINMENT = 'entertainment',
  TRAINING = 'training',
  MEAL = 'meal',
  TRANSPORT = 'transport',
  OTHER = 'other'
}

export const ExpenseStatusLabels: Record<string, string> = {
  draft: '草稿',
  pending: '待审批',
  approved: '已通过',
  rejected: '已驳回',
  withdrawn: '已撤回'
}

export const ExpenseStatusColors: Record<string, string> = {
  draft: 'info',
  pending: 'warning',
  approved: 'success',
  rejected: 'danger',
  withdrawn: 'info'
}

export const ExpenseTypeLabels: Record<string, string> = {
  travel: '差旅费',
  office: '办公费',
  entertainment: '招待费',
  training: '培训费',
  meal: '餐饮费',
  transport: '交通费',
  other: '其他'
}

export interface ExpenseItem {
  id: number
  expense_id: number
  category: string
  description: string
  amount: number
  expense_date: string
  receipt_url?: string
  created_at: string
}

export interface ExpenseItemCreate {
  category_id?: number
  description: string
  amount: number
  expense_date: string
  invoice_url?: string
}

export interface AIReviewResult {
  risk_level: 'low' | 'medium' | 'high'
  risk_score: number
  summary: string
  issues: AIReviewIssue[]
  suggestions: string[]
  reviewed_at: string
}

export interface AIReviewIssue {
  type: string
  severity: 'low' | 'medium' | 'high'
  description: string
  item_index?: number
}

export interface ApprovalRecord {
  id: number
  expense_id: number
  approver_id: number
  approver_name: string
  action: 'approve' | 'reject'
  comment: string
  created_at: string
}

export interface Expense {
  id: number
  expense_no: string
  title: string
  type: ExpenseType
  description: string
  total_amount: number
  status: ExpenseStatus
  submitter_id: number
  submitter_name: string
  submitter_department: string
  items: ExpenseItem[]
  ai_review?: AIReviewResult
  approval_records: ApprovalRecord[]
  created_at: string
  updated_at: string
  submitted_at?: string
}

export interface ExpenseCreate {
  title: string
  expense_type: string
  description: string
  items: ExpenseItemCreate[]
}

export interface ExpenseUpdate {
  title?: string
  type?: ExpenseType
  description?: string
}

export interface ExpenseListParams {
  page?: number
  page_size?: number
  status?: ExpenseStatus
  expense_type?: string
  keyword?: string
  start_date?: string
  end_date?: string
}

export interface ExpenseListResponse {
  items: Expense[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface AIReviewResponse {
  risk_level: 'low' | 'medium' | 'high'
  risk_score: number
  summary: string
  issues: AIReviewIssue[]
  suggestions: string[]
}

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
