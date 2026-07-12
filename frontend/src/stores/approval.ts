import { defineStore } from 'pinia'
import { ref, reactive } from 'vue'
import type { Expense } from '@/types'
import type { ExpenseListParams } from '@/types/expense'
import { getApprovalList, approveExpense, rejectExpense } from '@/api/approval'

export const useApprovalStore = defineStore('approval', () => {
  const approvalList = ref<Expense[]>([])
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
      approvalList.value = res.data.items
      total.value = res.data.total
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

  async function approve(id: number, comment?: string) {
    const res = await approveExpense(id, comment)
    await fetchList()
    return res
  }

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
