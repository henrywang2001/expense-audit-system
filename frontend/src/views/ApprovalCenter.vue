<template>
  <div class="approval-center-page">
    <div class="page-header">
      <h2 class="page-header__title">审批中心</h2>
    </div>

    <!-- Filter bar -->
    <div class="filter-bar">
      <el-input
        v-model="searchKeyword"
        placeholder="搜索报销编号/标题"
        clearable
        style="width: 240px"
        :prefix-icon="Search"
        @keyup.enter="handleSearch"
      />
      <el-select
        v-model="statusFilter"
        placeholder="状态筛选"
        clearable
        style="width: 140px"
        @change="handleSearch"
      >
        <el-option label="待审批" value="pending" />
        <el-option label="已通过" value="approved" />
        <el-option label="已驳回" value="rejected" />
      </el-select>
      <el-button type="primary" :icon="Search" @click="handleSearch">搜索</el-button>
      <el-button :icon="RefreshRight" @click="handleReset">重置</el-button>
    </div>

    <!-- Table -->
    <el-card v-loading="loading">
      <el-table :data="approvalList" border stripe style="width: 100%">
        <el-table-column prop="expense_no" label="报销编号" width="160" />
        <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
        <el-table-column label="类型" width="100">
          <template #default="{ row }">
            {{ getTypeLabel(row.expense_type) }}
          </template>
        </el-table-column>
        <el-table-column label="金额" width="140" align="right">
          <template #default="{ row }">
            <span class="amount-cell">¥{{ row.total_amount.toFixed(2) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="user_id" label="提交人ID" width="100" />
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="getStatusColor(row.status)" size="small">
              {{ getStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="提交时间" width="120">
          <template #default="{ row }">
            {{ formatDate(row.created_at, 'YYYY-MM-DD') }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right" align="center">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="handleView(row)">
              查看
            </el-button>
            <template v-if="row.status === 'pending'">
              <el-button link type="success" size="small" @click="handleApprove(row)">
                通过
              </el-button>
              <el-button link type="danger" size="small" @click="handleReject(row)">
                驳回
              </el-button>
            </template>
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
import { getApprovalList, approveExpense, rejectExpense } from '@/api/approval'
import type { Expense } from '@/types/expense'
import { ExpenseStatusLabels, ExpenseStatusColors, ExpenseTypeLabels } from '@/types/expense'
import { useUserStore } from '@/stores/user'
import { formatDate } from '@/utils/helpers'

const router = useRouter()
const userStore = useUserStore()

const approvalList = ref<Expense[]>([])
const total = ref(0)
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(10)
const searchKeyword = ref('')
const statusFilter = ref('')

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
    const params: any = { page: currentPage.value, page_size: pageSize.value }
    if (searchKeyword.value) params.keyword = searchKeyword.value
    if (statusFilter.value) params.status = statusFilter.value
    const res = await getApprovalList(params)
    approvalList.value = res.data || []
    total.value = res.total || 0
  } catch (error) {
    console.error('Fetch approval list error:', error)
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
  currentPage.value = 1
  fetchData()
}

function handleView(row: Expense) {
  router.push(`/expense/detail/${row.id}`)
}

async function handleApprove(row: Expense) {
  try {
    const { value: comment } = await ElMessageBox.prompt('请输入审批意见（可选）', '审批通过', {
      confirmButtonText: '确认通过',
      cancelButtonText: '取消',
      inputType: 'textarea',
      inputPlaceholder: '请输入审批意见...'
    })
    await approveExpense(row.id, comment || undefined)
    ElMessage.success('审批已通过')
    fetchData()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('Approve error:', error)
    }
  }
}

async function handleReject(row: Expense) {
  try {
    const { value: comment } = await ElMessageBox.prompt('请输入驳回原因', '审批驳回', {
      confirmButtonText: '确认驳回',
      cancelButtonText: '取消',
      inputType: 'textarea',
      inputPlaceholder: '请输入驳回原因...',
      inputValidator: (val: string) => {
        if (!val || !val.trim()) return '驳回原因不能为空'
        return true
      }
    })
    await rejectExpense(row.id, comment || '')
    ElMessage.success('报销单已驳回')
    fetchData()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('Reject error:', error)
    }
  }
}

fetchData()
</script>

<style scoped lang="scss">
@import '@/styles/variables.scss';
.amount-cell {
  font-weight: 600;
  color: $primary-color;
  font-family: 'Courier New', monospace;
}
</style>
