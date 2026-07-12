<template>
  <div class="expense-list-comp">
    <!-- Filter bar -->
    <div class="filter-bar">
      <el-input
        v-model="searchKeyword"
        placeholder="搜索报销编号/标题"
        clearable
        style="width: 240px"
        :prefix-icon="Search"
        @clear="handleSearch"
        @keyup.enter="handleSearch"
      />
      <el-select
        v-model="statusFilter"
        placeholder="状态筛选"
        clearable
        style="width: 140px"
        @change="handleSearch"
      >
        <el-option label="草稿" value="draft" />
        <el-option label="待审批" value="pending" />
        <el-option label="已通过" value="approved" />
        <el-option label="已驳回" value="rejected" />
      </el-select>
      <el-select
        v-model="typeFilter"
        placeholder="类型筛选"
        clearable
        style="width: 140px"
        @change="handleSearch"
      >
        <el-option
          v-for="(label, value) in ExpenseTypeLabels"
          :key="value"
          :label="label"
          :value="value"
        />
      </el-select>
      <el-date-picker
        v-model="dateRange"
        type="daterange"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        value-format="YYYY-MM-DD"
        style="width: 260px"
        @change="handleSearch"
      />
      <el-button type="primary" :icon="Search" @click="handleSearch">
        搜索
      </el-button>
      <el-button :icon="RefreshRight" @click="handleReset">
        重置
      </el-button>
    </div>

    <!-- Table -->
    <el-card>
      <el-table
        v-loading="loading"
        :data="expenses"
        border
        stripe
        style="width: 100%"
        @row-click="handleRowClick"
      >
        <el-table-column prop="expense_no" label="报销编号" width="160" />
        <el-table-column prop="title" label="标题" min-width="180" show-overflow-tooltip />
        <el-table-column label="类型" width="100">
          <template #default="{ row }">
            {{ getTypeLabel(row.expense_type) }}
          </template>
        </el-table-column>
        <el-table-column label="金额" width="140" align="right">
          <template #default="{ row }">
            <span class="amount-cell">&yen;{{ row.total_amount.toFixed(2) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="getStatusColor(row.status)" size="small">
              {{ getStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="user_id" label="提交人ID" width="100" />
        <el-table-column label="提交日期" width="120">
          <template #default="{ row }">
            {{ formatDate(row.created_at, 'YYYY-MM-DD') }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right" align="center">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click.stop="handleView(row)">
              查看
            </el-button>
            <el-button
              v-if="row.status === 'draft'"
              link
              type="success"
              size="small"
              @click.stop="handleSubmit(row)"
            >
              提交
            </el-button>
            <el-button
              v-if="row.status === 'pending'"
              link
              type="warning"
              size="small"
              @click.stop="handleWithdraw(row)"
            >
              撤回
            </el-button>
            <el-button
              v-if="row.status === 'draft'"
              link
              type="danger"
              size="small"
              @click.stop="handleDelete(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <Pagination
        :page="currentPage"
        :page-size="pageSize"
        :total="total"
        @update:page="currentPage = $event"
        @change="fetchData"
      />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, RefreshRight } from '@element-plus/icons-vue'
import Pagination from '@/components/common/Pagination.vue'
import { getExpenseList, submitExpense, withdrawExpense, deleteExpense } from '@/api/expense'
import type { Expense } from '@/types/expense'
import { ExpenseStatusLabels, ExpenseStatusColors, ExpenseTypeLabels } from '@/types/expense'
import { formatDate } from '@/utils/helpers'

const router = useRouter()

const expenses = ref<Expense[]>([])
const total = ref(0)
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(10)
const searchKeyword = ref('')
const statusFilter = ref('')
const typeFilter = ref('')
const dateRange = ref<string[]>([])

function getStatusLabel(status: string): string {
  return ExpenseStatusLabels[status] || status
}

function getStatusColor(status: string): string {
  return ExpenseStatusColors[status] || 'info'
}

function getTypeLabel(type: string): string {
  return ExpenseTypeLabels[type] || type
}

async function fetchData() {
  loading.value = true
  try {
    const params: any = {
      page: currentPage.value,
      page_size: pageSize.value
    }
    if (searchKeyword.value) params.keyword = searchKeyword.value
    if (statusFilter.value) params.status = statusFilter.value
    if (typeFilter.value) params.expense_type = typeFilter.value
    if (dateRange.value && dateRange.value.length === 2) {
      params.start_date = dateRange.value[0]
      params.end_date = dateRange.value[1]
    }
    const res = await getExpenseList(params)
    expenses.value = res.data || []
    total.value = res.total || 0
  } catch (error) {
    console.error('Fetch expense list error:', error)
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  currentPage.value = 1
  fetchData()
}

function handleReset() {
  searchKeyword.value = ''
  statusFilter.value = ''
  typeFilter.value = ''
  dateRange.value = []
  currentPage.value = 1
  fetchData()
}

function handleView(row: Expense) {
  router.push(`/expense/detail/${row.id}`)
}

function handleRowClick(row: Expense) {
  handleView(row)
}

async function handleSubmit(row: Expense) {
  try {
    await ElMessageBox.confirm('确认提交此报销单？提交后将进入审批流程。', '确认提交', {
      confirmButtonText: '确认提交',
      cancelButtonText: '取消',
      type: 'info'
    })
    await submitExpense(row.id)
    ElMessage.success('报销单已提交审批')
    fetchData()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('Submit error:', error)
    }
  }
}

async function handleWithdraw(row: Expense) {
  try {
    await ElMessageBox.confirm('确认撤回此报销单？', '确认撤回', {
      confirmButtonText: '确认撤回',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await withdrawExpense(row.id)
    ElMessage.success('报销单已撤回')
    fetchData()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('Withdraw error:', error)
    }
  }
}

async function handleDelete(row: Expense) {
  try {
    await ElMessageBox.confirm('确认删除此报销单？此操作不可撤销。', '确认删除', {
      confirmButtonText: '确认删除',
      cancelButtonText: '取消',
      type: 'error'
    })
    await deleteExpense(row.id)
    ElMessage.success('报销单已删除')
    fetchData()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('Delete error:', error)
    }
  }
}

fetchData()
</script>

<style scoped lang="scss">
@import '@/styles/variables.scss';
.amount-cell {
  font-weight: 600;
  color: $danger-color;
  font-family: 'Courier New', monospace;
}
</style>
