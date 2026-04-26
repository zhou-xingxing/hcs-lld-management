<template>
  <div class="app-layout">
    <aside class="sidebar">
      <SideMenu />
    </aside>
    <div class="main-container">
      <header class="app-header">
        <div class="header-left">
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/dashboard' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item v-if="route.meta.title">{{ route.meta.title }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="header-right">
          <span class="operator-label">操作者：</span>
          <el-input
            v-model="appStore.operator"
            size="small"
            style="width: 140px"
            placeholder="操作者名称"
            @blur="saveOperator"
          />
        </div>
      </header>
      <main class="app-content">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup>
import { useRoute } from 'vue-router'
import { useAppStore } from '@/stores/app'
import SideMenu from './SideMenu.vue'

const route = useRoute()
const appStore = useAppStore()

function saveOperator() {
  appStore.setOperator(appStore.operator)
}
</script>

<style scoped>
.app-layout {
  display: flex;
  height: 100vh;
}
.sidebar {
  width: 220px;
  flex-shrink: 0;
  background-color: #304156;
  overflow-y: auto;
}
.main-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.app-header {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: #fff;
  border-bottom: 1px solid #e6e6e6;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
}
.header-left {
  display: flex;
  align-items: center;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}
.operator-label {
  font-size: 13px;
  color: #606266;
  white-space: nowrap;
}
.app-content {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  background-color: #f5f7fa;
}
</style>
