<template>
  <div class="approval-history">
    <el-timeline v-if="records.length > 0">
      <el-timeline-item
        v-for="record in records"
        :key="record.id"
        :timestamp="formatDate(record.created_at || '')"
        :type="getStatusType(record.status)"
        :icon="getStatusIcon(record.status)"
        placement="top"
      >
        <el-card shadow="hover" class="history-card">
          <div class="history-card__header">
            <div class="history-card__user">
              <el-avatar :size="32" icon="UserFilled" />
              <div>
                <!-- approver_name 后端可能为 null，回落到用户编号，不留空、也不臆造姓名 -->
                <div class="history-card__name">
                  {{ record.approver_name || ('审批人#' + record.approver_id) }}
                </div>
                <div class="history-card__role">审批人</div>
              </div>
            </div>
            <el-tag
              :type="getStatusType(record.status)"
              size="default"
              effect="dark"
            >
              {{ getStatusLabel(record.status) }}
            </el-tag>
          </div>
          <div v-if="record.comment" class="history-card__comment">
            <div class="history-card__comment-label">审批意见：</div>
            <div class="history-card__comment-text">{{ record.comment }}</div>
          </div>
        </el-card>
      </el-timeline-item>
    </el-timeline>

    <el-empty v-else description="暂无审批记录" :image-size="80" />
  </div>
</template>

<script setup lang="ts">
import type { ApprovalRecord } from '@/types/expense'
import { ApprovalStatusLabels, ApprovalStatusColors } from '@/types/expense'
import { formatDate } from '@/utils/helpers'
import { CircleCheck, CircleClose, RefreshLeft, Clock } from '@element-plus/icons-vue'

// 后端 ApprovalResponse 没有 `action` 字段，审批动作体现在 `status` 上。
// 这里复用类型层已定义好的四态标签/配色，并映射对应的 Element Plus 图标组件。
const statusIcons: Record<string, any> = {
  approved: CircleCheck,
  rejected: CircleClose,
  returned: RefreshLeft,
  pending: Clock
}

function getStatusIcon(status: string): any {
  return statusIcons[status] || Clock
}

function getStatusLabel(status: string): string {
  return ApprovalStatusLabels[status] || status
}

// el-timeline-item 的 type 仅接受特定字面量联合，这里用显式映射保证类型安全
function getStatusType(
  status: string
): 'success' | 'info' | 'warning' | 'danger' | 'primary' {
  return (
    (ApprovalStatusColors[status] as
      | 'success'
      | 'info'
      | 'warning'
      | 'danger'
      | 'primary') || 'info'
  )
}

defineProps<{
  records: ApprovalRecord[]
}>()
</script>

<style scoped lang="scss">
@import '@/styles/variables.scss';

.approval-history {
  padding: $spacing-md 0;
}

.history-card {
  margin-bottom: $spacing-sm;

  &__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  &__user {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
  }

  &__name {
    font-weight: 600;
    color: $text-primary;
  }

  &__role {
    font-size: $font-size-sm;
    color: $text-secondary;
  }

  &__comment {
    margin-top: $spacing-sm;
    padding-top: $spacing-sm;
    border-top: 1px solid $border-color;

    &-label {
      font-size: $font-size-sm;
      color: $text-secondary;
      margin-bottom: 4px;
    }

    &-text {
      color: $text-regular;
      line-height: 1.6;
    }
  }
}
</style>
