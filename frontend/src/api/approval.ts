import { get, post } from '@/utils/request'
import type { Expense, ApprovalRecord, ApiResponse, PaginatedResponse } from '@/types'
import type { ExpenseListParams, ExpenseListResponse } from '@/types/expense'

export function getApprovalList(params?: ExpenseListParams): Promise<ApiResponse<ExpenseListResponse>> {
  return get<ApiResponse<ExpenseListResponse>>('/approvals', params)
}

export function approveExpense(id: number, comment?: string): Promise<ApiResponse<Expense>> {
  return post<ApiResponse<Expense>>(`/approvals/${id}/approve`, { comment })
}

export function rejectExpense(id: number, comment: string): Promise<ApiResponse<Expense>> {
  return post<ApiResponse<Expense>>(`/approvals/${id}/reject`, { comment })
}

export function getApprovalHistory(id: number): Promise<ApiResponse<ApprovalRecord[]>> {
  return get<ApiResponse<ApprovalRecord[]>>(`/approvals/${id}/history`)
}
