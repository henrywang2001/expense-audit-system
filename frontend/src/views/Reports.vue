<template>
  <div class="reports-page">
    <div class="page-header">
      <h2 class="page-header__title">统计报表</h2>
      <div class="page-header__actions">
        <el-button type="primary" :icon="Refresh" :loading="loading" @click="fetchStats">刷新</el-button>
      </div>
    </div>

    <!-- Summary Cards -->
    <div class="stat-cards" v-loading="loading">
      <div class="stat-card">
        <div class="stat-card__icon stat-card__icon--blue">
          <el-icon><Document /></el-icon>
        </div>
        <div class="stat-card__info">
          <div class="stat-card__label">报销总数</div>
          <div class="stat-card__value">{{ totalExpenses }}</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-card__icon stat-card__icon--green">
          <el-icon><Money /></el-icon>
        </div>
        <div class="stat-card__info">
          <div class="stat-card__label">总金额</div>
          <div class="stat-card__value">¥{{ formatNumber(totalAmount) }}</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-card__icon stat-card__icon--orange">
          <el-icon><CircleCheck /></el-icon>
        </div>
        <div class="stat-card__info">
          <div class="stat-card__label">通过率</div>
          <div class="stat-card__value">{{ approvalRate }}%</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-card__icon stat-card__icon--red">
          <el-icon><Warning /></el-icon>
        </div>
        <div class="stat-card__info">
          <div class="stat-card__label">驳回率</div>
          <div class="stat-card__value">{{ rejectionRate }}%</div>
        </div>
      </div>
    </div>

    <!-- Charts -->
    <div class="charts-grid" v-loading="loading">
      <!-- Pie Chart - Expense by Type -->
      <el-card class="chart-card">
        <template #header>
          <span class="chart-card__title">报销类型分布</span>
        </template>
        <div class="chart-container">
          <v-chart :option="typePieOption" autoresize v-if="hasTypeData" />
          <el-empty v-else description="暂无数据" :image-size="80" />
        </div>
      </el-card>

      <!-- Bar Chart - Expense by Month -->
      <el-card class="chart-card">
        <template #header>
          <span class="chart-card__title">月度报销趋势</span>
        </template>
        <div class="chart-container">
          <v-chart :option="monthBarOption" autoresize v-if="hasMonthData" />
          <el-empty v-else description="暂无数据" :image-size="80" />
        </div>
      </el-card>

      <!-- Bar Chart - Expense by Department -->
      <el-card class="chart-card chart-card--full">
        <template #header>
          <span class="chart-card__title">部门报销统计</span>
        </template>
        <div class="chart-container">
          <v-chart :option="deptBarOption" autoresize v-if="hasDeptData" />
          <el-empty v-else description="暂无数据" :image-size="80" />
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { PieChart, BarChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent
} from 'echarts/components'
import { getReportSummary, getReportByType, getReportByDepartment, getReportTrend } from '@/api/report'
import { ExpenseTypeLabels } from '@/types/expense'

use([CanvasRenderer, PieChart, BarChart, TitleComponent, TooltipComponent, LegendComponent, GridComponent])

const loading = ref(false)

const summary = ref<any>({})
const typeStats = ref<any[]>([])
const deptStats = ref<any[]>([])
const trendStats = ref<any[]>([])

const totalExpenses = computed(() => summary.value?.total_count || 0)
const totalAmount = computed(() => summary.value?.total_amount || 0)
const approvedCount = computed(() => summary.value?.status_distribution?.approved?.count || 0)
const rejectedCount = computed(() => summary.value?.status_distribution?.rejected?.count || 0)

const approvalRate = computed(() => {
  if (totalExpenses.value === 0) return 0
  return ((approvedCount.value / totalExpenses.value) * 100).toFixed(1)
})

const rejectionRate = computed(() => {
  if (totalExpenses.value === 0) return 0
  return ((rejectedCount.value / totalExpenses.value) * 100).toFixed(1)
})

const hasTypeData = computed(() => typeStats.value.length > 0)
const hasMonthData = computed(() => trendStats.value.length > 0)
const hasDeptData = computed(() => deptStats.value.length > 0)

const techColors = ['#00d4ff', '#7c3aed', '#f59e0b', '#ef4444', '#10b981', '#6366f1', '#ec4899']

const textStyle = { color: '#b0b8d0' }

const typePieOption = computed(() => {
  if (!hasTypeData.value) return {}
  const data = typeStats.value.map((item: any) => ({
    name: (ExpenseTypeLabels as Record<string, string>)[item.expense_type] || item.expense_type,
    value: item.total_amount
  }))
  return {
    tooltip: {
      trigger: 'item' as const,
      formatter: '{b}: ¥{c} ({d}%)',
      backgroundColor: 'rgba(13, 17, 23, 0.95)',
      borderColor: 'rgba(0, 212, 255, 0.3)',
      borderWidth: 1,
      textStyle: { color: '#f0f4fa' }
    },
    legend: {
      orient: 'vertical' as const,
      right: 10,
      top: 'center',
      textStyle
    },
    color: techColors,
    series: [
      {
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['40%', '50%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 4,
          borderColor: '#0f1729',
          borderWidth: 2
        },
        label: {
          show: false
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 14,
            fontWeight: 'bold' as const,
            color: '#f0f4fa'
          },
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: 'rgba(0, 0, 0, 0.5)'
          }
        },
        data
      }
    ]
  }
})

const monthBarOption = computed(() => {
  if (!hasMonthData.value) return {}
  const months = trendStats.value.map((item: any) => item.month)
  const amounts = trendStats.value.map((item: any) => item.total_amount)
  const counts = trendStats.value.map((item: any) => item.count)
  return {
    tooltip: {
      trigger: 'axis' as const,
      axisPointer: { type: 'shadow' as const },
      backgroundColor: 'rgba(13, 17, 23, 0.95)',
      borderColor: 'rgba(0, 212, 255, 0.3)',
      borderWidth: 1,
      textStyle: { color: '#f0f4fa' }
    },
    legend: {
      data: ['报销金额', '报销数量'],
      textStyle
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category' as const,
      data: months,
      axisLabel: { rotate: 30, ...textStyle },
      axisLine: { lineStyle: { color: 'rgba(0, 212, 255, 0.2)' } },
      axisTick: { lineStyle: { color: 'rgba(0, 212, 255, 0.2)' } }
    },
    yAxis: [
      {
        type: 'value' as const,
        name: '金额 (元)',
        nameTextStyle: textStyle,
        axisLabel: {
          formatter: (val: number) => {
            if (val >= 10000) return (val / 10000).toFixed(0) + '万'
            return val.toString()
          },
          ...textStyle
        },
        splitLine: { lineStyle: { color: 'rgba(0, 212, 255, 0.08)' } },
        axisLine: { lineStyle: { color: 'rgba(0, 212, 255, 0.2)' } }
      },
      {
        type: 'value' as const,
        name: '数量',
        nameTextStyle: textStyle,
        axisLabel: textStyle,
        splitLine: { show: false },
        axisLine: { lineStyle: { color: 'rgba(0, 212, 255, 0.2)' } }
      }
    ],
    color: techColors,
    series: [
      {
        name: '报销金额',
        type: 'bar',
        data: amounts,
        itemStyle: {
          borderRadius: [4, 4, 0, 0],
          color: {
            type: 'linear' as const,
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: '#00d4ff' },
              { offset: 1, color: '#007799' }
            ]
          }
        },
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowColor: 'rgba(0, 212, 255, 0.3)'
          }
        }
      },
      {
        name: '报销数量',
        type: 'bar',
        yAxisIndex: 1,
        data: counts,
        itemStyle: {
          borderRadius: [4, 4, 0, 0],
          color: {
            type: 'linear' as const,
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: '#10b981' },
              { offset: 1, color: '#065f46' }
            ]
          }
        },
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowColor: 'rgba(16, 185, 129, 0.3)'
          }
        }
      }
    ]
  }
})

const deptBarOption = computed(() => {
  if (!hasDeptData.value) return {}
  const departments = deptStats.value.map((item: any) => item.department)
  const amounts = deptStats.value.map((item: any) => item.total_amount)
  return {
    tooltip: {
      trigger: 'axis' as const,
      axisPointer: { type: 'shadow' as const },
      backgroundColor: 'rgba(13, 17, 23, 0.95)',
      borderColor: 'rgba(0, 212, 255, 0.3)',
      borderWidth: 1,
      textStyle: { color: '#f0f4fa' }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category' as const,
      data: departments,
      axisLabel: { rotate: 30, ...textStyle },
      axisLine: { lineStyle: { color: 'rgba(0, 212, 255, 0.2)' } },
      axisTick: { lineStyle: { color: 'rgba(0, 212, 255, 0.2)' } }
    },
    yAxis: {
      type: 'value' as const,
      name: '金额 (元)',
      nameTextStyle: textStyle,
      axisLabel: {
        formatter: (val: number) => {
          if (val >= 10000) return (val / 10000).toFixed(0) + '万'
          return val.toString()
        },
        ...textStyle
      },
      splitLine: { lineStyle: { color: 'rgba(0, 212, 255, 0.08)' } },
      axisLine: { lineStyle: { color: 'rgba(0, 212, 255, 0.2)' } }
    },
    color: techColors,
    series: [
      {
        type: 'bar',
        data: amounts.map((val: number) => ({
          value: val,
          itemStyle: {
            color: {
              type: 'linear' as const,
              x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [
                { offset: 0, color: val === Math.max(...amounts, 1) ? '#00d4ff' : '#6366f1' },
                { offset: 1, color: val === Math.max(...amounts, 1) ? '#007799' : '#3730a3' }
              ]
            }
          }
        })),
        itemStyle: {
          borderRadius: [4, 4, 0, 0]
        },
        label: {
          show: true,
          position: 'top' as const,
          formatter: (params: any) => {
            const v = params.value?.value || params.value
            return v >= 10000 ? (v / 10000).toFixed(1) + '万' : v.toFixed(1)
          },
          color: '#b0b8d0'
        },
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowColor: 'rgba(0, 212, 255, 0.3)'
          }
        }
      }
    ]
  }
})

function formatNumber(num: number): string {
  if (num >= 10000) {
    return (num / 10000).toFixed(2) + '万'
  }
  return num.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

async function fetchStats() {
  loading.value = true
  try {
    // 报表接口均不消费 start_date/end_date 等 Query 参数（见 @/api/report 注释），
    // 故直接无参调用并保留 `res.data` 取值。
    const [summaryRes, typeRes, deptRes, trendRes] = await Promise.all([
      getReportSummary(),
      getReportByType(),
      getReportByDepartment(),
      getReportTrend(12)
    ])
    summary.value = summaryRes.data || {}
    typeStats.value = typeRes.data || []
    deptStats.value = deptRes.data || []
    trendStats.value = trendRes.data || []
  } catch (error) {
    console.error('Fetch statistics error:', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchStats()
})
</script>

<style scoped lang="scss">
@import '@/styles/variables.scss';

.reports-page {
  // Inherits global styles
}

.charts-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: $spacing-md;

  @media (max-width: 1400px) {
    grid-template-columns: 1fr;
  }
}

.chart-card {
  background: $tech-dark-card;
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid $tech-border;
  border-radius: $border-radius-lg;
  box-shadow: $box-shadow-light;
  transition: all 0.3s ease;

  &:hover {
    box-shadow: $box-shadow;
    border-color: rgba(0, 212, 255, 0.4);
  }

  &__title {
    font-weight: 600;
    font-size: $font-size-lg;
    color: $text-primary;
  }

  &--full {
    grid-column: span 2;

    @media (max-width: 1400px) {
      grid-column: span 1;
    }
  }
}

.chart-container {
  height: 350px;
}
</style>
