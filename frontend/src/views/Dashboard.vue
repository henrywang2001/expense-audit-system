<template>
  <div class="dashboard">
    <!-- Tech Decoration Grid -->
    <div class="tech-grid"></div>
    <div class="tech-data-flow"></div>

    <!-- Stat Cards -->
    <div class="stat-cards">
      <div class="stat-card" v-for="(stat, index) in statsData" :key="index" :style="{ animationDelay: index * 0.1 + 's' }">
        <div :class="['stat-card__icon', 'stat-card__icon--' + stat.color]">
          <el-icon><component :is="stat.icon" /></el-icon>
        </div>
        <div class="stat-card__info">
          <div class="stat-card__label">{{ stat.label }}</div>
          <div class="stat-card__value">
            <span v-if="stat.prefix">{{ stat.prefix }}</span>
            {{ displayValue(stat.key) }}
          </div>
        </div>
        <div class="stat-card__glow" :style="{ background: stat.glowColor }"></div>
      </div>
    </div>

    <!-- Quick Actions -->
    <div class="quick-actions">
      <div class="quick-action-btn" v-for="(action, index) in quickActions" :key="index" @click="$router.push(action.route)">
        <el-icon><component :is="action.icon" /></el-icon>
        <span>{{ action.label }}</span>
      </div>
    </div>

    <!-- Dashboard Grid -->
    <div class="dashboard-grid">
      <!-- Pending Approvals -->
      <div class="dashboard-card" :class="{ 'card-visible': true }">
        <div class="dashboard-card__header">
          <h3>待审批报销</h3>
          <el-button link type="primary" @click="$router.push('/approval')">
            查看全部
            <el-icon><ArrowRight /></el-icon>
          </el-button>
        </div>
        <div class="dashboard-card__body">
          <el-table
            v-loading="statsLoading"
            :data="pendingList"
            size="small"
            style="width: 100%"
            empty-text="暂无待审批报销"
          >
            <el-table-column prop="expense_no" label="编号" width="150" />
            <el-table-column prop="title" label="标题" show-overflow-tooltip />
            <el-table-column label="金额" width="120" align="right">
              <template #default="{ row }">
                <span class="amount-cell">
                  ¥{{ row.total_amount.toFixed(2) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="user_id" label="提交人ID" width="100" />
            <el-table-column label="操作" width="80" align="center">
              <template #default="{ row }">
                <el-button link type="primary" size="small" @click="$router.push(`/expense/detail/${row.id}`)">
                  处理
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>

      <!-- Recent Expenses -->
      <div class="dashboard-card" :class="{ 'card-visible': true }">
        <div class="dashboard-card__header">
          <h3>最近报销</h3>
          <el-button link type="primary" @click="$router.push('/expense/list')">
            查看全部
            <el-icon><ArrowRight /></el-icon>
          </el-button>
        </div>
        <div class="dashboard-card__body">
          <el-table
            v-loading="listLoading"
            :data="recentList"
            size="small"
            style="width: 100%"
            empty-text="暂无报销记录"
          >
            <el-table-column prop="expense_no" label="编号" width="150" />
            <el-table-column prop="title" label="标题" show-overflow-tooltip />
            <el-table-column label="状态" width="80" align="center">
              <template #default="{ row }">
                <el-tag :type="getStatusColor(row.status)" size="small">
                  {{ getStatusLabel(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="金额" width="120" align="right">
              <template #default="{ row }">
                <span class="amount-cell">
                  ¥{{ row.total_amount.toFixed(2) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="80" align="center">
              <template #default="{ row }">
                <el-button link type="primary" size="small" @click="$router.push(`/expense/detail/${row.id}`)">
                  查看
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import { getExpenseList, getStatistics } from '@/api/expense'
import type { Expense, Statistics } from '@/types/expense'
import { ExpenseStatusLabels, ExpenseStatusColors } from '@/types/expense'

const stats = ref<Statistics | null>(null)
const statsLoading = ref(false)
const pendingList = ref<Expense[]>([])
const recentList = ref<Expense[]>([])
const listLoading = ref(false)

const displayValues = reactive<Record<string, string>>({
  total_amount: '0',
  approved_count: '0',
  pending_count: '0',
  rejected_count: '0'
})

const targetValues = reactive<Record<string, number>>({
  total_amount: 0,
  approved_count: 0,
  pending_count: 0,
  rejected_count: 0
})

const statsData = [
  { label: '本月报销总额', icon: 'Money', color: 'blue', key: 'total_amount', prefix: '¥', glowColor: 'rgba(0,212,255,0.08)' },
  { label: '已通过', icon: 'CircleCheck', color: 'green', key: 'approved_count', glowColor: 'rgba(16,185,129,0.08)' },
  { label: '待审批', icon: 'Clock', color: 'orange', key: 'pending_count', glowColor: 'rgba(245,158,11,0.08)' },
  { label: '已驳回', icon: 'CircleClose', color: 'red', key: 'rejected_count', glowColor: 'rgba(239,68,68,0.08)' }
]

const quickActions = [
  { icon: 'Edit', label: '提交报销', route: '/expense/submit' },
  { icon: 'Document', label: '我的报销', route: '/expense/list' },
  { icon: 'Checked', label: '审批中心', route: '/approval' },
  { icon: 'PieChart', label: '统计报表', route: '/reports' }
]

function formatNum(num: number): string {
  if (num >= 10000) {
    return (num / 10000).toFixed(2) + '万'
  }
  if (Number.isInteger(num)) {
    return num.toLocaleString('zh-CN')
  }
  return num.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function displayValue(key: string): string {
  return displayValues[key] || '0'
}

function getStatusLabel(status: string): string {
  return (ExpenseStatusLabels as Record<string, string>)[status] || status
}

function getStatusColor(status: string): string {
  return (ExpenseStatusColors as Record<string, string>)[status] || 'info'
}

function animateCounters() {
  const duration = 1500
  const steps = 30
  const interval = duration / steps
  let currentStep = 0

  const timer = setInterval(() => {
    currentStep++
    const progress = Math.min(currentStep / steps, 1)
    const easeProgress = 1 - Math.pow(1 - progress, 3)

    for (const key of ['total_amount', 'approved_count', 'pending_count', 'rejected_count']) {
      const val = targetValues[key] * easeProgress
      displayValues[key] = formatNum(val)
    }

    if (progress >= 1) {
      for (const key of ['total_amount', 'approved_count', 'pending_count', 'rejected_count']) {
        displayValues[key] = formatNum(targetValues[key])
      }
      clearInterval(timer)
    }
  }, interval)
}

async function fetchStats() {
  statsLoading.value = true
  try {
    const res = await getStatistics()
    const d = res.data
    stats.value = {
      total_expenses: d.total_count || 0,
      total_amount: d.total_amount || 0,
      pending_count: d.by_status?.pending?.count || 0,
      approved_count: d.by_status?.approved?.count || 0,
      rejected_count: d.by_status?.rejected?.count || 0,
      draft_count: d.by_status?.draft?.count || 0,
      monthly_stats: [],
      type_stats: Object.entries(d.by_type || {}).map(([k, v]: [string, any]) => ({ type: k, count: v.count, total_amount: v.amount })),
      department_stats: []
    }

    targetValues.total_amount = d.total_amount || 0
    targetValues.approved_count = d.by_status?.approved?.count || 0
    targetValues.pending_count = d.by_status?.pending?.count || 0
    targetValues.rejected_count = d.by_status?.rejected?.count || 0

    animateCounters()
  } catch (error) {
    console.error('Fetch statistics error:', error)
  } finally {
    statsLoading.value = false
  }
}

async function fetchPending() {
  try {
    const res = await getExpenseList({ page: 1, page_size: 5, status: 'pending' as any })
    pendingList.value = res.data || []
  } catch (error) {
    console.error('Fetch pending list error:', error)
  }
}

async function fetchRecent() {
  listLoading.value = true
  try {
    const res = await getExpenseList({ page: 1, page_size: 5 })
    recentList.value = res.data || []
  } catch (error) {
    console.error('Fetch recent list error:', error)
  } finally {
    listLoading.value = false
  }
}

onMounted(() => {
  fetchStats()
  fetchPending()
  fetchRecent()
})
</script>

<style scoped lang="scss">
.dashboard {
  position: relative;
}

// Tech background decoration
.tech-grid {
  position: fixed;
  top: 0;
  left: 240px;
  right: 0;
  bottom: 0;
  background-image:
    linear-gradient(rgba(0, 212, 255, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 212, 255, 0.03) 1px, transparent 1px);
  background-size: 40px 40px;
  pointer-events: none;
  z-index: 0;
}

.tech-data-flow {
  position: fixed;
  top: 0;
  left: 240px;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(0, 212, 255, 0.1), transparent);
  animation: dataFlow 3s ease-in-out infinite;
  pointer-events: none;
  z-index: 0;
}

@keyframes dataFlow {
  0%, 100% { transform: translateY(0); opacity: 0.3; }
  50% { transform: translateY(60px); opacity: 1; }
}

// Stat card glow decoration
.stat-card {
  position: relative;
  overflow: hidden;

  &__glow {
    position: absolute;
    top: -50%;
    right: -20%;
    width: 160px;
    height: 160px;
    border-radius: 50%;
    filter: blur(40px);
    pointer-events: none;
    opacity: 0.5;
    transition: all 0.3s ease;
  }

  &:hover &__glow {
    opacity: 1;
    transform: scale(1.2);
  }
}

// Amount highlight
.amount-cell {
  font-weight: 600;
  color: #00d4ff;
  font-family: 'Courier New', monospace;
}

// Card visibility animation
.card-visible {
  animation: fadeInUp 0.5s ease;
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
