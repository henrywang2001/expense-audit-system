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

  /**
   * 侧边栏菜单项。
   * ⚠️ 这里的显隐必须与 `router/index.ts` 中各路由的 `meta.roles` 保持一致，
   *    否则会出现「菜单可见但进入即被守卫弹回 /dashboard」的割裂体验。
   *    当前受限页面：/rules 与 /reports —— 仅 admin / finance 可见。
   */
  const menuItems = computed(() => {
    const isPrivileged = userRole.value === 'admin' || userRole.value === 'finance'

    const items: Array<{ path: string; title: string; icon: string }> = [
      { path: '/dashboard', title: '工作台', icon: 'Monitor' },
      { path: '/expense/submit', title: '提交报销', icon: 'Edit' },
      { path: '/expense/list', title: '我的报销', icon: 'Document' },
      { path: '/approval', title: '审批中心', icon: 'Checked' }
    ]

    if (isPrivileged) {
      items.push({ path: '/rules', title: '规则管理', icon: 'Setting' })
      items.push({ path: '/reports', title: '统计报表', icon: 'PieChart' })
    }

    return items
  })

  async function login(form: LoginForm) {
    const res = await loginApi(form)
    const tokenData = res.data
    token.value = tokenData.access_token
    setToken(tokenData.access_token)
    // 登录响应的 data 中已内联 user，直接赋值可省一次 /auth/me 请求
    if (tokenData.user) {
      user.value = tokenData.user
    } else {
      await fetchUserInfo()
    }
  }

  /**
   * 拉取当前用户信息。
   * ⚠️ GET /auth/me 是【裸响应】（顶层就是 User 对象，无 success/data 信封），
   *    所以这里必须 `user.value = res`，写成 `res.data` 会恒为 undefined。
   */
  async function fetchUserInfo() {
    try {
      const res = await getUserInfoApi()
      user.value = res
    } catch (error) {
      console.error('Failed to fetch user info:', error)
    }
  }

  /** 供路由守卫调用：有 token 但 user 尚未加载时补拉一次 */
  async function ensureUserLoaded() {
    if (token.value && !user.value) {
      await fetchUserInfo()
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
    ensureUserLoaded,
    logout
  }
})
