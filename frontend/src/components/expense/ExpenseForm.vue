<template>
  <el-form
    ref="formRef"
    :model="formData"
    :rules="rules"
    label-width="100px"
    class="expense-form"
  >
    <!-- Basic Info -->
    <el-card class="mb-md">
      <template #header>
        <span class="card-header-title">基本信息</span>
      </template>
      <el-row :gutter="20">
        <el-col :span="12">
          <el-form-item label="报销标题" prop="title">
            <el-input v-model="formData.title" placeholder="请输入报销标题" maxlength="100" show-word-limit />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="报销类型" prop="expense_type">
            <el-select v-model="formData.expense_type" placeholder="请选择报销类型" style="width: 100%">
              <el-option
                v-for="(label, value) in typeOptions"
                :key="value"
                :label="label"
                :value="value"
              />
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item label="报销描述" prop="description">
        <el-input
          v-model="formData.description"
          type="textarea"
          :rows="3"
          placeholder="请输入报销描述"
          maxlength="500"
          show-word-limit
        />
      </el-form-item>
    </el-card>

    <!-- Expense Items -->
    <el-card class="mb-md">
      <template #header>
        <div class="flex-between">
          <span class="card-header-title">费用明细</span>
          <el-button type="primary" :icon="Plus" size="small" @click="addItem">
            添加费用项
          </el-button>
        </div>
      </template>

      <div v-if="formData.items.length === 0" class="empty-items">
        <el-empty description="暂无费用明细，请点击添加费用项" :image-size="80" />
      </div>

      <div v-else class="items-table">
        <el-table :data="formData.items" border stripe style="width: 100%">
          <el-table-column label="序号" width="60" align="center">
            <template #default="{ $index }">{{ $index + 1 }}</template>
          </el-table-column>
          <el-table-column label="费用类别" width="140">
            <template #default="{ row, $index }">
              <el-select v-model="row.category_id" placeholder="选择类别" size="small" clearable>
                <el-option label="差旅费" :value="1" />
                <el-option label="办公费" :value="2" />
                <el-option label="招待费" :value="3" />
                <el-option label="交通费" :value="4" />
                <el-option label="餐饮费" :value="5" />
                <el-option label="培训费" :value="6" />
                <el-option label="设备费" :value="7" />
                <el-option label="其他" :value="8" />
              </el-select>
            </template>
          </el-table-column>
          <el-table-column label="费用描述" min-width="180">
            <template #default="{ row, $index }">
              <el-input v-model="row.description" placeholder="费用描述" size="small" />
            </template>
          </el-table-column>
          <el-table-column label="金额" width="140">
            <template #default="{ row, $index }">
              <el-input-number
                v-model="row.amount"
                :min="0.01"
                :max="999999.99"
                :precision="2"
                :controls="false"
                size="small"
                style="width: 100%"
              />
            </template>
          </el-table-column>
          <el-table-column label="日期" width="160">
            <template #default="{ row, $index }">
              <el-date-picker
                v-model="row.expense_date"
                type="date"
                placeholder="选择日期"
                value-format="YYYY-MM-DD"
                size="small"
                style="width: 100%"
              />
            </template>
          </el-table-column>
          <el-table-column label="发票" width="120">
            <template #default="{ row, $index }">
              <el-upload
                :auto-upload="false"
                :limit="1"
                :show-file-list="false"
                @change="(file: any) => handleInvoiceUpload(file, $index)"
              >
                <el-button size="small" :type="row.invoice_url ? 'success' : 'default'">
                  {{ row.invoice_url ? '已上传' : '上传' }}
                </el-button>
              </el-upload>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="70" align="center">
            <template #default="{ $index }">
              <el-button type="danger" :icon="Delete" size="small" circle @click="removeItem($index)" />
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- Total -->
      <div class="total-amount" v-if="formData.items.length > 0">
        <span class="total-amount__label">合计金额：</span>
        <span class="total-amount__value">¥{{ totalAmount.toFixed(2) }}</span>
      </div>
    </el-card>

    <!-- Actions -->
    <div class="form-actions">
      <el-button @click="handleCancel">取消</el-button>
      <el-button type="primary" @click="handleSaveDraft" :loading="saving">
        保存草稿
      </el-button>
      <el-button type="success" @click="handleSubmit" :loading="submitting">
        提交审批
      </el-button>
    </div>
  </el-form>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { createExpense, submitExpense } from '@/api/expense'
import type { ExpenseCreate, ExpenseItemCreate } from '@/types/expense'
import { ExpenseTypeLabels } from '@/types/expense'

const router = useRouter()
const formRef = ref<FormInstance>()
const saving = ref(false)
const submitting = ref(false)

const typeOptions = ExpenseTypeLabels

const formData = reactive<{
  title: string
  expense_type: string
  description: string
  items: ExpenseItemCreate[]
}>({
  title: '',
  expense_type: '',
  description: '',
  items: []
})

const rules: FormRules = {
  title: [
    { required: true, message: '请输入报销标题', trigger: 'blur' },
    { min: 2, max: 100, message: '标题长度在2-100个字符', trigger: 'blur' }
  ],
  expense_type: [
    { required: true, message: '请选择报销类型', trigger: 'change' }
  ],
  description: [
    { required: true, message: '请输入报销描述', trigger: 'blur' }
  ]
}

const totalAmount = computed(() => {
  return formData.items.reduce((sum, item) => sum + (item.amount || 0), 0)
})

function addItem() {
  formData.items.push({
    category_id: undefined,
    description: '',
    amount: 0,
    expense_date: new Date().toISOString().split('T')[0],
    invoice_url: undefined
  })
}

function removeItem(index: number) {
  formData.items.splice(index, 1)
}

function handleInvoiceUpload(file: any, index: number) {
  formData.items[index].invoice_url = file.name
}

function resetForm() {
  formData.title = ''
  formData.expense_type = ''
  formData.description = ''
  formData.items = []
}

async function handleSaveDraft() {
  if (!formRef.value) return

  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  if (formData.items.length === 0) {
    ElMessage.warning('请至少添加一条费用明细')
    return
  }

  saving.value = true
  try {
    const payload: ExpenseCreate = {
      title: formData.title,
      expense_type: formData.expense_type,
      description: formData.description,
      items: formData.items
    }
    const res = await createExpense(payload)
    ElMessage.success('报销单已保存为草稿')
    resetForm()
    router.push('/expense/list')
  } catch (error) {
    console.error('Save draft failed:', error)
  } finally {
    saving.value = false
  }
}

async function handleSubmit() {
  if (!formRef.value) return

  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  if (formData.items.length === 0) {
    ElMessage.warning('请至少添加一条费用明细')
    return
  }

  submitting.value = true
  try {
    const payload: ExpenseCreate = {
      title: formData.title,
      expense_type: formData.expense_type,
      description: formData.description,
      items: formData.items
    }
    const res = await createExpense(payload)
    // Submit the created expense
    await submitExpense(res.data.id)
    ElMessage.success('报销单已提交审批')
    resetForm()
    router.push('/expense/list')
  } catch (error) {
    console.error('Submit failed:', error)
  } finally {
    submitting.value = false
  }
}

function handleCancel() {
  router.back()
}
</script>

<style scoped lang="scss">
@import '@/styles/variables.scss';

.expense-form {
  max-width: 1100px;
}

.card-header-title {
  font-weight: 600;
  font-size: $font-size-lg;
}

.empty-items {
  padding: $spacing-xl 0;
}

.total-amount {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  padding: $spacing-md 0 0;
  margin-top: $spacing-md;
  border-top: 1px solid $border-color;

  &__label {
    font-size: $font-size-lg;
    color: $text-secondary;
  }

  &__value {
    font-size: 24px;
    font-weight: 700;
    color: $primary-color;
    margin-left: $spacing-sm;
  }
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: $spacing-sm;
  padding: $spacing-md 0;
}
</style>
