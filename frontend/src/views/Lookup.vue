<template>
  <div>
    <h2 class="page-title">IP 查找</h2>

    <el-card shadow="never" class="search-card">
      <el-form :inline="true" @submit.prevent="handleSearch">
        <el-form-item label="IP地址 / CIDR">
          <el-input
            v-model="query"
            placeholder="例如: 10.0.0.5 或 10.0.0.0/24"
            style="width: 300px"
            clearable
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="匹配模式">
          <el-radio-group v-model="exact">
            <el-radio :value="true">精确匹配</el-radio>
            <el-radio :value="false">包含匹配</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch" :loading="searching">查找</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" v-if="searched">
      <template #header>
        <span>查找结果 ({{ total }} 条)</span>
      </template>
      <el-table :data="results" stripe v-loading="searching" empty-text="未找到匹配的IP分配">
        <el-table-column prop="ip_range" label="IP地址段" width="160" />
        <el-table-column prop="region_name" label="所属区域" width="160" />
        <el-table-column prop="plane_type_name" label="网络平面" width="120" />
        <el-table-column prop="vlan_id" label="VLAN ID" width="90" />
        <el-table-column prop="gateway" label="网关" width="140" />
        <el-table-column prop="purpose" label="用途" min-width="160" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : row.status === 'reserved' ? 'warning' : 'info'" size="small">
              {{ row.status === 'active' ? '已使用' : row.status === 'reserved' ? '已预留' : '已废弃' }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-empty v-else-if="!searching" description="输入 IP 或 CIDR 开始搜索" />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { lookupIP } from '@/api/lookup'

const query = ref('')
const exact = ref(true)
const searching = ref(false)
const searched = ref(false)
const results = ref([])
const total = ref(0)

async function handleSearch() {
  if (!query.value.trim()) return
  searching.value = true
  searched.value = true
  try {
    const res = await lookupIP(query.value.trim(), exact.value)
    results.value = res.results || []
    total.value = res.total || 0
  } catch (e) {
    results.value = []
    total.value = 0
  } finally {
    searching.value = false
  }
}
</script>

<style scoped>
.page-title { font-size: 20px; margin-bottom: 16px; color: #303133; }
.search-card { margin-bottom: 16px; }
</style>
