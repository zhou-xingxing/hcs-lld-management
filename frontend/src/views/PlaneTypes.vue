<template>
  <div>
    <div class="page-header">
      <h2 class="page-title">网络平面类型</h2>
      <el-button type="primary" @click="showCreateDialog">添加类型</el-button>
    </div>

    <el-card shadow="never">
      <el-table :data="items" stripe v-loading="loading" empty-text="暂无网络平面类型">
        <el-table-column prop="name" label="类型名称" min-width="160" />
        <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
        <el-table-column prop="region_count" label="使用区域数" width="120" align="center" />
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="warning" link @click="showEditDialog(row)">编辑</el-button>
            <el-popconfirm title="确定删除？如果该类型已被区域使用则无法删除" @confirm="handleDelete(row.id)">
              <template #reference>
                <el-button size="small" type="danger" link :disabled="row.region_count > 0">删除</el-button>
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

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑类型' : '添加类型'" width="500px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="类型名称" prop="name">
          <el-input v-model="form.name" placeholder="例如: 管理平面" maxlength="100" />
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
import { fetchPlaneTypes, createPlaneType, updatePlaneType, deletePlaneType } from '@/api/networkPlaneTypes'
import { ElMessage } from 'element-plus'

const loading = ref(false)
const items = ref([])
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
  name: [{ required: true, message: '请输入类型名称', trigger: 'blur' }],
}

async function fetchData() {
  loading.value = true
  try {
    const res = await fetchPlaneTypes({ skip: (page.value - 1) * pageSize.value, limit: pageSize.value })
    items.value = res.items
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

async function handleSubmit() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    if (isEdit.value) {
      await updatePlaneType(editId.value, form.value)
      ElMessage.success('更新成功')
    } else {
      await createPlaneType(form.value)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    await fetchData()
  } finally {
    submitting.value = false
  }
}

async function handleDelete(id) {
  try {
    await deletePlaneType(id)
    ElMessage.success('删除成功')
    await fetchData()
  } catch (e) {
    // Error handled by Axios interceptor
  }
}

onMounted(fetchData)
</script>

<style scoped>
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.page-title { font-size: 20px; color: #303133; margin: 0; }
</style>
