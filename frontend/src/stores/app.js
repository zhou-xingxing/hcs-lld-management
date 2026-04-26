import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAppStore = defineStore('app', () => {
  const operator = ref(localStorage.getItem('hcs_operator') || 'admin')
  const sidebarCollapsed = ref(false)

  function setOperator(name) {
    operator.value = name
    localStorage.setItem('hcs_operator', name)
  }

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  return { operator, sidebarCollapsed, setOperator, toggleSidebar }
})
