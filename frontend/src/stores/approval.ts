import { defineStore } from 'pinia'
import { ref, reactive } from 'vue'
import type { ApprovalRecord } from '@/types'
import type { ExpenseListParams } from '@/types/expense'
import { getApprovalList, approveExpense, rejectExpense } from '@/api/approval'

export const useApprovalStore = defineStore('approval', () => {
  // ⚠️ 列表元素是【审批记录】，不是报销单
  const approvalList = ref<ApprovalRecord[]>([])
  const total = ref(0)
  const loading = ref(false)

  const listParams = reactive<ExpenseListParams>({
    page: 1,
    page_size: 10,
    status: undefined
  })

  async function fetchList(params?: ExpenseListParams) {
    loading.value = true
    try {
      const mergedParams = { ...listParams, ...params }
      const res = await getApprovalList(mergedParams)
      // 形态 A：payload 在 res.data，total 与 data 平级
      approvalList.value = res.data || []
      total.value = res.total || 0
      if (params?.page) listParams.page = params.page
      if (params?.page_size) listParams.page_size = params.page_size
    } catch (error) {
      console.error('Failed to fetch approval list:', error)
      approvalList.value = []
      total.value = 0
    } finally {
      loading.value = false
    }
  }

  /** @param id 审批记录 id（不是报销单 id） */
  async function approve(id: number, comment?: string) {
    const res = await approveExpense(id, comment)
    await fetchList()
    return res
  }

  /** @param id 审批记录 id（不是报销单 id） */
  async function reject(id: number, comment: string) {
    const res = await rejectExpense(id, comment)
    await fetchList()
    return res
  }

  function resetParams() {
    listParams.page = 1
    listParams.page_size = 10
    listParams.status = undefined
  }

  return {
    approvalList,
    total,
    loading,
    listParams,
    fetchList,
    approve,
    reject,
    resetParams
  }
})
