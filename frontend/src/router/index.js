import { createRouter, createWebHistory } from 'vue-router'
import AppLayout from '@/components/layout/AppLayout.vue'

const routes = [
  {
    path: '/',
    component: AppLayout,
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/Dashboard.vue'),
        meta: { title: '仪表盘' },
      },
      {
        path: 'regions',
        name: 'Regions',
        component: () => import('@/views/Regions.vue'),
        meta: { title: '区域管理' },
      },
      {
        path: 'regions/:id',
        name: 'RegionDetail',
        component: () => import('@/views/RegionDetail.vue'),
        props: true,
        meta: { title: '区域详情' },
      },
      {
        path: 'plane-types',
        name: 'PlaneTypes',
        component: () => import('@/views/PlaneTypes.vue'),
        meta: { title: '网络平面类型' },
      },
      {
        path: 'lookup',
        name: 'Lookup',
        component: () => import('@/views/Lookup.vue'),
        meta: { title: 'IP 查找' },
      },
      {
        path: 'import-export',
        name: 'ImportExport',
        component: () => import('@/views/ImportExport.vue'),
        meta: { title: '导入 / 导出' },
      },
      {
        path: 'change-logs',
        name: 'ChangeLogs',
        component: () => import('@/views/ChangeLogs.vue'),
        meta: { title: '变更历史' },
      },
      {
        path: 'backup-config',
        name: 'BackupConfig',
        component: () => import('@/views/BackupConfig.vue'),
        meta: { title: '备份配置' },
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
