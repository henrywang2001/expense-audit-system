<template>
  <div class="expense-list-page">
    <div class="page-header">
      <h2 class="page-header__title">我的报销</h2>
      <div class="page-header__actions">
        <el-button type="primary" :icon="Plus" @click="$router.push('/expense/submit')">
          新建报销
        </el-button>
      </div>
    </div>
    <ExpenseListComponent />
  </div>
</template>

<script setup lang="ts">
import { Plus } from '@element-plus/icons-vue'
import ExpenseListComponent from '@/components/expense/ExpenseList.vue'
</script>
