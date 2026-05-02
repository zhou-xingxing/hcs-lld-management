import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

export const useAppStore = defineStore('app', () => {
  const token = ref(localStorage.getItem('hcs_token') || '')
  const currentUser = ref(JSON.parse(localStorage.getItem('hcs_current_user') || 'null'))
  const sidebarCollapsed = ref(false)
  const isAuthenticated = computed(() => Boolean(token.value))
  const isAdministrator = computed(() => currentUser.value?.role === 'administrator')
  const permittedRegionIds = computed(() =>
    new Set((currentUser.value?.permitted_regions || []).map((item) => item.id))
  )

  function setSession(accessToken, user) {
    token.value = accessToken
    currentUser.value = user
    localStorage.setItem('hcs_token', accessToken)
    localStorage.setItem('hcs_current_user', JSON.stringify(user))
  }

  function setCurrentUser(user) {
    currentUser.value = user
    localStorage.setItem('hcs_current_user', JSON.stringify(user))
  }

  function logout() {
    token.value = ''
    currentUser.value = null
    localStorage.removeItem('hcs_token')
    localStorage.removeItem('hcs_current_user')
  }

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  function canManageRegionBusiness(regionId) {
    return currentUser.value?.role === 'user' && permittedRegionIds.value.has(regionId)
  }

  return {
    token,
    currentUser,
    sidebarCollapsed,
    isAuthenticated,
    isAdministrator,
    permittedRegionIds,
    setSession,
    setCurrentUser,
    logout,
    toggleSidebar,
    canManageRegionBusiness,
  }
})
