<template>
  <div class="rule-management-page">
    <div class="page-header">
      <h2 class="page-header__title">规则管理</h2>
      <div class="page-header__actions">
        <el-button type="primary" :icon="Plus" @click="handleAdd">新建规则</el-button>
      </div>
    </div>

    <el-card v-loading="loading">
      <el-table :data="ruleList" border stripe style="width: 100%">
        <el-table-column prop="id" label="ID" width="80" align="center" />
        <el-table-column prop="name" label="规则名称" min-width="180" show-overflow-tooltip />
        <el-table-column label="规则类型" width="120">
          <template #default="{ row }">
            <el-tag type="info" size="small">{{ row.rule_type || '通用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="适用类型" width="120">
          <template #default="{ row }">
            {{ getTypeLabel(row.expense_type) }}
          </template>
        </el-table-column>
        <el-table-column label="限额" width="140" align="right">
          <template #default="{ row }">
            ¥{{ (row.max_amount || 0).toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-switch
              v-model="row.is_active"
              :active-value="true"
              :inactive-value="false"
              @change="handleToggle(row)"
            />
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="160">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right" align="center">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button link type="danger" size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <Pagination
        :page="currentPage"
        :page-size="pageSize"
        :total="total"
        @update:page="currentPage = $event"
        @change="fetchData"
      />
    </el-card>

    <!-- Rule Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEditing ? '编辑规则' : '新建规则'"
      width="600px"
      :close-on-click-modal="false"
    >
      <el-form ref="ruleFormRef" :model="ruleForm" :rules="ruleRules" label-width="100px">
        <el-form-item label="规则名称" prop="name">
          <el-input v-model="ruleForm.name" placeholder="请输入规则名称" maxlength="100" />
        </el-form-item>
        <el-form-item label="适用类型" prop="expense_type">
          <el-select v-model="ruleForm.expense_type" placeholder="请选择适用类型" style="width: 100%">
            <el-option
              v-for="(label, value) in typeOptions"
              :key="value"
              :label="label"
              :value="value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="金额上限" prop="max_amount">
          <el-input-number v-model="ruleForm.max_amount" :min="0" :precision="2" style="width: 100%" />
        </el-form-item>
        <el-form-item label="规则描述" prop="description">
          <el-input
            v-model="ruleForm.description"
            type="textarea"
            :rows="3"
            placeholder="请输入规则描述"
            maxlength="500"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { get, post, put, del } from '@/utils/request'
import Pagination from '@/components/common/Pagination.vue'
import { ExpenseTypeLabels } from '@/types/expense'
import { formatDate } from '@/utils/helpers'

interface Rule {
  id: number
  name: string
  rule_type: string
  expense_type: string
  max_amount: number
  description: string
  is_active: boolean
  created_at: string
}

const ruleList = ref<Rule[]>([])
const total = ref(0)
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(10)
const saving = ref(false)

const typeOptions = ExpenseTypeLabels

const dialogVisible = ref(false)
const isEditing = ref(false)
const editingId = ref<number | null>(null)
const ruleFormRef = ref<FormInstance>()

const ruleForm = reactive({
  name: '',
  expense_type: '',
  max_amount: 0,
  description: ''
})

const ruleRules: FormRules = {
  name: [
    { required: true, message: '请输入规则名称', trigger: 'blur' },
    { min: 2, max: 100, message: '名称长度2-100个字符', trigger: 'blur' }
  ],
  expense_type: [
    { required: true, message: '请选择适用类型', trigger: 'change' }
  ],
  max_amount: [
    { required: true, message: '请输入金额上限', trigger: 'blur' }
  ]
}

function getTypeLabel(type: string): string {
  return ExpenseTypeLabels[type] || type || '全部'
}

async function fetchData() {
  loading.value = true
  try {
    const res = await get<{ data: { items: Rule[]; total: number } }>('/rules', {
      page: currentPage.value,
      page_size: pageSize.value
    })
    ruleList.value = res.data.items
    total.value = res.data.total
  } catch (error) {
    console.error('Fetch rules error:', error)
  } finally {
    loading.value = false
  }
}

function resetForm() {
  ruleForm.name = ''
  ruleForm.expense_type = ''
  ruleForm.max_amount = 0
  ruleForm.description = ''
  isEditing.value = false
  editingId.value = null
  ruleFormRef.value?.resetFields()
}

function handleAdd() {
  resetForm()
  dialogVisible.value = true
}

function handleEdit(row: Rule) {
  resetForm()
  isEditing.value = true
  editingId.value = row.id
  ruleForm.name = row.name
  ruleForm.expense_type = row.expense_type
  ruleForm.max_amount = row.max_amount
  ruleForm.description = row.description
  dialogVisible.value = true
}

async function handleSave() {
  if (!ruleFormRef.value) return
  const valid = await ruleFormRef.value.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    if (isEditing.value && editingId.value) {
      await put(`/rules/${editingId.value}`, ruleForm)
      ElMessage.success('规则已更新')
    } else {
      await post('/rules', ruleForm)
      ElMessage.success('规则已创建')
    }
    dialogVisible.value = false
    fetchData()
  } catch (error) {
    console.error('Save rule error:', error)
  } finally {
    saving.value = false
  }
}

async function handleToggle(row: Rule) {
  try {
    await put(`/rules/${row.id}`, { is_active: row.is_active })
    ElMessage.success(row.is_active ? '规则已启用' : '规则已停用')
  } catch (error) {
    row.is_active = !row.is_active
    console.error('Toggle rule error:', error)
  }
}

async function handleDelete(row: Rule) {
  try {
    await ElMessageBox.confirm(`确认删除规则"${row.name}"？此操作不可撤销。`, '确认删除', {
      confirmButtonText: '确认删除',
      cancelButtonText: '取消',
      type: 'error'
    })
    await del(`/rules/${row.id}`)
    ElMessage.success('规则已删除')
    fetchData()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('Delete rule error:', error)
    }
  }
}

fetchData()
</script>
