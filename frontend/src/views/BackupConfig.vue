<template>
  <div>
    <div class="page-heading">
      <div>
        <h2 class="page-title">备份配置</h2>
        <p class="page-desc">配置备份目标、定时任务，查看备份执行历史</p>
      </div>
      <el-button type="primary" :loading="running" @click="handleRunBackup">
        <el-icon style="margin-right: 6px"><FolderChecked /></el-icon>立即备份
      </el-button>
    </div>

    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-width="120px"
      class="backup-form"
      v-loading="loading"
    >
      <el-card shadow="never" class="config-card">
        <template #header>
          <div class="card-header">
            <span>备份目标</span>
            <el-tag type="primary">{{ methodText(form.method) }}</el-tag>
          </div>
        </template>

        <el-form-item label="备份方式" prop="method">
          <el-radio-group v-model="form.method">
            <el-radio-button label="local">本地文件</el-radio-button>
            <el-radio-button label="object_storage">对象存储</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <el-form-item v-if="form.method === 'local'" label="本地路径" prop="local_path">
          <el-input v-model="form.local_path" placeholder="./backups" clearable />
        </el-form-item>

        <template v-else>
          <el-form-item label="Endpoint" prop="endpoint_url">
            <el-input v-model="form.endpoint_url" placeholder="https://obs.example.com" clearable />
          </el-form-item>
          <el-form-item label="AK" prop="access_key">
            <el-input v-model="form.access_key" placeholder="Access Key" clearable />
          </el-form-item>
          <el-form-item label="SK" prop="secret_key">
            <el-input
              v-model="form.secret_key"
              type="password"
              show-password
              :placeholder="secretConfigured ? '已配置，留空沿用原值' : 'Secret Key'"
              clearable
            />
          </el-form-item>
          <el-form-item label="Bucket" prop="bucket">
            <el-input v-model="form.bucket" placeholder="hcs-lld-backup" clearable />
          </el-form-item>
          <el-form-item label="对象前缀">
            <el-input v-model="form.object_prefix" placeholder="hcs-lld" clearable />
          </el-form-item>
        </template>
      </el-card>

      <el-card shadow="never" class="config-card">
        <template #header>
          <div class="card-header">
            <span>定时任务</span>
            <el-tag :type="form.enabled ? 'success' : 'info'">{{ form.enabled ? '已开启' : '未开启' }}</el-tag>
          </div>
        </template>

        <el-form-item label="启用任务">
          <el-switch v-model="form.enabled" active-text="开启" inactive-text="关闭" />
        </el-form-item>

        <el-form-item label="备份周期" prop="frequency">
          <el-segmented v-model="form.frequency" :options="frequencyOptions" />
        </el-form-item>

        <el-form-item v-if="form.frequency === 'weekly'" label="备份星期" prop="schedule_weekday">
          <el-select v-model="form.schedule_weekday" placeholder="请选择星期" style="width: 180px">
            <el-option v-for="item in weekdayOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>

        <el-form-item label="备份时间" required>
          <div class="time-row">
            <el-form-item prop="schedule_hour" class="inline-form-item">
              <el-select v-model="form.schedule_hour" placeholder="时" style="width: 120px">
                <el-option v-for="hour in hourOptions" :key="hour" :label="`${pad2(hour)} 时`" :value="hour" />
              </el-select>
            </el-form-item>
            <span class="time-separator">:</span>
            <el-form-item prop="schedule_minute" class="inline-form-item">
              <el-select v-model="form.schedule_minute" placeholder="分" style="width: 120px">
                <el-option v-for="minute in minuteOptions" :key="minute" :label="`${pad2(minute)} 分`" :value="minute" />
              </el-select>
            </el-form-item>
          </div>
        </el-form-item>

        <el-form-item label="上次执行">
          <span class="readonly-text">{{ formatDate(config?.last_run_at) }}</span>
        </el-form-item>
        <el-form-item label="下次执行">
          <span class="readonly-text">{{ form.enabled ? formatDate(config?.next_run_at) : '未启用' }}</span>
        </el-form-item>
      </el-card>

      <div class="form-actions">
        <el-button type="primary" :loading="saving" @click="handleSave">
          <el-icon style="margin-right: 6px"><Check /></el-icon>保存配置
        </el-button>
        <el-button @click="loadConfig">刷新</el-button>
      </div>
    </el-form>

    <el-card shadow="never" class="history-card">
      <template #header>
        <div class="card-header">
          <span>备份历史</span>
          <el-button :icon="Refresh" text @click="loadRecords" />
        </div>
      </template>

      <el-table :data="records" stripe v-loading="recordsLoading">
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'success' ? 'success' : row.status === 'failed' ? 'danger' : 'warning'">
              {{ statusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="method" label="方式" width="120">
          <template #default="{ row }">{{ methodText(row.method) }}</template>
        </el-table-column>
        <el-table-column prop="target" label="目标" min-width="260" show-overflow-tooltip />
        <el-table-column prop="file_size" label="大小" width="120">
          <template #default="{ row }">{{ formatSize(row.file_size) }}</template>
        </el-table-column>
        <el-table-column prop="operator" label="操作者" width="130" />
        <el-table-column prop="started_at" label="开始时间" width="180">
          <template #default="{ row }">{{ formatDate(row.started_at) }}</template>
        </el-table-column>
        <el-table-column prop="error_message" label="错误" min-width="200" show-overflow-tooltip />
      </el-table>

      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="loadRecords"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { fetchBackupConfig, fetchBackupRecords, runBackup, updateBackupConfig } from '@/api/backup'
import { Check, FolderChecked, Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { computed, onMounted, reactive, ref } from 'vue'

const loading = ref(false)
const saving = ref(false)
const running = ref(false)
const recordsLoading = ref(false)
const config = ref(null)
const secretConfigured = ref(false)
const formRef = ref(null)
const records = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(10)

const form = reactive({
  enabled: false,
  frequency: 'daily',
  schedule_hour: 2,
  schedule_minute: 0,
  schedule_weekday: 1,
  method: 'local',
  local_path: './backups',
  endpoint_url: '',
  access_key: '',
  secret_key: '',
  bucket: '',
  object_prefix: '',
})

const frequencyOptions = [
  { label: '每天', value: 'daily' },
  { label: '每周', value: 'weekly' },
]

const weekdayOptions = [
  { label: '周一', value: 1 },
  { label: '周二', value: 2 },
  { label: '周三', value: 3 },
  { label: '周四', value: 4 },
  { label: '周五', value: 5 },
  { label: '周六', value: 6 },
  { label: '周日', value: 7 },
]

const hourOptions = Array.from({ length: 24 }, (_, index) => index)
const minuteOptions = Array.from({ length: 60 }, (_, index) => index)

const rules = computed(() => ({
  frequency: [{ required: true, message: '请选择备份周期', trigger: 'change' }],
  schedule_hour: [{ required: true, message: '请选择小时', trigger: 'change' }],
  schedule_minute: [{ required: true, message: '请选择分钟', trigger: 'change' }],
  schedule_weekday: form.frequency === 'weekly' ? [{ required: true, message: '请选择星期', trigger: 'change' }] : [],
  method: [{ required: true, message: '请选择备份方式', trigger: 'change' }],
  local_path: form.method === 'local' ? [{ required: true, message: '请输入本地路径', trigger: 'blur' }] : [],
  endpoint_url: form.method === 'object_storage' ? [{ required: true, message: '请输入 Endpoint', trigger: 'blur' }] : [],
  access_key: form.method === 'object_storage' ? [{ required: true, message: '请输入 AK', trigger: 'blur' }] : [],
  secret_key: form.method === 'object_storage' && !secretConfigured.value
    ? [{ required: true, message: '请输入 SK', trigger: 'blur' }]
    : [],
  bucket: form.method === 'object_storage' ? [{ required: true, message: '请输入 Bucket', trigger: 'blur' }] : [],
}))

function applyConfig(data) {
  config.value = data
  secretConfigured.value = data.secret_key_configured
  form.enabled = data.enabled
  form.frequency = data.frequency
  form.schedule_hour = data.schedule_hour ?? 2
  form.schedule_minute = data.schedule_minute ?? 0
  form.schedule_weekday = data.schedule_weekday || 1
  form.method = data.method
  form.local_path = data.local_path || './backups'
  form.endpoint_url = data.endpoint_url || ''
  form.access_key = data.access_key || ''
  form.secret_key = ''
  form.bucket = data.bucket || ''
  form.object_prefix = data.object_prefix || ''
}

async function loadConfig() {
  loading.value = true
  try {
    applyConfig(await fetchBackupConfig())
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  await formRef.value?.validate()
  saving.value = true
  try {
    const payload = { ...form }
    if (payload.frequency === 'daily') {
      payload.schedule_weekday = null
    }
    if (payload.method === 'local') {
      payload.endpoint_url = ''
      payload.access_key = ''
      payload.secret_key = ''
      payload.bucket = ''
      payload.object_prefix = ''
    }
    applyConfig(await updateBackupConfig(payload))
    ElMessage.success('备份配置已保存')
  } finally {
    saving.value = false
  }
}

async function handleRunBackup() {
  running.value = true
  try {
    const result = await runBackup()
    if (result.status === 'success') {
      ElMessage.success('备份完成')
    } else {
      ElMessage.warning('备份未成功，请查看历史记录')
    }
    await Promise.all([loadConfig(), loadRecords()])
  } finally {
    running.value = false
  }
}

async function loadRecords() {
  recordsLoading.value = true
  try {
    const res = await fetchBackupRecords({
      skip: (currentPage.value - 1) * pageSize.value,
      limit: pageSize.value,
    })
    records.value = res.items || []
    total.value = res.total || 0
  } finally {
    recordsLoading.value = false
  }
}

function formatDate(value) {
  if (!value) return '-'
  return new Date(value).toLocaleString('zh-CN', { hour12: false })
}

function pad2(value) {
  return String(value).padStart(2, '0')
}

function formatSize(value) {
  if (!value) return '-'
  if (value < 1024) return `${value} B`
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`
  return `${(value / 1024 / 1024).toFixed(1)} MB`
}

function methodText(value) {
  return value === 'object_storage' ? '对象存储' : '本地文件'
}

function statusText(value) {
  if (value === 'success') return '成功'
  if (value === 'failed') return '失败'
  return '执行中'
}

onMounted(async () => {
  await Promise.all([loadConfig(), loadRecords()])
})
</script>

<style scoped>
.page-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-lg);
}

.page-title {
  font-size: var(--font-size-xl);
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0;
}

.page-desc {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
  margin-top: 4px;
}

.config-card,
.history-card {
  margin-bottom: var(--spacing-lg);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
}

.backup-form {
  width: 100%;
}

.readonly-text {
  color: var(--color-text-secondary);
}

.time-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.inline-form-item {
  margin-bottom: 0;
}

.time-separator {
  line-height: 32px;
  color: var(--color-text-tertiary);
  font-weight: 600;
}

.form-actions {
  display: flex;
  gap: var(--spacing-sm);
  margin: 0 0 var(--spacing-lg) 120px;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: var(--spacing-md);
}
</style>
