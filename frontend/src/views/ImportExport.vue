<template>
  <div>
    <h2 class="page-title">导入 / 导出</h2>
    <el-card shadow="never">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="导入 Excel" name="import">
          <div class="import-section">
            <p class="section-desc">请先下载模板，按照模板格式填写数据后上传。</p>
            <el-button type="primary" plain @click="downloadTemplate" :loading="downloading">下载模板</el-button>
          </div>

          <el-divider />

          <div class="import-section">
            <h4>上传文件</h4>
            <el-upload
              ref="uploadRef"
              action="#"
              :auto-upload="false"
              :show-file-list="true"
              :limit="1"
              accept=".xlsx,.xls"
              :on-change="onFileChange"
            >
              <template #trigger>
                <el-button type="primary">选择文件</el-button>
              </template>
              <el-button style="margin-left: 10px" type="success" @click="previewUpload" :loading="previewLoading" :disabled="!selectedFile">预览</el-button>
              <template #tip><div class="el-upload__tip">仅支持 .xlsx / .xls 文件</div></template>
            </el-upload>
          </div>

          <div v-if="previewData" class="preview-section">
            <el-alert
              :title="`共 ${previewData.total_rows} 行，有效 ${previewData.valid_rows} 行，错误 ${previewData.error_rows.length} 行`"
              :type="previewData.error_rows.length > 0 ? 'warning' : 'success'"
              show-icon
              style="margin-bottom: 16px"
            />
            <div v-if="previewData.error_rows.length > 0">
              <h4>错误详情：</h4>
              <el-table :data="previewData.error_rows" stripe size="small">
                <el-table-column prop="row" label="行号" width="80" />
                <el-table-column prop="errors" label="错误" min-width="300">
                  <template #default="{ row }">
                    <el-tag v-for="err in row.errors" :key="err" type="danger" size="small" style="margin: 2px">{{ err }}</el-tag>
                  </template>
                </el-table-column>
              </el-table>
              <el-divider />
            </div>
            <h4>数据预览（仅显示有效行）：</h4>
            <div style="max-height: 400px; overflow-y: auto">
              <el-table :data="previewData.rows" stripe size="small">
                <el-table-column prop="row_number" label="行" width="50" />
                <el-table-column prop="region_name" label="区域" width="120" />
                <el-table-column prop="plane_type_name" label="网络平面" width="120" />
                <el-table-column prop="ip_range" label="IP段" width="140" />
                <el-table-column prop="vlan_id" label="VLAN" width="80" />
                <el-table-column prop="status" label="状态" width="80" />
              </el-table>
            </div>
            <el-button type="success" style="margin-top: 16px" @click="confirmImport" :loading="importing" :disabled="previewData.valid_rows === 0">
              确认导入 ({{ previewData.valid_rows }} 条)
            </el-button>
          </div>

          <el-result v-if="importResult" icon="success" :title="`导入完成`" :sub-title="`成功 ${importResult.imported_count} 条，失败 ${importResult.error_count} 条`">
            <template #extra>
              <el-button type="primary" @click="resetImport">继续导入</el-button>
            </template>
          </el-result>
        </el-tab-pane>

        <el-tab-pane label="导出 Excel" name="export">
          <div class="export-section">
            <el-form :model="exportForm" label-width="120px">
              <el-form-item label="区域">
                <el-select v-model="exportForm.region_id" placeholder="全部区域" clearable style="width: 300px">
                  <el-option v-for="r in regions" :key="r.id" :label="r.name" :value="r.id" />
                </el-select>
              </el-form-item>
              <el-form-item label="网络平面">
                <el-select v-model="exportForm.plane_type_id" placeholder="全部平面" clearable style="width: 300px">
                  <el-option v-for="pt in planeTypes" :key="pt.id" :label="pt.name" :value="pt.id" />
                </el-select>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" @click="handleExport" :loading="exporting">导出</el-button>
              </el-form-item>
            </el-form>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { downloadTemplate as downloadTemplateApi, previewImport, confirmImport as confirmImportApi, exportExcel } from '@/api/excel'
import { fetchRegions } from '@/api/regions'
import { fetchPlaneTypes } from '@/api/networkPlaneTypes'
import { ElMessage } from 'element-plus'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()
const activeTab = ref('import')

const downloading = ref(false)
const selectedFile = ref(null)
const previewLoading = ref(false)
const previewData = ref(null)
const importing = ref(false)
const importResult = ref(null)
const uploadRef = ref(null)

const regions = ref([])
const planeTypes = ref([])
const exporting = ref(false)
const exportForm = ref({ region_id: '', plane_type_id: '' })

async function downloadTemplate() {
  downloading.value = true
  try {
    const blob = await downloadTemplateApi()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'hcs_lld_import_template.xlsx'
    a.click()
    URL.revokeObjectURL(url)
  } finally {
    downloading.value = false
  }
}

function onFileChange(uploadFile) {
  selectedFile.value = uploadFile.raw
  previewData.value = null
  importResult.value = null
}

async function previewUpload() {
  if (!selectedFile) return
  previewLoading.value = true
  try {
    previewData.value = await previewImport(selectedFile)
  } finally {
    previewLoading.value = false
  }
}

async function confirmImport() {
  if (!previewData.value) return
  importing.value = true
  try {
    importResult.value = await confirmImportApi(previewData.value.preview_id, appStore.operator)
    if (importResult.value.imported_count === 0 && importResult.value.error_count > 0) {
      ElMessage.warning('所有行导入失败')
    }
  } finally {
    importing.value = false
  }
}

function resetImport() {
  selectedFile.value = null
  previewData.value = null
  importResult.value = null
}

async function handleExport() {
  exporting.value = true
  try {
    const params = {}
    if (exportForm.value.region_id) params.region_id = exportForm.value.region_id
    if (exportForm.value.plane_type_id) params.plane_type_id = exportForm.value.plane_type_id
    const blob = await exportExcel(params)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'hcs_lld_export.xlsx'
    a.click()
    URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } finally {
    exporting.value = false
  }
}

onMounted(async () => {
  const regRes = await fetchRegions({ skip: 0, limit: 500 })
  regions.value = regRes.items || []
  const ptRes = await fetchPlaneTypes({ skip: 0, limit: 500 })
  planeTypes.value = ptRes.items || []
})
</script>

<style scoped>
.page-title { font-size: 20px; margin-bottom: 16px; color: #303133; }
.import-section, .export-section, .preview-section { padding: 8px 0; }
.section-desc { color: #606266; margin-bottom: 12px; }
</style>
