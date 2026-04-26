<template>
  <el-menu
    :default-active="activeMenu"
    router
    :collapse="false"
    background-color="#304156"
    text-color="#bfcbd9"
    active-text-color="#409EFF"
    style="border-right: none; height: 100%"
  >
    <div class="logo">
      <span class="logo-text">HCS LLD 管理</span>
    </div>
    <el-menu-item index="/dashboard">
      <el-icon><DataAnalysis /></el-icon>
      <span>仪表盘</span>
    </el-menu-item>
    <el-menu-item index="/regions">
      <el-icon><Location /></el-icon>
      <span>区域管理</span>
    </el-menu-item>
    <el-menu-item index="/plane-types">
      <el-icon><Connection /></el-icon>
      <span>网络平面类型</span>
    </el-menu-item>
    <el-menu-item index="/lookup">
      <el-icon><Search /></el-icon>
      <span>IP 查找</span>
    </el-menu-item>
    <el-menu-item index="/import-export">
      <el-icon><Upload /></el-icon>
      <span>导入 / 导出</span>
    </el-menu-item>
    <el-menu-item index="/change-logs">
      <el-icon><Clock /></el-icon>
      <span>变更历史</span>
    </el-menu-item>
  </el-menu>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import {
  DataAnalysis, Location, Connection, Search, Upload, Clock
} from '@element-plus/icons-vue'

const route = useRoute()
const activeMenu = computed(() => route.path)
</script>

<style scoped>
.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}
.logo-text {
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 1px;
}
</style>
