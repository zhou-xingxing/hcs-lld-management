<template>
  <div>
    <div class="page-header">
      <h2 class="page-title">区域管理</h2>
      <el-button type="primary" @click="showCreateDialog">添加区域</el-button>
    </div>

    <el-card shadow="never">
      <el-table :data="regions" stripe v-loading="loading" empty-text="暂无区域">
        <el-table-column prop="name" label="区域名称" min-width="160" />
        <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
        <el-table-column prop="plane_count" label="网络平面数" width="120" align="center" />
        <el-table-column prop="allocation_count" label="IP分配数" width="120" align="center" />
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" link @click="viewRegion(row)">详情</el-button>
            <el-button size="small" type="warning" link @click="showEditDialog(row)">编辑</el-button>
            <el-popconfirm title="确定删除该区域？" @confirm="handleDelete(row.id)">
              <template #reference>
                <el-button size="small" type="danger" link>删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination
        v-if="total > 0"
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        style="margin-top: 16px; justify-content: flex-end"
        @current-change="fetchData"
      />
    </el-card>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑区域' : '添加区域'" width="500px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="区域名称" prop="name">
          <el-input v-model="form.name" placeholder="例如: HCS华北-北京" maxlength="100" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input v-model="form.description" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { fetchRegions, createRegion, updateRegion, deleteRegion } from '@/api/regions'
import { ElMessage } from 'element-plus'

const router = useRouter()
const loading = ref(false)
const regions = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const dialogVisible = ref(false)
const isEdit = ref(false)
const submitting = ref(false)
const editId = ref(null)
const formRef = ref(null)
const form = ref({ name: '', description: '' })

const rules = {
  name: [{ required: true, message: '请输入区域名称', trigger: 'blur' }],
}

async function fetchData() {
  loading.value = true
  try {
    const res = await fetchRegions({ skip: (page.value - 1) * pageSize.value, limit: pageSize.value })
    regions.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

function showCreateDialog() {
  isEdit.value = false
  editId.value = null
  form.value = { name: '', description: '' }
  dialogVisible.value = true
}

function showEditDialog(row) {
  isEdit.value = true
  editId.value = row.id
  form.value = { name: row.name, description: row.description || '' }
  dialogVisible.value = true
}

function viewRegion(row) {
  router.push(`/regions/${row.id}`)
}

async function handleSubmit() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    if (isEdit.value) {
      await updateRegion(editId.value, form.value)
      ElMessage.success('更新成功')
    } else {
      await createRegion(form.value)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    await fetchData()
  } finally {
    submitting.value = false
  }
}

async function handleDelete(id) {
  await deleteRegion(id)
  ElMessage.success('删除成功')
  await fetchData()
}

onMounted(fetchData)
</script>

<style scoped>
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.page-title { font-size: 20px; color: #303133; margin: 0; }
</style>
