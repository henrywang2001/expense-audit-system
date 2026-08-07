<template>
  <div class="approval-flow">
    <el-steps :active="activeStep" align-center finish-status="success">
      <el-step title="提交报销" description="员工提交报销申请" />
      <el-step title="AI审核" description="AI自动审核风险" />
      <el-step title="主管审批" description="部门主管审批" />
      <el-step title="财务审批" description="财务部门终审" />
      <el-step title="完成" description="报销完成入账" />
    </el-steps>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  status: string
  hasAIReview?: boolean
}>()

// 键必须取自后端 ExpenseStatus 七态（draft/submitted/pending/approved/rejected/paid/cancelled），
// 不存在 `withdrawn` 状态：撤回后报销单回到 draft。
const stepMap: Record<string, number> = {
  draft: 0,
  submitted: 1,
  pending: 1,
  approved: 4,
  rejected: 0,
  paid: 4,
  cancelled: 0
}

const activeStep = computed(() => {
  let step = stepMap[props.status] ?? 1
  if (step === 1 && props.hasAIReview) {
    step = 2
  }
  return step
})
</script>

<style scoped lang="scss">
.approval-flow {
  padding: 24px;
  background: transparent;
  border-radius: 8px;
}
</style>
