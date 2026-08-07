<template>
  <div class="expense-detail" v-loading="loading">
    <template v-if="expense">
      <!-- Basic Info -->
      <el-card class="mb-md">
        <template #header>
          <div class="flex-between">
            <span class="card-header-title">报销单信息</span>
            <el-tag :type="getStatusColor(expense.status)" size="large">
              {{ getStatusLabel(expense.status) }}
            </el-tag>
          </div>
        </template>
        <div class="detail-info">
          <div class="detail-info__item">
            <span class="detail-info__item-label">报销编号：</span>
            <span class="detail-info__item-value">{{ expense.expense_no }}</span>
          </div>
          <div class="detail-info__item">
            <span class="detail-info__item-label">报销类型：</span>
            <span class="detail-info__item-value">{{ getTypeLabel(expense.expense_type) }}</span>
          </div>
          <div class="detail-info__item">
            <span class="detail-info__item-label">报销标题：</span>
            <span class="detail-info__item-value">{{ expense.title }}</span>
          </div>
          <div class="detail-info__item">
            <span class="detail-info__item-label">总金额：</span>
            <span class="detail-info__item-value amount-highlight">
              ¥{{ expense.total_amount.toFixed(2) }}
            </span>
          </div>
          <!-- 后端 ExpenseResponse 只返回 user_id，没有提交人姓名 / 部门字段，
               这里如实显示用户编号，不臆造姓名，也不再把用户编号伪装成"部门"。 -->
          <div class="detail-info__item">
            <span class="detail-info__item-label">提交人：</span>
            <span class="detail-info__item-value">用户#{{ expense.user_id }}</span>
          </div>
          <div class="detail-info__item">
            <span class="detail-info__item-label">创建时间：</span>
            <span class="detail-info__item-value">{{ formatDate(expense.created_at) }}</span>
          </div>
          <div class="detail-info__item" v-if="expense.submitted_at">
            <span class="detail-info__item-label">提交时间：</span>
            <span class="detail-info__item-value">{{ formatDate(expense.submitted_at) }}</span>
          </div>
          <div class="detail-info__item detail-info__item--full">
            <span class="detail-info__item-label">描述：</span>
            <span class="detail-info__item-value">{{ expense.description || '无' }}</span>
          </div>
        </div>
      </el-card>

      <!-- Expense Items -->
      <el-card class="mb-md">
        <template #header>
          <span class="card-header-title">费用明细</span>
        </template>
        <el-table :data="expense.items" border stripe>
          <el-table-column label="序号" width="60" align="center">
            <template #default="{ $index }">{{ $index + 1 }}</template>
          </el-table-column>
          <!-- category_id 是费用类别表的主键，与 ExpenseTypeLabels（报销类型枚举）
               不是同一套字典，不能拿它去查表，否则永远查不中并回落成数字。 -->
          <el-table-column label="费用类别" width="120">
            <template #default="{ row }">
              {{ row.category_id ?? '-' }}
            </template>
          </el-table-column>
          <el-table-column label="发票号" width="150" show-overflow-tooltip>
            <template #default="{ row }">
              {{ row.invoice_no || '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
          <el-table-column label="金额" width="140" align="right">
            <template #default="{ row }">
              <span class="amount-cell">¥{{ row.amount.toFixed(2) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="日期" width="120">
            <template #default="{ row }">
              {{ formatDate(row.expense_date, 'YYYY-MM-DD') }}
            </template>
          </el-table-column>
          <el-table-column label="发票" width="100" align="center">
            <template #default="{ row }">
              <el-button
                v-if="row.invoice_url"
                link
                type="primary"
                size="small"
                @click="handlePreviewInvoice(row)"
              >
                查看
              </el-button>
              <span v-else class="text-secondary">无</span>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <!-- AI Review -->
      <el-card v-if="expense.ai_review_result" class="mb-md ai-review-card">
        <template #header>
          <div class="ai-review-header">
            <el-icon size="20" color="#409eff"><Cpu /></el-icon>
            <span class="card-header-title">AI 审核结果</span>
            <el-tag
              :type="getRiskTagType(expense.ai_review_result.risk_level)"
              size="small"
            >
              风险等级：{{ getRiskLabel(expense.ai_review_result.risk_level) }}
            </el-tag>
          </div>
        </template>
        <div class="ai-review-body">
          <div class="ai-review-summary">
            <strong>审核摘要：</strong>{{ formatAiSummary(expense.ai_review_result.summary) }}
          </div>
          <div v-if="expense.ai_review_result.issues && expense.ai_review_result.issues.length > 0" class="mt-md">
            <strong>发现的问题：</strong>
            <div
              v-for="(issue, idx) in expense.ai_review_result.issues"
              :key="idx"
              class="ai-review-issue"
              :class="`ai-review-issue--${issue.severity}`"
            >
              <el-tag :type="issue.severity === 'high' ? 'danger' : issue.severity === 'medium' ? 'warning' : 'info'" size="small">
                {{ issue.severity === 'high' ? '严重' : issue.severity === 'medium' ? '中等' : '轻微' }}
              </el-tag>
              <span>{{ issue.description }}</span>
            </div>
          </div>
          <div v-if="expense.ai_review_result.suggestions && expense.ai_review_result.suggestions.length > 0" class="mt-md">
            <strong>改进建议：</strong>
            <ul class="suggestion-list">
              <li v-for="(sug, idx) in expense.ai_review_result.suggestions" :key="idx">{{ sug }}</li>
            </ul>
          </div>
        </div>
      </el-card>

      <!-- Approval History -->
      <el-card v-if="approvalRecords.length > 0" class="mb-md">
        <template #header>
          <span class="card-header-title">审批记录</span>
        </template>
        <ApprovalHistory :records="approvalRecords" />
      </el-card>

      <!-- Action Buttons -->
      <div class="form-actions" v-if="canAct">
        <el-button
          v-if="expense.status === 'draft'"
          type="primary"
          :icon="Upload"
          :loading="actionLoading"
          @click="handleSubmit"
        >
          提交审批
        </el-button>
        <el-button
          v-if="expense.status === 'pending' && isOwner"
          type="warning"
          :icon="Download"
          :loading="actionLoading"
          @click="handleWithdraw"
        >
          撤回
        </el-button>
        <!-- 只有当前用户名下确实存在一条 pending 审批记录时才允许直接审批，
             否则没有可用的 approval_id，点了必然打到错误的记录上。 -->
        <template v-if="expense.status === 'pending' && canApprove">
          <template v-if="myPendingApproval">
            <el-button
              type="success"
              :icon="Select"
              :loading="actionLoading"
              @click="handleApprove"
            >
              通过
            </el-button>
            <el-button
              type="danger"
              :icon="CloseBold"
              :loading="actionLoading"
              @click="handleReject"
            >
              驳回
            </el-button>
          </template>
          <el-tooltip
            v-else
            content="当前没有分配给你的待办审批记录，请到审批中心处理"
            placement="top"
          >
            <span class="approve-disabled-hint">
              <el-button type="success" :icon="Select" disabled>通过</el-button>
              <el-button type="danger" :icon="CloseBold" disabled>驳回</el-button>
            </span>
          </el-tooltip>
        </template>
        <el-button
          v-if="expense.status === 'pending' || expense.status === 'draft'"
          type="info"
          @click="handleAIReview"
          :loading="aiReviewLoading"
        >
          <el-icon><Cpu /></el-icon>
          AI审核
        </el-button>
        <el-button @click="handleBack">返回</el-button>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
// Upload / Download / Select / CloseBold 以 `:icon="..."` 绑定表达式引用，必须显式 import
import { Upload, Download, Select, CloseBold } from '@element-plus/icons-vue'
import { getExpenseDetail, submitExpense, withdrawExpense, aiReviewExpense } from '@/api/expense'
import { approveExpense, rejectExpense, getApprovalHistoryByExpense } from '@/api/approval'
import { useUserStore } from '@/stores/user'
import type { Expense, ExpenseItem, ApprovalRecord } from '@/types/expense'
import { ExpenseStatusLabels, ExpenseStatusColors, ExpenseTypeLabels } from '@/types/expense'
import { formatDate } from '@/utils/helpers'
import ApprovalHistory from '@/components/approval/ApprovalHistory.vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const expense = ref<Expense | null>(null)
const approvalRecords = ref<ApprovalRecord[]>([])
const loading = ref(false)
const actionLoading = ref(false)
const aiReviewLoading = ref(false)

const isOwner = computed(() => {
  return expense.value?.user_id === userStore.user?.id
})

const canApprove = computed(() => {
  return userStore.hasPermission(['admin', 'finance']) && !isOwner.value
})

/**
 * 当前登录用户名下、属于本报销单的那条【待审批记录】。
 * ⚠️ POST /approvals/{approval_id}/approve|reject 收的是【审批记录 id】，
 *    绝不能传报销单 id —— 那会命中另一条毫不相干的审批记录。
 */
const myPendingApproval = computed<ApprovalRecord | undefined>(() => {
  const uid = userStore.user?.id
  if (!uid) return undefined
  return approvalRecords.value.find(
    (r) => r.status === 'pending' && r.approver_id === uid
  )
})

const canAct = computed(() => {
  if (!expense.value) return false
  if (expense.value.status === 'draft' && isOwner.value) return true
  if (expense.value.status === 'pending' && (isOwner.value || canApprove.value)) return true
  return false
})

function getStatusLabel(status: string): string {
  return ExpenseStatusLabels[status] || status
}

function getStatusColor(status: string): string {
  return ExpenseStatusColors[status] || 'info'
}

function getTypeLabel(type: string): string {
  return ExpenseTypeLabels[type] || type
}

function getRiskLabel(level: string): string {
  const labels: Record<string, string> = {
    low: '低',
    medium: '中',
    high: '高',
    critical: '极高'
  }
  return labels[level] || level
}

/** critical 必须排在 high 之前判断，否则极高风险会被渲染成 success（绿色）。 */
function getRiskTagType(level: string): 'danger' | 'warning' | 'success' {
  if (level === 'critical' || level === 'high') return 'danger'
  if (level === 'medium') return 'warning'
  return 'success'
}

async function fetchDetail() {
  const id = Number(route.params.id)
  if (!id) {
    router.push('/expense/list')
    return
  }

  loading.value = true
  try {
    const res = await getExpenseDetail(id)
    expense.value = res.data
    // 审批记录走专用接口（后端 /approvals/{expense_id}/history，返回裸数组），
    // 不再依赖 expense.approval_records 内联字段。
    await fetchApprovalRecords(id)
  } catch (error) {
    console.error('Fetch expense detail error:', error)
    ElMessage.error('获取报销单详情失败')
  } finally {
    loading.value = false
  }
}

async function fetchApprovalRecords(expenseId: number) {
  try {
    const res = await getApprovalHistoryByExpense(expenseId)
    approvalRecords.value = res.data || []
  } catch (error) {
    console.error('Fetch approval history error:', error)
    approvalRecords.value = []
  }
}

/** 兼容 summary 为字符串或结构化对象的渲染 */
function formatAiSummary(summary: string | Record<string, any> | undefined): string {
  if (!summary) return '无'
  if (typeof summary === 'string') return summary
  if (typeof summary === 'object') {
    const parts: string[] = []
    if (summary.overall) parts.push(String(summary.overall))
    if (summary.conclusion) parts.push(String(summary.conclusion))
    if (summary.summary) parts.push(String(summary.summary))
    if (parts.length > 0) return parts.join('；')
    try {
      return JSON.stringify(summary, null, 2)
    } catch {
      return '（结构化审核摘要）'
    }
  }
  return String(summary)
}

async function handleSubmit() {
  if (!expense.value) return
  try {
    await ElMessageBox.confirm('确认提交此报销单？提交后将进入审批流程。', '确认提交', {
      confirmButtonText: '确认提交',
      cancelButtonText: '取消',
      type: 'info'
    })
    actionLoading.value = true
    await submitExpense(expense.value.id)
    ElMessage.success('报销单已提交审批')
    await fetchDetail()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('Submit error:', error)
    }
  } finally {
    actionLoading.value = false
  }
}

async function handleWithdraw() {
  if (!expense.value) return
  try {
    await ElMessageBox.confirm('确认撤回此报销单？', '确认撤回', {
      confirmButtonText: '确认撤回',
      cancelButtonText: '取消',
      type: 'warning'
    })
    actionLoading.value = true
    await withdrawExpense(expense.value.id)
    ElMessage.success('报销单已撤回')
    await fetchDetail()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('Withdraw error:', error)
    }
  } finally {
    actionLoading.value = false
  }
}

async function handleApprove() {
  if (!expense.value) return
  const approvalId = myPendingApproval.value?.id
  if (!approvalId) {
    ElMessage.warning('当前没有分配给你的待办审批记录，请到审批中心处理')
    return
  }
  try {
    const { value: comment } = await ElMessageBox.prompt('请输入审批意见（可选）', '审批通过', {
      confirmButtonText: '确认通过',
      cancelButtonText: '取消',
      inputType: 'textarea',
      inputPlaceholder: '请输入审批意见...'
    })
    actionLoading.value = true
    await approveExpense(approvalId, comment || undefined)
    ElMessage.success('审批已通过')
    await fetchDetail()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('Approve error:', error)
    }
  } finally {
    actionLoading.value = false
  }
}

async function handleReject() {
  if (!expense.value) return
  const approvalId = myPendingApproval.value?.id
  if (!approvalId) {
    ElMessage.warning('当前没有分配给你的待办审批记录，请到审批中心处理')
    return
  }
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
    actionLoading.value = true
    await rejectExpense(approvalId, comment || '')
    ElMessage.success('报销单已驳回')
    await fetchDetail()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('Reject error:', error)
    }
  } finally {
    actionLoading.value = false
  }
}

async function handleAIReview() {
  if (!expense.value) return
  aiReviewLoading.value = true
  try {
    await aiReviewExpense(expense.value.id)
    ElMessage.success('AI审核完成')
    await fetchDetail()
  } catch (error) {
    console.error('AI review error:', error)
  } finally {
    aiReviewLoading.value = false
  }
}

/** 发票文件由后端以 /uploads/... 静态目录提供，已通过 vite 代理同源访问，直接新窗口打开即可。 */
function handlePreviewInvoice(item: ExpenseItem) {
  if (!item.invoice_url) {
    ElMessage.warning('该费用明细没有关联发票')
    return
  }
  window.open(item.invoice_url, '_blank', 'noopener')
}

function handleBack() {
  router.back()
}

onMounted(() => {
  fetchDetail()
})
</script>

<style scoped lang="scss">
@import '@/styles/variables.scss';

.expense-detail {
  max-width: 1100px;
}

.card-header-title {
  font-weight: 600;
  font-size: $font-size-lg;
}

.detail-info {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: $spacing-md;

  &__item {
    display: flex;
    align-items: flex-start;

    &-label {
      width: 100px;
      color: $text-secondary;
      flex-shrink: 0;
    }

    &-value {
      flex: 1;
      color: $text-primary;
    }

    &--full {
      grid-column: span 2;
    }
  }
}

.amount-highlight {
  font-size: $font-size-lg;
  font-weight: 700;
  color: $primary-color;
  font-family: 'Courier New', monospace;
}

.amount-cell {
  font-weight: 600;
  color: $primary-color;
  font-family: 'Courier New', monospace;
}

.ai-review-header {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
}

.ai-review-card {
  border-left: 4px solid $primary-color;
}

.ai-review-body {
  padding: $spacing-sm 0;
}

.ai-review-summary {
  line-height: 1.8;
  color: $text-regular;
}

.ai-review-issue {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  padding: $spacing-xs 0;

  &--high {
    background: $danger-light;
    padding: $spacing-sm;
    border-radius: $border-radius-sm;
    margin: $spacing-xs 0;
  }
}

.suggestion-list {
  padding-left: $spacing-lg;

  li {
    list-style: disc;
    padding: $spacing-xs 0;
    color: $text-regular;
    line-height: 1.6;
  }
}

.timeline-item {
  display: flex;
  align-items: center;
}

.timeline-comment {
  color: $text-secondary;
  margin-top: 4px;
  font-size: $font-size-sm;
}

.form-actions {
  display: flex;
  justify-content: center;
  gap: $spacing-sm;
  padding: $spacing-lg 0;
}

// el-tooltip 无法直接挂在 disabled 的按钮上（disabled 元素不触发鼠标事件），
// 故用一个 inline-flex 包裹层承载 tooltip。
.approve-disabled-hint {
  display: inline-flex;
  gap: $spacing-sm;
}

.ml-sm {
  margin-left: $spacing-sm;
}
</style>
