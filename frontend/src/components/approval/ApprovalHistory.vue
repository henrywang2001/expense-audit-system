<template>
  <div class="approval-history">
    <el-timeline v-if="records.length > 0">
      <el-timeline-item
        v-for="record in records"
        :key="record.id"
        :timestamp="formatDate(record.created_at)"
        :type="record.action === 'approve' ? 'success' : 'danger'"
        :icon="record.action === 'approve' ? 'CircleCheck' : 'CircleClose'"
        placement="top"
      >
        <el-card shadow="hover" class="history-card">
          <div class="history-card__header">
            <div class="history-card__user">
              <el-avatar :size="32" icon="UserFilled" />
              <div>
                <div class="history-card__name">{{ record.approver_name }}</div>
                <div class="history-card__role">审批人</div>
              </div>
            </div>
            <el-tag
              :type="record.action === 'approve' ? 'success' : 'danger'"
              size="default"
              effect="dark"
            >
              {{ record.action === 'approve' ? '通过' : '驳回' }}
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
import { formatDate } from '@/utils/helpers'

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
