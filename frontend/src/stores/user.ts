import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { User, LoginForm } from '@/types'
import { login as loginApi, getUserInfo as getUserInfoApi, logout as logoutApi } from '@/api/auth'
import { getToken, setToken, removeToken } from '@/utils/helpers'
import router from '@/router'

export const useUserStore = defineStore('user', () => {
  const user = ref<User | null>(null)
  const token = ref<string | null>(getToken())

  const isLoggedIn = computed(() => !!token.value)
  const username = computed(() => user.value?.username || '')
  const userRole = computed(() => user.value?.role || 'employee')
  const fullName = computed(() => user.value?.full_name || user.value?.username || '')

  function hasPermission(roles: string[]): boolean {
    if (!roles || roles.length === 0) return true
    return roles.includes(userRole.value)
  }

  const menuItems = computed(() => {
    const items = [
      { path: '/dashboard', title: '工作台', icon: 'Monitor' },
      { path: '/expense/submit', title: '提交报销', icon: 'Edit' },
      { path: '/expense/list', title: '我的报销', icon: 'Document' },
      { path: '/approval', title: '审批中心', icon: 'Checked' },
      { path: '/reports', title: '统计报表', icon: 'PieChart' }
    ]

    if (userRole.value === 'admin' || userRole.value === 'finance') {
      items.splice(4, 0, { path: '/rules', title: '规则管理', icon: 'Setting' })
    }

    return items
  })

  async function login(form: LoginForm) {
    const res = await loginApi(form)
    const tokenData = (res as any).data || res
    token.value = tokenData.access_token
    setToken(tokenData.access_token)
    await fetchUserInfo()
  }

  async function fetchUserInfo() {
    try {
      const res = await getUserInfoApi()
      user.value = res.data
    } catch (error) {
      console.error('Failed to fetch user info:', error)
    }
  }

  async function logout() {
    try {
      await logoutApi()
    } catch (error) {
      console.error('Logout API error:', error)
    } finally {
      user.value = null
      token.value = null
      removeToken()
      router.push('/login')
    }
  }

  return {
    user,
    token,
    isLoggedIn,
    username,
    userRole,
    fullName,
    menuItems,
    hasPermission,
    login,
    fetchUserInfo,
    logout
  }
})
