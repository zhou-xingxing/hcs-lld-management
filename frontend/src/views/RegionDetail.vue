<template>
  <div v-loading="loading">
    <div class="page-heading">
      <div>
        <el-button size="small" text @click="$router.push('/regions')" :icon="ArrowLeft" style="margin-bottom: 8px">返回区域列表</el-button>
        <h2 class="page-title">{{ region.name }}</h2>
        <p class="page-desc">区域详情与网络平面管理</p>
      </div>
      <div v-if="appStore.isAdministrator" class="header-actions">
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
        <el-descriptions-item label="创建时间" :content-style="desContentStyle">{{ formatDateTime(region.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="更新时间" :content-style="desContentStyle">{{ formatDateTime(region.updated_at) }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <!-- Network Planes (树形展示) -->
    <el-card shadow="never" class="section-card">
      <template #header>
        <div class="card-header">
          <span class="card-title">已启用的网络平面</span>
          <div v-if="canManageBusiness" class="header-actions" style="gap: 8px">
            <el-select v-model="newPlaneTypeId" placeholder="选择网络平面类型" size="small" style="width: 180px" clearable>
              <el-option
                v-for="pt in availablePlaneTypes"
                :key="pt.id"
                :label="pt.name"
                :value="pt.id"
              />
            </el-select>
            <el-input v-model="newPlaneCidr" placeholder="CIDR, 如 10.0.0.0/22" size="small" style="width: 200px" clearable />
            <el-input-number v-model="newPlaneVlanId" placeholder="VLAN" size="small" :min="1" :max="4094" :step="1" :controls="false" style="width: 90px" />
            <el-input v-model="newPlaneGatewayPosition" placeholder="网关位置" size="small" style="width: 120px" clearable />
            <el-input
              v-model="newPlaneGatewayIp"
              placeholder="网关IP"
              size="small"
              style="width: 140px"
              clearable
              @focus="fillRecommendedGatewayIp"
            />
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
              <el-tag v-if="data.vlan_id" size="small" type="warning" effect="plain">VLAN {{ data.vlan_id }}</el-tag>
              <el-tag v-if="data.gateway_position" size="small" type="success" effect="plain">{{ data.gateway_position }}</el-tag>
              <el-tag v-if="data.gateway_ip" size="small" type="success" effect="plain">{{ data.gateway_ip }}</el-tag>
              <span v-if="canManageBusiness" class="plane-actions">
                <el-popconfirm
                  title="确定删除此平面？其所有子平面也将被一并删除"
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
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getRegion, enableRegionPlane, disableRegionPlane } from '@/api/regions'
import { fetchPlaneTypes } from '@/api/networkPlaneTypes'
import { useAppStore } from '@/stores/app'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Edit, Delete, Connection } from '@element-plus/icons-vue'
import { formatDateTime } from '@/utils/time'

const props = defineProps({ id: String })
const router = useRouter()
const appStore = useAppStore()

const loading = ref(false)
const region = ref({ name: '', planes: [] })

// ---- 平面相关状态 ----
const newPlaneTypeId = ref('')
const newPlaneCidr = ref('')
const newPlaneVlanId = ref(null)
const newPlaneGatewayPosition = ref('')
const newPlaneGatewayIp = ref('')
const availablePlaneTypes = ref([])

// ---- 计算属性 ----
const planeTree = computed(() => region.value.planes || [])
const canManageBusiness = computed(() => appStore.canManageRegionBusiness(props.id))

const desContentStyle = { color: 'var(--color-text-primary)', fontSize: '13px' }

async function fetchRegion() {
  region.value = await getRegion(props.id)
}

async function fetchPlanes() {
  const res = await fetchPlaneTypes({ skip: 0, limit: 500 })
  const enabledPlaneTypeIds = new Set(flattenPlanes(region.value.planes || []).map(p => p.plane_type_id))
  availablePlaneTypes.value = (res.items || []).filter(
    pt => !enabledPlaneTypeIds.has(pt.id)
  )
}

// ---------- 平面操作 ----------

async function enablePlane() {
  if (!newPlaneTypeId.value || !newPlaneCidr.value) return
  try {
    const result = await enableRegionPlane(props.id, {
      plane_type_id: newPlaneTypeId.value,
      cidr: newPlaneCidr.value,
      vlan_id: newPlaneVlanId.value || null,
      gateway_position: newPlaneGatewayPosition.value || null,
      gateway_ip: newPlaneGatewayIp.value || null,
    })
    ElMessage.success('网络平面已启用')
    if (result.gateway_ip_warning) {
      ElMessage.warning(result.gateway_ip_warning)
    }
    newPlaneTypeId.value = ''
    newPlaneCidr.value = ''
    newPlaneVlanId.value = null
    newPlaneGatewayPosition.value = ''
    newPlaneGatewayIp.value = ''
    await fetchRegion()
    await fetchPlanes()
  } catch (e) { /* handled by interceptor */ }
}

function fillRecommendedGatewayIp() {
  if (newPlaneGatewayIp.value || !newPlaneCidr.value || !newPlaneTypeId.value) return
  const planeType = availablePlaneTypes.value.find(pt => pt.id === newPlaneTypeId.value)
  const recommended = recommendedGatewayIp(newPlaneCidr.value, Boolean(planeType?.is_private))
  if (recommended) {
    newPlaneGatewayIp.value = recommended
  }
}

function recommendedGatewayIp(cidr, isPrivate) {
  const [ip, prefixText] = cidr.trim().split('/')
  const prefix = Number(prefixText)
  if (!isValidIpv4(ip) || !Number.isInteger(prefix) || prefix < 0 || prefix > 32) return ''
  const base = ipv4ToNumber(ip)
  const mask = prefix === 0 ? 0 : (0xffffffff << (32 - prefix)) >>> 0
  const network = base & mask
  const broadcast = (network | (~mask >>> 0)) >>> 0
  if (network === broadcast) return numberToIpv4(network)
  if (isPrivate) {
    return numberToIpv4(prefix < 31 ? network + 1 : network)
  }
  return numberToIpv4(prefix < 31 ? broadcast - 1 : broadcast)
}

function isValidIpv4(ip) {
  const parts = ip.split('.')
  return parts.length === 4 && parts.every(part => {
    if (!/^\d+$/.test(part)) return false
    const value = Number(part)
    return value >= 0 && value <= 255
  })
}

function ipv4ToNumber(ip) {
  return ip.split('.').reduce((acc, part) => ((acc << 8) + Number(part)) >>> 0, 0)
}

function numberToIpv4(value) {
  return [24, 16, 8, 0].map(shift => (value >>> shift) & 255).join('.')
}

async function disablePlane(planeId) {
  try {
    await disableRegionPlane(props.id, planeId)
    ElMessage.success('网络平面已删除')
    await fetchRegion()
    await fetchPlanes()
  } catch (e) { /* handled */ }
}

function flattenPlanes(nodes) {
  const result = []
  for (const node of nodes) {
    result.push(node)
    if (node.children) {
      result.push(...flattenPlanes(node.children))
    }
  }
  return result
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
.header-actions { display: flex; flex-wrap: wrap; gap: 8px; }
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
.plane-actions { margin-left: auto; display: flex; gap: 4px; }
.form-tip { display: block; color: var(--color-text-tertiary); font-size: 12px; margin-top: 4px; line-height: 1.4; }
</style>
