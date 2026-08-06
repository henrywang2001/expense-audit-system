import { get, post, put, del, upload } from '@/utils/request'
import type {
  Expense,
  ExpenseCreate,
  ExpenseUpdate,
  ExpenseListParams,
  AIReviewResponse,
  StatisticsOverview,
  ApiResponse,
  ApiListResponse
} from '@/types'

/** 上传发票的返回 payload（后端 upload-invoice） */
export interface UploadInvoiceResult {
  filename: string
  original_name: string
  size: number
  url: string
}

// ⚠️ 后端 expense.py 的列表/创建路由定义为 @router.get("/") / @router.post("/")，
//    路径必须【带】尾斜杠，不带会 307 重定向。
//    注意：这与 /rules 模块相反（那边必须不带斜杠），不要"统一"处理。
export function getExpenseList(params?: ExpenseListParams): Promise<ApiListResponse<Expense>> {
  return get<ApiListResponse<Expense>>('/expenses/', params)
}

export function getExpenseDetail(id: number): Promise<ApiResponse<Expense>> {
  return get<ApiResponse<Expense>>(`/expenses/${id}`)
}

export function createExpense(data: ExpenseCreate): Promise<ApiResponse<Expense>> {
  return post<ApiResponse<Expense>>('/expenses/', data)
}

export function updateExpense(id: number, data: ExpenseUpdate): Promise<ApiResponse<Expense>> {
  return put<ApiResponse<Expense>>(`/expenses/${id}`, data)
}

export function deleteExpense(id: number): Promise<ApiResponse<null>> {
  return del<ApiResponse<null>>(`/expenses/${id}`)
}

/** 后端返回 MessageResponse，data 恒为 null —— 成功提示请用 res.message */
export function submitExpense(id: number): Promise<ApiResponse<null>> {
  return post<ApiResponse<null>>(`/expenses/${id}/submit`)
}

/** 后端返回 MessageResponse，data 恒为 null —— 成功提示请用 res.message */
export function withdrawExpense(id: number): Promise<ApiResponse<null>> {
  return post<ApiResponse<null>>(`/expenses/${id}/withdraw`)
}

// ⚠️ 后端 AIReviewRequest.expense_id 为必填字段，不传 body 必然 422。
export function aiReviewExpense(id: number): Promise<ApiResponse<AIReviewResponse>> {
  return post<ApiResponse<AIReviewResponse>>(`/expenses/${id}/ai-review`, { expense_id: id })
}

export function uploadInvoice(file: File): Promise<ApiResponse<UploadInvoiceResult>> {
  return upload<ApiResponse<UploadInvoiceResult>>('/expenses/upload-invoice', file, 'file')
}

// ⚠️ 后端 get_statistics 不接受任何 Query 参数，故此处不暴露 params 形参。
export function getStatistics(): Promise<ApiResponse<StatisticsOverview>> {
  return get<ApiResponse<StatisticsOverview>>('/expenses/statistics/overview')
}
