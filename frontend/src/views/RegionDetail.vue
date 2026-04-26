<template>
  <div v-loading="loading">
    <div class="page-heading">
      <div>
        <el-button size="small" text @click="$router.push('/regions')" :icon="ArrowLeft" style="margin-bottom: 8px">返回区域列表</el-button>
        <h2 class="page-title">{{ region.name }}</h2>
        <p class="page-desc">区域详情与 IP 分配管理</p>
      </div>
      <div class="header-actions">
        <el-button size="small" plain @click="editRegion">
          <el-icon><Edit /></el-icon>编辑
        </el-button>
        <el-button size="small" plain type="danger" @click="deleteRegion">
          <el-icon><Delete /></el-icon>删除
        </el-button>
      </div>
    </div>

    <!-- Region Info -->
    <el-card shadow="never" class="region-info">
      <template #header>
        <div class="card-header">
          <span class="card-title">基本信息</span>
        </div>
      </template>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="描述" :content-style="desContentStyle">{{ region.description || '无' }}</el-descriptions-item>
        <el-descriptions-item label="区域ID" :content-style="desContentStyle">{{ region.id }}</el-descriptions-item>
        <el-descriptions-item label="网络平面数" :content-style="desContentStyle">{{ region.plane_count }}</el-descriptions-item>
        <el-descriptions-item label="IP分配数" :content-style="desContentStyle">{{ region.allocation_count }}</el-descriptions-item>
        <el-descriptions-item label="创建时间" :content-style="desContentStyle">{{ formatDateTime(region.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="更新时间" :content-style="desContentStyle">{{ formatDateTime(region.updated_at) }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <!-- Network Planes (树形展示) -->
    <el-card shadow="never" class="section-card">
      <template #header>
        <div class="card-header">
          <span class="card-title">已启用的网络平面</span>
          <div class="header-actions" style="gap: 8px">
            <el-select v-model="newPlaneTypeId" placeholder="选择网络平面类型" size="small" style="width: 180px" clearable>
              <el-option
                v-for="pt in availablePlaneTypes"
                :key="pt.id"
                :label="pt.name"
                :value="pt.id"
              />
            </el-select>
            <el-input v-model="newPlaneCidr" placeholder="CIDR, 如 10.0.0.0/22" size="small" style="width: 200px" clearable />
            <el-button size="small" type="primary" @click="enablePlane" :disabled="!newPlaneTypeId || !newPlaneCidr">启用</el-button>
          </div>
        </div>
      </template>
      <div v-if="planeTree.length > 0" class="plane-tree-container">
        <el-tree
          :data="planeTree"
          :props="{ children: 'children', label: 'plane_type_name' }"
          node-key="id"
          default-expand-all
          :expand-on-click-node="false"
        >
          <template #default="{ node, data }">
            <span class="plane-tree-node">
              <el-icon><Connection /></el-icon>
              <span class="plane-type-name">{{ data.plane_type_name }}</span>
              <el-tag size="small" type="info" effect="plain" class="plane-cidr-tag">{{ data.cidr }}</el-tag>
              <span class="plane-alloc-count">{{ data.allocation_count }} 分配</span>
              <span class="plane-actions">
                <el-button size="small" text type="primary" @click.stop="showCreateChild(data)">添加子网</el-button>
                <el-popconfirm
                  title="确定删除此平面？其所有子平面和 IP 分配也将被一并删除"
                  @confirm="disablePlane(data.id)"
                >
                  <template #reference>
                    <el-button size="small" text type="danger">删除</el-button>
                  </template>
                </el-popconfirm>
              </span>
            </span>
          </template>
        </el-tree>
      </div>
      <el-empty v-else description="尚未启用任何网络平面" :image-size="80" />
    </el-card>

    <!-- IP Allocations -->
    <el-card shadow="never" class="section-card">
      <template #header>
        <div class="card-header">
          <span class="card-title">IP 地址分配</span>
          <div class="header-actions" style="gap: 8px">
            <el-cascader
              v-model="filterPlaneId"
              :options="planeTree"
              :props="{ value: 'id', label: 'plane_type_name', children: 'children', emitPath: false }"
              placeholder="全部网络平面"
              size="small"
              style="width: 200px"
              clearable
              @change="fetchAllocations"
            />
            <el-button size="small" type="primary" @click="showCreateAllocation" :icon="Plus">添加分配</el-button>
          </div>
        </div>
      </template>
      <el-table :data="allocations" stripe v-loading="allocationLoading" empty-text="暂无IP分配">
        <el-table-column prop="ip_range" label="IP地址段(CIDR)" width="160" />
        <el-table-column prop="plane_type_name" label="网络平面" width="120" />
        <el-table-column prop="vlan_id" label="VLAN ID" width="90" align="center" />
        <el-table-column prop="gateway" label="网关" width="140" />
        <el-table-column prop="subnet_mask" label="子网掩码" width="140" />
        <el-table-column prop="purpose" label="用途" min-width="160" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="statusTag(row.status)" size="small" effect="plain">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right">
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

    <!-- 创建子网络平面对话框 -->
    <el-dialog v-model="childDialogVisible" title="添加子网络平面" width="480px" :close-on-click-modal="false">
      <el-form :model="childForm" :rules="childRules" label-width="100px">
        <el-form-item label="父平面">
          <el-tag type="primary" effect="plain">{{ childForm.parentName }}</el-tag>
          <span style="margin-left: 8px; color: var(--color-text-tertiary); font-size: 12px">
            CIDR: {{ childForm.parentCidr }}
          </span>
        </el-form-item>
        <el-form-item label="子网CIDR" prop="cidr">
          <el-input v-model="childForm.cidr" placeholder="如 10.0.0.0/24" />
          <span class="form-tip">子网 CIDR 必须在 {{ childForm.parentCidr }} 范围内</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="childDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleCreateChild" :loading="childSubmitting">确定</el-button>
      </template>
    </el-dialog>

    <!-- Allocation Dialog -->
    <el-dialog v-model="allocDialogVisible" :title="isEditAlloc ? '编辑IP分配' : '添加IP分配'" width="550px" :close-on-click-modal="false">
      <el-form ref="allocFormRef" :model="allocForm" :rules="allocRules" label-width="120px">
        <el-form-item label="网络平面" prop="plane_id">
          <el-cascader
            v-model="allocForm.plane_id"
            :options="planeTree"
            :props="{ value: 'id', label: 'plane_type_name', children: 'children', emitPath: false }"
            style="width: 100%"
            :disabled="isEditAlloc"
            placeholder="选择网络平面节点（含CIDR范围约束）"
          />
        </el-form-item>
        <el-form-item label="IP地址段" prop="ip_range">
          <el-input v-model="allocForm.ip_range" placeholder="例如: 10.0.0.0/24" />
        </el-form-item>
        <el-form-item label="VLAN ID" prop="vlan_id">
          <el-input-number v-model="allocForm.vlan_id" :min="1" :max="4094" :step="1" style="width: 100%" :controls="false" />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="网关" prop="gateway">
              <el-input v-model="allocForm.gateway" placeholder="10.0.0.1" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="子网掩码" prop="subnet_mask">
              <el-input v-model="allocForm.subnet_mask" placeholder="255.255.255.0" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="用途" prop="purpose">
          <el-input v-model="allocForm.purpose" type="textarea" :rows="2" placeholder="描述此IP段的用途" />
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
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  getRegion, fetchRegionPlanes, enableRegionPlane, createChildPlane, disableRegionPlane,
  fetchRegionAllocations, createAllocation, updateAllocation, deleteAllocation
} from '@/api/regions'
import { fetchPlaneTypes } from '@/api/networkPlaneTypes'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Edit, Delete, Connection, Plus } from '@element-plus/icons-vue'
import { formatDateTime } from '@/utils/time'

const props = defineProps({ id: String })
const router = useRouter()

const loading = ref(false)
const region = ref({ name: '', planes: [] })
const allocations = ref([])
const allocationTotal = ref(0)
const allocationLoading = ref(false)
const allocationPage = ref(1)
const allocationPageSize = ref(20)

// ---- 平面相关状态 ----
const newPlaneTypeId = ref('')
const newPlaneCidr = ref('')
const availablePlaneTypes = ref([])
const filterPlaneId = ref('')

// ---- 子平面对话框 ----
const childDialogVisible = ref(false)
const childSubmitting = ref(false)
const childForm = ref({
  parentId: '',
  parentName: '',
  parentCidr: '',
  cidr: '',
})
const childRules = {
  cidr: [{ required: true, message: '请输入子网 CIDR', trigger: 'blur' }],
}

// ---- IP 分配对话框 ----
const allocDialogVisible = ref(false)
const isEditAlloc = ref(false)
const editAllocId = ref(null)
const allocSubmitting = ref(false)
const allocFormRef = ref(null)
const allocForm = ref({
  plane_id: '', ip_range: '', vlan_id: null, gateway: '',
  subnet_mask: '', purpose: '', status: 'active',
})

const allocRules = {
  plane_id: [{ required: true, message: '请选择网络平面节点', trigger: 'change' }],
  ip_range: [{ required: true, message: '请输入IP地址段', trigger: 'blur' }],
}

// ---- 计算属性 ----
const planeTree = computed(() => region.value.planes || [])

const desContentStyle = { color: 'var(--color-text-primary)', fontSize: '13px' }

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
    if (filterPlaneId.value) {
      params.plane_id = filterPlaneId.value
    }
    const res = await fetchRegionAllocations(props.id, params)
    allocations.value = res.items
    allocationTotal.value = res.total
  } finally {
    allocationLoading.value = false
  }
}

// ---------- 平面操作 ----------

async function enablePlane() {
  if (!newPlaneTypeId.value || !newPlaneCidr.value) return
  try {
    await enableRegionPlane(props.id, newPlaneTypeId.value, newPlaneCidr.value)
    ElMessage.success('网络平面已启用')
    newPlaneTypeId.value = ''
    newPlaneCidr.value = ''
    await fetchRegion()
    await fetchPlanes()
  } catch (e) { /* handled by interceptor */ }
}

function showCreateChild(data) {
  childForm.value = {
    parentId: data.id,
    parentName: data.plane_type_name,
    parentCidr: data.cidr,
    cidr: '',
  }
  childDialogVisible.value = true
}

async function handleCreateChild() {
  childSubmitting.value = true
  try {
    await createChildPlane(props.id, childForm.value.parentId, childForm.value.cidr)
    ElMessage.success('子网络平面已创建')
    childDialogVisible.value = false
    await fetchRegion()
    await fetchPlanes()
  } finally {
    childSubmitting.value = false
  }
}

async function disablePlane(planeId) {
  try {
    await disableRegionPlane(props.id, planeId)
    ElMessage.success('网络平面已删除')
    await fetchRegion()
    await fetchPlanes()
    await fetchAllocations()
  } catch (e) { /* handled */ }
}

// ---------- IP 分配操作 ----------

function showCreateAllocation() {
  isEditAlloc.value = false
  editAllocId.value = null
  allocForm.value = { plane_id: '', ip_range: '', vlan_id: null, gateway: '', subnet_mask: '', purpose: '', status: 'active' }
  allocDialogVisible.value = true
}

function showEditAllocation(row) {
  isEditAlloc.value = true
  editAllocId.value = row.id
  allocForm.value = {
    plane_id: row.plane_id || '',
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
      plane_type_id: '',
      plane_id: allocForm.value.plane_id,
      ip_range: allocForm.value.ip_range,
      vlan_id: allocForm.value.vlan_id || null,
      gateway: allocForm.value.gateway || null,
      subnet_mask: allocForm.value.subnet_mask || null,
      purpose: allocForm.value.purpose || '',
      status: allocForm.value.status,
    }
    // 从 planeTree 中查找 plane_type_id
    function findPlaneTypeId(nodes, targetId) {
      for (const n of nodes) {
        if (n.id === targetId) return n.plane_type_id
        if (n.children) {
          const found = findPlaneTypeId(n.children, targetId)
          if (found) return found
        }
      }
      return null
    }
    data.plane_type_id = findPlaneTypeId(planeTree.value, data.plane_id) || ''

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

// ---------- Region 操作 ----------

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
.page-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: var(--spacing-lg);
}
.page-title { font-size: var(--font-size-xl); font-weight: 700; color: var(--color-text-primary); margin: 4px 0 0; }
.page-desc { font-size: var(--font-size-sm); color: var(--color-text-tertiary); margin-top: 4px; }
.header-actions { display: flex; gap: 8px; }
.region-info { margin-bottom: var(--spacing-md); }
.section-card { margin-bottom: var(--spacing-md); }
.card-header { display: flex; align-items: center; justify-content: space-between; }
.card-title {
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--color-text-primary);
  position: relative;
  padding-left: 12px;
}
.card-title::before {
  content: '';
  position: absolute;
  left: 0;
  top: 2px;
  bottom: 2px;
  width: 3px;
  background: var(--color-primary);
  border-radius: 2px;
}
.plane-tree-container { padding: 8px 0; }
.plane-tree-node {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  padding: 4px 8px;
  width: 100%;
}
.plane-type-name { font-weight: 500; min-width: 80px; }
.plane-cidr-tag { font-family: 'SF Mono', monospace; }
.plane-alloc-count { color: var(--color-text-tertiary); font-size: 12px; }
.plane-actions { margin-left: auto; display: flex; gap: 4px; }
.form-tip { display: block; color: var(--color-text-tertiary); font-size: 12px; margin-top: 4px; line-height: 1.4; }
</style>
