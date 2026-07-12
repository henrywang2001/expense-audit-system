<template>
  <div class="expense-detail-page">
    <div class="page-header">
      <h2 class="page-header__title">报销详情</h2>
      <div class="page-header__actions">
        <el-button :icon="ArrowLeft" @click="$router.back()">返回</el-button>
      </div>
    </div>
    <ExpenseDetail />
  </div>
</template>

<script setup lang="ts">
import { ArrowLeft } from '@element-plus/icons-vue'
import ExpenseDetail from '@/components/expense/ExpenseDetail.vue'
</script>
