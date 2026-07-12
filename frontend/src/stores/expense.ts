import { defineStore } from 'pinia'
import { ref, reactive } from 'vue'
import type { Expense, ExpenseListParams, Statistics } from '@/types'
import { getExpenseList, getExpenseDetail, getStatistics as getStatsApi } from '@/api/expense'

export const useExpenseStore = defineStore('expense', () => {
  const expenseList = ref<Expense[]>([])
  const total = ref(0)
  const loading = ref(false)
  const currentExpense = ref<Expense | null>(null)
  const statistics = ref<Statistics | null>(null)
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

  async function fetchStatistics(params?: { start_date?: string; end_date?: string }) {
    statsLoading.value = true
    try {
      const res = await getStatsApi(params)
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
    listParams.start_date = undefined
    listParams.end_date = undefined
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
