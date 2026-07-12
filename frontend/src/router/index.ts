import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { getToken } from '@/utils/helpers'

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
        meta: { title: '统计报表' }
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
router.beforeEach((to, _from, next) => {
  // Set page title
  document.title = (to.meta.title as string) || '财务报销审核系统'

  const token = getToken()

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

  // Check role permissions
  const requiredRoles = to.meta.roles as string[] | undefined
  if (requiredRoles && requiredRoles.length > 0) {
    // We'll check roles dynamically from the store
    // For now, allow through - detailed check done at component level
    next()
  } else {
    next()
  }
})

export default router
