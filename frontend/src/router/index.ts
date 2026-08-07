import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { getToken } from '@/utils/helpers'
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { title: '登录', noAuth: true }
  },
  {
    path: '/',
    name: 'Main',
    component: () => import('@/layouts/MainLayout.vue'),
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/Dashboard.vue'),
        meta: { title: '工作台' }
      },
      {
        path: 'expense/submit',
        name: 'ExpenseSubmit',
        component: () => import('@/views/ExpenseSubmit.vue'),
        meta: { title: '提交报销' }
      },
      {
        path: 'expense/list',
        name: 'ExpenseList',
        component: () => import('@/views/ExpenseList.vue'),
        meta: { title: '我的报销' }
      },
      {
        path: 'expense/detail/:id',
        name: 'ExpenseDetail',
        component: () => import('@/views/ExpenseDetailPage.vue'),
        meta: { title: '报销详情' }
      },
      {
        path: 'approval',
        name: 'ApprovalCenter',
        component: () => import('@/views/ApprovalCenter.vue'),
        meta: { title: '审批中心' }
      },
      {
        path: 'rules',
        name: 'RuleManagement',
        component: () => import('@/views/RuleManagement.vue'),
        meta: { title: '规则管理', roles: ['admin', 'finance'] }
      },
      {
        path: 'reports',
        name: 'Reports',
        component: () => import('@/views/Reports.vue'),
        meta: { title: '统计报表', roles: ['admin', 'finance'] }
      }
    ]
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/NotFound.vue'),
    meta: { title: '404' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Route guard
router.beforeEach(async (to, _from, next) => {
  // Set page title
  document.title = (to.meta.title as string) || '财务报销审核系统'

  const token = getToken()
  const userStore = useUserStore()

  if (to.meta.noAuth) {
    // Login page - redirect to dashboard if already logged in
    if (token && to.path === '/login') {
      next('/dashboard')
    } else {
      next()
    }
    return
  }

  if (!token) {
    next('/login')
    return
  }

  // 刷新场景下：有 token 但 store 里的 user 尚未加载，补拉一次用户信息
  await userStore.ensureUserLoaded()

  // 校验角色权限（命中 meta.roles 才放行，避免无限重定向）
  const requiredRoles = to.meta.roles as string[] | undefined
  if (requiredRoles && requiredRoles.length > 0) {
    const userRole = userStore.user?.role
    if (!userRole || !requiredRoles.includes(userRole)) {
      ElMessage.warning('您没有访问该页面的权限')
      next('/dashboard')
      return
    }
  }

  next()
})

export default router
