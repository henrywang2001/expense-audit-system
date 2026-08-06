import { get, post, put, del } from '@/utils/request'
import type { Rule, RuleListResponse, RuleCreatePayload, RuleUpdatePayload, RuleListParams } from '@/types/rule'

// ⚠️ 规则路由后端定义为 @router.get("") —— 路径必须【不带】尾斜杠，
//    带斜杠会 307 到无斜杠版本。切勿"统一加斜杠"。
export function getRuleList(params?: RuleListParams): Promise<RuleListResponse> {
  return get<RuleListResponse>('/rules', params)          // 裸响应：res.items / res.total
}
export function getRule(id: number): Promise<Rule> {
  return get<Rule>(`/rules/${id}`)                        // 裸 RuleResponse
}
export function createRule(data: RuleCreatePayload): Promise<Rule> {
  return post<Rule>('/rules', data)                       // 裸 RuleResponse
}
export function updateRule(id: number, data: RuleUpdatePayload): Promise<Rule> {
  return put<Rule>(`/rules/${id}`, data)                  // 裸 RuleResponse
}
export function setRuleActive(id: number, isActive: boolean): Promise<Rule> {
  return put<Rule>(`/rules/${id}`, { is_active: isActive })   // 只传 is_active，不触发 logic 校验
}
export function deactivateRule(id: number): Promise<{ success: boolean; message: string; rule_id: number }> {
  return del(`/rules/${id}`)                              // 软删除 = 停用
}
