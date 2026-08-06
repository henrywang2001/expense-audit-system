import { get, post } from '@/utils/request'
import type { ApprovalRecord, ApiResponse, ApiListResponse, ExpenseListParams } from '@/types'

// ⚠️ 后端 approval.py:21 定义为 @router.get("/")，路径必须【带】尾斜杠。
// ⚠️ 列表元素是【审批记录 ApprovalResponse】，不是报销单 Expense。
export function getApprovalList(params?: ExpenseListParams): Promise<ApiListResponse<ApprovalRecord>> {
  return get<ApiListResponse<ApprovalRecord>>('/approvals/', params)
}

/** @param approvalId 传的是审批记录 id，不是报销单 id */
export function approveExpense(approvalId: number, comment?: string): Promise<ApiResponse<ApprovalRecord>> {
  return post<ApiResponse<ApprovalRecord>>(`/approvals/${approvalId}/approve`, { comment })
}

/** @param approvalId 传的是审批记录 id，不是报销单 id */
export function rejectExpense(approvalId: number, comment: string): Promise<ApiResponse<ApprovalRecord>> {
  return post<ApiResponse<ApprovalRecord>>(`/approvals/${approvalId}/reject`, { comment })
}

/** @param expenseId 这里传的是【报销单 id】，与 approve/reject 不同 */
export function getApprovalHistoryByExpense(expenseId: number): Promise<ApiResponse<ApprovalRecord[]>> {
  return get<ApiResponse<ApprovalRecord[]>>(`/approvals/${expenseId}/history`)
}
