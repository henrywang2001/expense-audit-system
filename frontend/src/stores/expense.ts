import { defineStore } from 'pinia'
import { ref, reactive } from 'vue'
import type { Expense, ExpenseListParams, StatisticsOverview } from '@/types'
import { getExpenseList, getExpenseDetail, getStatistics as getStatsApi } from '@/api/expense'

export const useExpenseStore = defineStore('expense', () => {
  const expenseList = ref<Expense[]>([])
  const total = ref(0)
  const loading = ref(false)
  const currentExpense = ref<Expense | null>(null)
  // 存的是接口原始 payload（StatisticsOverview），不是页面视图模型
  const statistics = ref<StatisticsOverview | null>(null)
  const statsLoading = ref(false)

  const listParams = reactive<ExpenseListParams>({
    page: 1,
    page_size: 10
  })

  async function fetchList(params?: ExpenseListParams) {
    loading.value = true
    try {
      const mergedParams = { ...listParams, ...params }
      const res = await getExpenseList(mergedParams)
      expenseList.value = res.data || []
      total.value = res.total || 0
      if (params?.page) listParams.page = params.page
      if (params?.page_size) listParams.page_size = params.page_size
    } catch (error) {
      console.error('Failed to fetch expense list:', error)
      expenseList.value = []
      total.value = 0
    } finally {
      loading.value = false
    }
  }

  async function fetchDetail(id: number) {
    loading.value = true
    try {
      const res = await getExpenseDetail(id)
      currentExpense.value = res.data
      return res.data
    } catch (error) {
      console.error('Failed to fetch expense detail:', error)
      currentExpense.value = null
      return null
    } finally {
      loading.value = false
    }
  }

  // ⚠️ 后端 get_statistics 不接受任何 Query 参数，故不再暴露 params 形参
  async function fetchStatistics() {
    statsLoading.value = true
    try {
      const res = await getStatsApi()
      statistics.value = res.data
    } catch (error) {
      console.error('Failed to fetch statistics:', error)
    } finally {
      statsLoading.value = false
    }
  }

  function resetParams() {
    listParams.page = 1
    listParams.page_size = 10
    listParams.status = undefined
    listParams.expense_type = undefined
    listParams.keyword = undefined
  }

  return {
    expenseList,
    total,
    loading,
    currentExpense,
    listParams,
    statistics,
    statsLoading,
    fetchList,
    fetchDetail,
    fetchStatistics,
    resetParams
  }
})
