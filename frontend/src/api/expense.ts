import { get, post, put, del, upload } from '@/utils/request'
import type {
  Expense,
  ExpenseCreate,
  ExpenseUpdate,
  ExpenseListParams,
  ExpenseListResponse,
  AIReviewResponse,
  Statistics,
  ApiResponse
} from '@/types'

export function getExpenseList(params?: ExpenseListParams): Promise<ApiResponse<ExpenseListResponse>> {
  return get<ApiResponse<ExpenseListResponse>>('/expenses', params)
}

export function getExpenseDetail(id: number): Promise<ApiResponse<Expense>> {
  return get<ApiResponse<Expense>>(`/expenses/${id}`)
}

export function createExpense(data: ExpenseCreate): Promise<ApiResponse<Expense>> {
  return post<ApiResponse<Expense>>('/expenses', data)
}

export function updateExpense(id: number, data: ExpenseUpdate): Promise<ApiResponse<Expense>> {
  return put<ApiResponse<Expense>>(`/expenses/${id}`, data)
}

export function deleteExpense(id: number): Promise<ApiResponse<null>> {
  return del<ApiResponse<null>>(`/expenses/${id}`)
}

export function submitExpense(id: number): Promise<ApiResponse<Expense>> {
  return post<ApiResponse<Expense>>(`/expenses/${id}/submit`)
}

export function withdrawExpense(id: number): Promise<ApiResponse<Expense>> {
  return post<ApiResponse<Expense>>(`/expenses/${id}/withdraw`)
}

export function aiReviewExpense(id: number): Promise<ApiResponse<AIReviewResponse>> {
  return post<ApiResponse<AIReviewResponse>>(`/expenses/${id}/ai-review`)
}

export function uploadInvoice(file: File): Promise<ApiResponse<{ url: string }>> {
  return upload<ApiResponse<{ url: string }>>('/expenses/upload-invoice', file, 'file')
}

export function getStatistics(params?: { start_date?: string; end_date?: string }): Promise<ApiResponse<Statistics>> {
  return get<ApiResponse<Statistics>>('/expenses/statistics/overview', params)
}

// Report APIs
export function getReportSummary(params?: { start_date?: string; end_date?: string }): Promise<ApiResponse<any>> {
  return get<ApiResponse<any>>('/reports/summary', params)
}

export function getReportByType(params?: { start_date?: string; end_date?: string }): Promise<ApiResponse<any[]>> {
  return get<ApiResponse<any[]>>('/reports/by-type', params)
}

export function getReportByDepartment(params?: { start_date?: string; end_date?: string }): Promise<ApiResponse<any[]>> {
  return get<ApiResponse<any[]>>('/reports/by-department', params)
}

export function getReportTrend(months?: number): Promise<ApiResponse<any[]>> {
  return get<ApiResponse<any[]>>('/reports/trend', { months: months || 12 })
}
