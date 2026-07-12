<template>
  <div class="expense-submit-page">
    <div class="page-header">
      <h2 class="page-header__title">提交报销</h2>
    </div>
    <div class="card-container">
      <ExpenseForm />
    </div>
  </div>
</template>

<script setup lang="ts">
import ExpenseForm from '@/components/expense/ExpenseForm.vue'
</script>

<style scoped lang="scss">
.expense-submit-page {
  max-width: 1100px;
}
</style>
