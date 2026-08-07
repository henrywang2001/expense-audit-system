<template>
  <div class="rule-management-page">
    <div class="page-header">
      <h2 class="page-header__title">规则管理</h2>
      <div class="page-header__actions">
        <el-button type="primary" :icon="Plus" @click="handleAdd">新建规则</el-button>
      </div>
    </div>

    <!-- Filter bar：后端 list_rules 原生支持 rule_type / is_active / exec_mode 三个过滤参数 -->
    <div class="filter-bar">
      <el-select
        v-model="ruleTypeFilter"
        placeholder="规则类型"
        clearable
        style="width: 160px"
        @change="handleSearch"
      >
        <el-option
          v-for="(label, value) in RuleTypeLabels"
          :key="value"
          :label="label"
          :value="value"
        />
      </el-select>
      <el-select
        v-model="execModeFilter"
        placeholder="求值模式"
        clearable
        style="width: 170px"
        @change="handleSearch"
      >
        <el-option
          v-for="(label, value) in RuleExecModeLabels"
          :key="value"
          :label="label"
          :value="value"
        />
      </el-select>
      <el-select
        v-model="activeFilter"
        placeholder="启用状态"
        clearable
        style="width: 140px"
        @change="handleSearch"
      >
        <el-option label="已启用" :value="true" />
        <el-option label="已停用" :value="false" />
      </el-select>
      <el-button type="primary" :icon="Search" @click="handleSearch">搜索</el-button>
      <el-button :icon="RefreshRight" @click="handleReset">重置</el-button>
    </div>

    <el-card v-loading="loading">
      <el-table :data="ruleList" border stripe style="width: 100%">
        <el-table-column prop="id" label="ID" width="80" align="center" />
        <el-table-column prop="name" label="规则名称" min-width="180" show-overflow-tooltip />
        <el-table-column label="规则类型" width="130">
          <template #default="{ row }">
            <el-tag type="info" size="small">{{ getRuleTypeLabel(row.rule_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="动作" width="120">
          <template #default="{ row }">
            <el-tag :type="getActionColor(row.action)" size="small">
              {{ getActionLabel(row.action) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="求值模式" width="140">
          <template #default="{ row }">
            {{ getExecModeLabel(row.exec_mode) }}
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
        <el-table-column label="操作" width="180" fixed="right" align="center">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button
              link
              type="danger"
              size="small"
              :disabled="!row.is_active"
              @click="handleDeactivate(row)"
            >
              停用
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <Pagination
        :page="currentPage"
        :page-size="pageSize"
        :total="total"
        @update:page="currentPage = $event"
        @update:page-size="pageSize = $event"
        @change="fetchData"
      />
    </el-card>

    <!-- Rule Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEditing ? '编辑规则' : '新建规则'"
      width="720px"
      :close-on-click-modal="false"
    >
      <el-form ref="ruleFormRef" :model="ruleForm" :rules="formRules" label-width="110px">
        <el-form-item label="规则名称" prop="name">
          <el-input v-model="ruleForm.name" placeholder="请输入规则名称" maxlength="100" show-word-limit />
        </el-form-item>

        <el-form-item label="规则类型" prop="rule_type">
          <el-select v-model="ruleForm.rule_type" placeholder="请选择规则类型" style="width: 100%">
            <el-option
              v-for="(label, value) in RuleTypeLabels"
              :key="value"
              :label="label"
              :value="value"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="命中动作" prop="action">
          <el-select v-model="ruleForm.action" placeholder="请选择命中后的动作" style="width: 100%">
            <el-option
              v-for="(label, value) in RuleActionLabels"
              :key="value"
              :label="label"
              :value="value"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="求值模式" prop="exec_mode">
          <el-select v-model="ruleForm.exec_mode" placeholder="请选择求值模式" style="width: 100%">
            <el-option
              v-for="(label, value) in RuleExecModeLabels"
              :key="value"
              :label="label"
              :value="value"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="提示信息" prop="message">
          <el-input
            v-model="ruleForm.message"
            placeholder="命中规则时展示给用户的提示语"
            maxlength="200"
          />
          <div class="form-tip">后端为必填字段；留空将自动填充「{{ defaultMessage }}」。</div>
        </el-form-item>

        <el-form-item label="规则描述" prop="description">
          <el-input
            v-model="ruleForm.description"
            type="textarea"
            :rows="2"
            placeholder="选填，用于说明规则用途"
            maxlength="500"
            show-word-limit
          />
        </el-form-item>

        <el-form-item label="规则逻辑" prop="logicText">
          <el-input
            v-model="ruleForm.logicText"
            type="textarea"
            :rows="8"
            placeholder='JSON Logic 表达式，例如：{">": [{"var": "total_amount"}, 5000]}'
            spellcheck="false"
            class="logic-editor"
          />
          <div class="form-tip">
            <div>
              可用字段：<code>{{ fieldWhitelistText }}</code>
            </div>
            <div class="mt-4">
              <el-button link type="primary" size="small" @click="handleFormatLogic">格式化 JSON</el-button>
              <el-button link type="primary" size="small" @click="handleInsertTemplate">插入示例</el-button>
            </div>
          </div>
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
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Plus, Search, RefreshRight } from '@element-plus/icons-vue'
import Pagination from '@/components/common/Pagination.vue'
import {
  getRuleList,
  createRule,
  updateRule,
  setRuleActive,
  deactivateRule
} from '@/api/rule'
import type {
  Rule,
  RuleAction,
  RuleExecMode,
  RuleCreatePayload,
  RuleUpdatePayload,
  RuleListParams
} from '@/types/rule'
import {
  RuleTypeLabels,
  RuleActionLabels,
  RuleActionColors,
  RuleExecModeLabels,
  RULE_FIELD_WHITELIST,
  RULE_ALLOWED_OPS
} from '@/types/rule'

/** JSON Logic 示例，用作"插入示例"按钮的内容 */
const LOGIC_TEMPLATE = JSON.stringify({ '>': [{ var: 'total_amount' }, 5000] }, null, 2)

const ALLOWED_OPS_SET = new Set<string>(RULE_ALLOWED_OPS as readonly string[])
const FIELD_WHITELIST_SET = new Set<string>(RULE_FIELD_WHITELIST as readonly string[])

const ruleList = ref<Rule[]>([])
const total = ref(0)
const loading = ref(false)
const saving = ref(false)
const currentPage = ref(1)
const pageSize = ref(10)

const ruleTypeFilter = ref<string>('')
const execModeFilter = ref<string>('')
// clearable 的 el-select 清空后会写回 undefined，故类型必须容纳 undefined
const activeFilter = ref<boolean | undefined>(undefined)

const dialogVisible = ref(false)
const isEditing = ref(false)
const editingId = ref<number | null>(null)
const ruleFormRef = ref<FormInstance>()

/**
 * 编辑时进入弹窗那一刻的 logic 文本快照。
 * 存量数据的 logic 可能是 `{}`（后端拒绝写回空对象），
 * 只要用户没有改动它，保存时就把 logic 整个字段省略掉 —— 后端会跳过 logic 校验。
 */
const originalLogicText = ref('')

const ruleForm = reactive<{
  name: string
  rule_type: string
  action: RuleAction
  exec_mode: RuleExecMode
  message: string
  description: string
  logicText: string
}>({
  name: '',
  rule_type: '',
  action: 'warn',
  exec_mode: 'deterministic',
  message: '',
  description: '',
  logicText: LOGIC_TEMPLATE
})

const defaultMessage = computed(() => `${ruleForm.name || '该规则'}不符合规则`)

const fieldWhitelistText = computed(() => RULE_FIELD_WHITELIST.join('、'))

// ========== 字典展示 ==========

function getRuleTypeLabel(type: string): string {
  return RuleTypeLabels[type] || type || '-'
}

function getActionLabel(action: string): string {
  return RuleActionLabels[action] || action || '-'
}

function getActionColor(action: string): string {
  return RuleActionColors[action] || 'info'
}

function getExecModeLabel(mode: string): string {
  return RuleExecModeLabels[mode] || mode || '-'
}

// ========== JSON Logic 前端预校验 ==========

/**
 * 递归校验 JSON Logic 节点，命中非法项时返回可读的错误描述，合法时返回 null。
 * 白名单与后端 `rule_engine.ALLOWED_OPS` / `FIELD_WHITELIST` 保持一致，
 * 目的是在提交前把 400/422 拦在本地，并明确告诉用户是哪个操作符 / 字段不合法。
 */
function validateLogicNode(node: unknown, path: string): string | null {
  // 基础类型（数字 / 字符串 / 布尔 / null）在 JSON Logic 中都是合法的字面量
  if (node === null || typeof node !== 'object') return null

  if (Array.isArray(node)) {
    for (let i = 0; i < node.length; i++) {
      const err = validateLogicNode(node[i], `${path}[${i}]`)
      if (err) return err
    }
    return null
  }

  const obj = node as Record<string, unknown>
  const keys = Object.keys(obj)

  for (const key of keys) {
    if (!ALLOWED_OPS_SET.has(key)) {
      return `不支持的操作符 "${key}"（位置：${path || '根节点'}）。允许的操作符：${RULE_ALLOWED_OPS.join(', ')}`
    }

    const value = obj[key]
    const childPath = path ? `${path}.${key}` : key

    // var / missing / missing_some 的参数是字段名而非嵌套表达式，单独按字段白名单校验
    if (key === 'var' || key === 'missing' || key === 'missing_some') {
      const fieldErr = validateFieldRef(value, childPath)
      if (fieldErr) return fieldErr
      continue
    }

    const err = validateLogicNode(value, childPath)
    if (err) return err
  }

  return null
}

/** 校验 var / missing / missing_some 引用的字段是否在白名单内 */
function validateFieldRef(value: unknown, path: string): string | null {
  const names: unknown[] = Array.isArray(value) ? value : [value]

  for (const name of names) {
    // 允许 {"var": ""}（整个数据对象）与非字符串的默认值参数
    if (typeof name !== 'string' || name === '') continue

    // 支持 `items.0.amount` 这类路径，只校验根字段
    const rootField = name.split('.')[0]
    if (!FIELD_WHITELIST_SET.has(rootField)) {
      return `不支持的字段 "${name}"（位置：${path}）。允许的字段：${RULE_FIELD_WHITELIST.join(', ')}`
    }
  }

  return null
}

/** el-form 自定义校验器：JSON 语法 → 非空对象 → 白名单递归检查 */
function validateLogicText(
  _rule: unknown,
  value: string,
  callback: (error?: Error) => void
): void {
  const text = (value || '').trim()

  if (!text) {
    callback(new Error('规则逻辑不能为空，请输入 JSON Logic 表达式'))
    return
  }

  let parsed: unknown
  try {
    parsed = JSON.parse(text)
  } catch (error: any) {
    callback(new Error(`JSON 语法错误：${error?.message || '无法解析，请检查括号与引号是否配对'}`))
    return
  }

  if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)) {
    callback(new Error('规则逻辑必须是一个 JSON 对象，例如 {">": [{"var": "total_amount"}, 5000]}'))
    return
  }

  if (Object.keys(parsed as Record<string, unknown>).length === 0) {
    // 存量规则的 logic 本来就是 {}，只要用户没改动就放行（保存时会省略该字段）
    if (isEditing.value && text === originalLogicText.value) {
      callback()
      return
    }
    callback(new Error('规则逻辑不能为空对象 {}，后端会拒绝。请填写至少一个条件'))
    return
  }

  const err = validateLogicNode(parsed, '')
  if (err) {
    callback(new Error(err))
    return
  }

  callback()
}

const formRules: FormRules = {
  name: [
    { required: true, message: '请输入规则名称', trigger: 'blur' },
    { min: 2, max: 100, message: '名称长度2-100个字符', trigger: 'blur' }
  ],
  rule_type: [{ required: true, message: '请选择规则类型', trigger: 'change' }],
  action: [{ required: true, message: '请选择命中动作', trigger: 'change' }],
  exec_mode: [{ required: true, message: '请选择求值模式', trigger: 'change' }],
  logicText: [{ validator: validateLogicText, trigger: 'blur' }]
}

// ========== 数据加载 ==========

async function fetchData() {
  loading.value = true
  try {
    const params: RuleListParams = {
      page: currentPage.value,
      page_size: pageSize.value
    }
    if (ruleTypeFilter.value) params.rule_type = ruleTypeFilter.value
    if (execModeFilter.value) params.exec_mode = execModeFilter.value
    if (typeof activeFilter.value === 'boolean') params.is_active = activeFilter.value

    // ⚠️ /rules 是【裸响应】{total, items}，没有 success/data 信封，
    //    取值只能是 res.items / res.total。
    const res = await getRuleList(params)
    ruleList.value = res.items || []
    total.value = res.total || 0
  } catch (error) {
    console.error('Fetch rules error:', error)
    ruleList.value = []
    total.value = 0
    ElMessage.error('获取规则列表失败')
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  currentPage.value = 1
  fetchData()
}

function handleReset() {
  ruleTypeFilter.value = ''
  execModeFilter.value = ''
  activeFilter.value = undefined
  currentPage.value = 1
  fetchData()
}

// ========== 表单 ==========

function resetForm() {
  ruleFormRef.value?.clearValidate()
  ruleForm.name = ''
  ruleForm.rule_type = ''
  ruleForm.action = 'warn'
  ruleForm.exec_mode = 'deterministic'
  ruleForm.message = ''
  ruleForm.description = ''
  ruleForm.logicText = LOGIC_TEMPLATE
  originalLogicText.value = ''
  isEditing.value = false
  editingId.value = null
}

function handleAdd() {
  resetForm()
  dialogVisible.value = true
}

function handleEdit(row: Rule) {
  resetForm()
  isEditing.value = true
  editingId.value = row.id
  ruleForm.name = row.name || ''
  ruleForm.rule_type = row.rule_type || ''
  ruleForm.action = row.action || 'warn'
  ruleForm.exec_mode = row.exec_mode || 'deterministic'
  ruleForm.message = row.message || ''
  ruleForm.description = row.description || ''
  // 存量 logic 可能是 {} 或 null，一律安全回显，不抛异常
  ruleForm.logicText = safeStringifyLogic(row.logic)
  originalLogicText.value = ruleForm.logicText
  dialogVisible.value = true
}

function safeStringifyLogic(logic: Record<string, any> | null | undefined): string {
  if (!logic) return '{}'
  try {
    return JSON.stringify(logic, null, 2)
  } catch {
    return '{}'
  }
}

function handleFormatLogic() {
  const text = (ruleForm.logicText || '').trim()
  if (!text) return
  try {
    ruleForm.logicText = JSON.stringify(JSON.parse(text), null, 2)
  } catch (error: any) {
    ElMessage.error(`JSON 语法错误，无法格式化：${error?.message || '请检查内容'}`)
  }
}

function handleInsertTemplate() {
  ruleForm.logicText = LOGIC_TEMPLATE
}

async function handleSave() {
  if (!ruleFormRef.value) return
  const valid = await ruleFormRef.value.validate().catch(() => false)
  if (!valid) return

  const logicText = (ruleForm.logicText || '').trim()
  let parsedLogic: Record<string, any> = {}
  try {
    parsedLogic = JSON.parse(logicText) as Record<string, any>
  } catch {
    ElMessage.error('规则逻辑不是合法的 JSON，请修正后再保存')
    return
  }

  // message 是后端必填字段，留空必然 422，这里补一个与后端一致的默认提示
  const message = ruleForm.message.trim() || `${ruleForm.name}不符合规则`
  const description = ruleForm.description.trim()

  saving.value = true
  try {
    if (isEditing.value && editingId.value !== null) {
      const payload: RuleUpdatePayload = {
        name: ruleForm.name.trim(),
        rule_type: ruleForm.rule_type,
        action: ruleForm.action,
        exec_mode: ruleForm.exec_mode,
        message,
        description
      }
      // 逻辑未改动（含存量空对象场景）就不下发 logic，后端会跳过 logic 校验
      const logicUnchanged = logicText === originalLogicText.value
      const logicIsEmpty = Object.keys(parsedLogic).length === 0
      if (!(logicUnchanged && logicIsEmpty)) {
        payload.logic = parsedLogic
      }
      await updateRule(editingId.value, payload)
      ElMessage.success('规则已更新')
    } else {
      const payload: RuleCreatePayload = {
        name: ruleForm.name.trim(),
        rule_type: ruleForm.rule_type,
        logic: parsedLogic,
        action: ruleForm.action,
        exec_mode: ruleForm.exec_mode,
        message,
        description
      }
      await createRule(payload)
      ElMessage.success('规则已创建')
    }
    dialogVisible.value = false
    await fetchData()
  } catch (error) {
    console.error('Save rule error:', error)
  } finally {
    saving.value = false
  }
}

// ========== 启停 ==========

async function handleToggle(row: Rule) {
  const nextActive = row.is_active
  try {
    // 只提交 is_active，避免带上 logic 触发后端的规则逻辑校验
    await setRuleActive(row.id, nextActive)
    ElMessage.success(nextActive ? '规则已启用' : '规则已停用')
  } catch (error) {
    // 失败时把开关拨回去，保持界面与服务端一致
    row.is_active = !nextActive
    console.error('Toggle rule error:', error)
  }
}

/**
 * 后端 DELETE /rules/{id} 是【软删除】—— 实际只是把 is_active 置为 false，
 * 数据仍然保留，因此这里用"停用"语义，不再宣称"不可撤销"。
 */
async function handleDeactivate(row: Rule) {
  try {
    await ElMessageBox.confirm(
      `确认停用规则"${row.name}"？停用后该规则将不再参与审核，可随时通过状态开关重新启用。`,
      '确认停用',
      {
        confirmButtonText: '确认停用',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    await deactivateRule(row.id)
    ElMessage.success('规则已停用')
    await fetchData()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('Deactivate rule error:', error)
    }
  }
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped lang="scss">
@import '@/styles/variables.scss';

.form-tip {
  width: 100%;
  margin-top: 4px;
  font-size: $font-size-sm;
  color: $text-secondary;
  line-height: 1.6;

  code {
    font-family: 'Courier New', monospace;
    word-break: break-all;
  }
}

.mt-4 {
  margin-top: 4px;
}

.logic-editor :deep(textarea) {
  font-family: 'Courier New', monospace;
  line-height: 1.6;
}
</style>
