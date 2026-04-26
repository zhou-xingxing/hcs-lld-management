<template>
  <div class="dashboard">
    <h2 class="page-title">仪表盘</h2>
    <el-row :gutter="20" class="stat-row">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value">{{ stats.total_regions }}</div>
          <div class="stat-label">区域总数</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value">{{ stats.total_plane_types }}</div>
          <div class="stat-label">网络平面类型</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value">{{ stats.total_allocations }}</div>
          <div class="stat-label">IP 分配总数</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value">{{ stats.total_change_logs }}</div>
          <div class="stat-label">变更记录数</div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header><span>按状态分布</span></template>
          <div v-if="Object.keys(stats.allocation_by_status).length === 0" class="empty-text">暂无数据</div>
          <div v-else>
            <div v-for="(count, status) in stats.allocation_by_status" :key="status" class="status-row">
              <el-tag :type="statusTag(status)" size="small">{{ statusLabel(status) }}</el-tag>
              <span class="status-count">{{ count }}</span>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header><span>按区域分布</span></template>
          <div v-if="stats.allocation_by_region.length === 0" class="empty-text">暂无数据</div>
          <div v-else>
            <div v-for="item in stats.allocation_by_region" :key="item.region_name" class="status-row">
              <span class="region-name">{{ item.region_name }}</span>
              <span class="status-count">{{ item.count }}</span>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="hover" class="recent-card">
      <template #header><span>最近变更</span></template>
      <el-table :data="stats.recent_changes" stripe style="width: 100%" v-loading="loading">
        <el-table-column prop="created_at" label="时间" width="180" />
        <el-table-column prop="entity_type" label="类型" width="140" />
        <el-table-column prop="action" label="操作" width="100" />
        <el-table-column prop="operator" label="操作者" width="100" />
        <el-table-column prop="summary" label="摘要" min-width="200" show-overflow-tooltip />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { fetchStats } from '@/api/excel'

const loading = ref(false)
const stats = ref({
  total_regions: 0,
  total_plane_types: 0,
  total_allocations: 0,
  total_change_logs: 0,
  allocation_by_status: {},
  allocation_by_region: [],
  recent_changes: [],
})

function statusTag(status) {
  const map = { active: 'success', reserved: 'warning', deprecated: 'info' }
  return map[status] || 'info'
}

function statusLabel(status) {
  const map = { active: '已使用', reserved: '已预留', deprecated: '已废弃' }
  return map[status] || status
}

onMounted(async () => {
  loading.value = true
  try {
    stats.value = await fetchStats()
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.dashboard { max-width: 1200px; }
.page-title { font-size: 20px; margin-bottom: 20px; color: #303133; }
.stat-row { margin-bottom: 20px; }
.stat-card { text-align: center; }
.stat-value { font-size: 36px; font-weight: 700; color: #409EFF; }
.stat-label { font-size: 14px; color: #909399; margin-top: 8px; }
.status-row { display: flex; align-items: center; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #f0f0f0; }
.status-row:last-child { border-bottom: none; }
.status-count { font-size: 16px; font-weight: 600; color: #303133; }
.region-name { font-size: 14px; color: #606266; }
.recent-card { margin-top: 20px; }
.empty-text { color: #909399; font-size: 14px; padding: 20px; text-align: center; }
</style>
