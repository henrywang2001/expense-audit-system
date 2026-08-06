import { get } from '@/utils/request'
import type { ApiResponse } from '@/types'

export interface ReportSummary {
  total_count: number
  total_amount: number
  month_count: number
  month_amount: number
  status_distribution: Record<string, number>
}

export interface ReportByTypeItem {
  expense_type: string
  count: number
  total_amount: number
}

export interface ReportByDepartmentItem {
  department: string
  count: number
  total_amount: number
}

export interface ReportTrendItem {
  month: string
  count: number
  total_amount: number
}

// ⚠️ /reports/summary、/reports/by-type、/reports/by-department 后端均不消费
//    start_date / end_date 等 Query 参数，因此这里不再暴露形参，避免误导。
export function getReportSummary(): Promise<ApiResponse<ReportSummary>> {
  return get<ApiResponse<ReportSummary>>('/reports/summary')
}

export function getReportByType(): Promise<ApiResponse<ReportByTypeItem[]>> {
  return get<ApiResponse<ReportByTypeItem[]>>('/reports/by-type')
}

export function getReportByDepartment(): Promise<ApiResponse<ReportByDepartmentItem[]>> {
  return get<ApiResponse<ReportByDepartmentItem[]>>('/reports/by-department')
}

/** 仅 trend 接口真实消费 months 参数 */
export function getReportTrend(months?: number): Promise<ApiResponse<ReportTrendItem[]>> {
  return get<ApiResponse<ReportTrendItem[]>>('/reports/trend', { months: months || 12 })
}
