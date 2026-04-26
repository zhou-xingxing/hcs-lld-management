<template>
  <div v-loading="loading">
    <el-button size="small" @click="$router.push('/regions')" style="margin-bottom: 16px">← 返回区域列表</el-button>

    <el-card shadow="never" class="region-info">
      <template #header>
        <div class="card-header">
          <span>{{ region.name }}</span>
          <div>
            <el-button size="small" type="warning" plain @click="editRegion">编辑</el-button>
            <el-button size="small" type="danger" plain @click="deleteRegion">删除</el-button>
          </div>
        </div>
      </template>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="描述">{{ region.description || '无' }}</el-descriptions-item>
        <el-descriptions-item label="区域ID">{{ region.id }}</el-descriptions-item>
        <el-descriptions-item label="网络平面数">{{ region.plane_count }}</el-descriptions-item>
        <el-descriptions-item label="IP分配数">{{ region.allocation_count }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ region.created_at }}</el-descriptions-item>
        <el-descriptions-item label="更新时间">{{ region.updated_at }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <el-card shadow="never" class="section-card">
      <template #header>
        <div class="card-header">
          <span>已启用的网络平面</span>
          <div style="display: flex; gap: 8px">
            <el-select v-model="newPlaneTypeId" placeholder="选择网络平面类型" size="small" style="width: 180px">
              <el-option
                v-for="pt in availablePlaneTypes"
                :key="pt.id"
                :label="pt.name"
                :value="pt.id"
              />
            </el-select>
            <el-button size="small" type="primary" @click="enablePlane" :disabled="!newPlaneTypeId">启用</el-button>
          </div>
        </div>
      </template>
      <div v-if="region.planes && region.planes.length > 0">
        <el-tag
          v-for="plane in region.planes"
          :key="plane.id"
          closable
          style="margin: 4px"
          @close="disablePlane(plane.id)"
        >
          {{ plane.plane_type_name }}
        </el-tag>
      </div>
      <el-empty v-else description="尚未启用任何网络平面" />
    </el-card>

    <el-card shadow="never" class="section-card">
      <template #header>
        <div class="card-header">
          <span>IP 地址分配</span>
          <div style="display: flex; gap: 8px">
            <el-select v-model="filterPlaneTypeId" placeholder="全部网络平面" size="small" style="width: 180px" clearable @change="fetchAllocations">
              <el-option
                v-for="plane in region.planes || []"
                :key="plane.id"
                :label="plane.plane_type_name"
                :value="plane.plane_type_id"
              />
            </el-select>
            <el-button size="small" type="primary" @click="showCreateAllocation">添加分配</el-button>
          </div>
        </div>
      </template>
      <el-table :data="allocations" stripe v-loading="allocationLoading" empty-text="暂无IP分配">
        <el-table-column prop="ip_range" label="IP地址段(CIDR)" width="160" />
        <el-table-column prop="plane_type_name" label="网络平面" width="120" />
        <el-table-column prop="vlan_id" label="VLAN ID" width="90" />
        <el-table-column prop="gateway" label="网关" width="140" />
        <el-table-column prop="subnet_mask" label="子网掩码" width="140" />
        <el-table-column prop="purpose" label="用途" min-width="160" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="statusTag(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="warning" link @click="showEditAllocation(row)">编辑</el-button>
            <el-popconfirm title="确定删除此IP分配？" @confirm="handleDeleteAllocation(row.id)">
              <template #reference>
                <el-button size="small" type="danger" link>删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination
        v-if="allocationTotal > 0"
        v-model:current-page="allocationPage"
        :page-size="allocationPageSize"
        :total="allocationTotal"
        layout="total, prev, pager, next"
        style="margin-top: 16px; justify-content: flex-end"
        @current-change="fetchAllocations"
      />
    </el-card>

    <el-dialog v-model="allocDialogVisible" :title="isEditAlloc ? '编辑IP分配' : '添加IP分配'" width="550px">
      <el-form ref="allocFormRef" :model="allocForm" :rules="allocRules" label-width="120px">
        <el-form-item label="网络平面" prop="plane_type_id">
          <el-select v-model="allocForm.plane_type_id" style="width: 100%" :disabled="isEditAlloc">
            <el-option v-for="plane in region.planes || []" :key="plane.id" :label="plane.plane_type_name" :value="plane.plane_type_id" />
          </el-select>
        </el-form-item>
        <el-form-item label="IP地址段" prop="ip_range">
          <el-input v-model="allocForm.ip_range" placeholder="例如: 10.0.0.0/24" />
        </el-form-item>
        <el-form-item label="VLAN ID" prop="vlan_id">
          <el-input-number v-model="allocForm.vlan_id" :min="1" :max="4094" :step="1" style="width: 100%" />
        </el-form-item>
        <el-form-item label="网关" prop="gateway">
          <el-input v-model="allocForm.gateway" placeholder="例如: 10.0.0.1" />
        </el-form-item>
        <el-form-item label="子网掩码" prop="subnet_mask">
          <el-input v-model="allocForm.subnet_mask" placeholder="例如: 255.255.255.0" />
        </el-form-item>
        <el-form-item label="用途" prop="purpose">
          <el-input v-model="allocForm.purpose" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-select v-model="allocForm.status" style="width: 100%">
            <el-option label="已使用" value="active" />
            <el-option label="已预留" value="reserved" />
            <el-option label="已废弃" value="deprecated" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="allocDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleAllocSubmit" :loading="allocSubmitting">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  getRegion, fetchRegionPlanes, enableRegionPlane, disableRegionPlane,
  fetchRegionAllocations, createAllocation, updateAllocation, deleteAllocation
} from '@/api/regions'
import { fetchPlaneTypes } from '@/api/networkPlaneTypes'
import { ElMessage, ElMessageBox } from 'element-plus'

const props = defineProps({ id: String })
const router = useRouter()

const loading = ref(false)
const region = ref({ name: '', planes: [] })
const allocations = ref([])
const allocationTotal = ref(0)
const allocationLoading = ref(false)
const allocationPage = ref(1)
const allocationPageSize = ref(20)

const newPlaneTypeId = ref('')
const filterPlaneTypeId = ref('')
const availablePlaneTypes = ref([])

const allocDialogVisible = ref(false)
const isEditAlloc = ref(false)
const editAllocId = ref(null)
const allocSubmitting = ref(false)
const allocFormRef = ref(null)
const allocForm = ref({
  plane_type_id: '', ip_range: '', vlan_id: null, gateway: '',
  subnet_mask: '', purpose: '', status: 'active',
})

const allocRules = {
  plane_type_id: [{ required: true, message: '请选择网络平面', trigger: 'change' }],
  ip_range: [{ required: true, message: '请输入IP地址段', trigger: 'blur' }],
}

function statusTag(status) {
  const map = { active: 'success', reserved: 'warning', deprecated: 'info' }
  return map[status] || 'info'
}
function statusLabel(status) {
  const map = { active: '已使用', reserved: '已预留', deprecated: '已废弃' }
  return map[status] || status
}

async function fetchRegion() {
  region.value = await getRegion(props.id)
}

async function fetchPlanes() {
  const res = await fetchPlaneTypes({ skip: 0, limit: 500 })
  availablePlaneTypes.value = (res.items || []).filter(
    pt => !(region.value.planes || []).some(p => p.plane_type_id === pt.id)
  )
}

async function fetchAllocations() {
  allocationLoading.value = true
  try {
    const params = {
      skip: (allocationPage.value - 1) * allocationPageSize.value,
      limit: allocationPageSize.value,
    }
    if (filterPlaneTypeId.value) {
      params.plane_type_id = filterPlaneTypeId.value
    }
    const res = await fetchRegionAllocations(props.id, params)
    allocations.value = res.items
    allocationTotal.value = res.total
  } finally {
    allocationLoading.value = false
  }
}

async function enablePlane() {
  if (!newPlaneTypeId.value) return
  try {
    await enableRegionPlane(props.id, newPlaneTypeId.value)
    ElMessage.success('网络平面已启用')
    newPlaneTypeId.value = ''
    await fetchRegion()
    await fetchPlanes()
  } catch (e) { /* handled by interceptor */ }
}

async function disablePlane(planeId) {
  try {
    await ElMessageBox.confirm('确定禁用该网络平面？相关的IP分配数据不会被删除', '确认')
    await disableRegionPlane(props.id, planeId)
    ElMessage.success('网络平面已禁用')
    await fetchRegion()
    await fetchPlanes()
  } catch (e) {
    if (e !== 'cancel') throw e
  }
}

function showCreateAllocation() {
  isEditAlloc.value = false
  editAllocId.value = null
  allocForm.value = { plane_type_id: '', ip_range: '', vlan_id: null, gateway: '', subnet_mask: '', purpose: '', status: 'active' }
  allocDialogVisible.value = true
}

function showEditAllocation(row) {
  isEditAlloc.value = true
  editAllocId.value = row.id
  allocForm.value = {
    plane_type_id: row.plane_type_id,
    ip_range: row.ip_range,
    vlan_id: row.vlan_id,
    gateway: row.gateway || '',
    subnet_mask: row.subnet_mask || '',
    purpose: row.purpose || '',
    status: row.status,
  }
  allocDialogVisible.value = true
}

async function handleAllocSubmit() {
  const valid = await allocFormRef.value.validate().catch(() => false)
  if (!valid) return
  allocSubmitting.value = true
  try {
    const data = {
      plane_type_id: allocForm.value.plane_type_id,
      ip_range: allocForm.value.ip_range,
      vlan_id: allocForm.value.vlan_id || null,
      gateway: allocForm.value.gateway || null,
      subnet_mask: allocForm.value.subnet_mask || null,
      purpose: allocForm.value.purpose || '',
      status: allocForm.value.status,
    }
    if (isEditAlloc.value) {
      await updateAllocation(editAllocId.value, data)
      ElMessage.success('更新成功')
    } else {
      await createAllocation(props.id, data)
      ElMessage.success('创建成功')
    }
    allocDialogVisible.value = false
    await fetchAllocations()
    await fetchRegion()
  } finally {
    allocSubmitting.value = false
  }
}

async function handleDeleteAllocation(id) {
  try {
    await deleteAllocation(id)
    ElMessage.success('删除成功')
    await fetchAllocations()
    await fetchRegion()
  } catch (e) { /* handled */ }
}

function editRegion() {
  ElMessageBox.prompt('区域名称', '编辑区域', { inputValue: region.value.name, inputPattern: /.+/, inputErrorMessage: '名称不能为空' })
    .then(async ({ value }) => {
      const { updateRegion: updateRegionApi } = await import('@/api/regions')
      await updateRegionApi(props.id, { name: value })
      ElMessage.success('更新成功')
      await fetchRegion()
    }).catch(() => {})
}

async function deleteRegion() {
  try {
    await ElMessageBox.confirm('确定删除该区域？所有相关数据将被删除', '警告', { type: 'warning' })
    const { deleteRegion: deleteRegionApi } = await import('@/api/regions')
    await deleteRegionApi(props.id)
    ElMessage.success('删除成功')
    router.push('/regions')
  } catch (e) {
    if (e !== 'cancel') throw e
  }
}

onMounted(async () => {
  loading.value = true
  try {
    await fetchRegion()
    await fetchPlanes()
    await fetchAllocations()
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.region-info { margin-bottom: 16px; }
.section-card { margin-bottom: 16px; }
.card-header { display: flex; align-items: center; justify-content: space-between; }
</style>
