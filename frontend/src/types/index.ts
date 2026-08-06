export interface User {
  id: number
  username: string
  email: string
  full_name: string
  phone?: string | null
  department: string
  position?: string | null
  role: 'employee' | 'manager' | 'finance' | 'admin'
  is_active: boolean
  is_superuser?: boolean
  last_login_at?: string | null
  created_at: string
  updated_at: string
}

export interface LoginForm {
  username: string
  password: string
}

export interface RegisterForm {
  username: string
  password: string
  password_confirm: string
  email: string
  full_name: string
  department: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  user: User
}

/**
 * 形态 B：对象信封。
 * 注意：`utils/request.ts` 的响应拦截器已 `return data`，
 * 所以业务代码里的 `res` 就是这个信封本身，payload 取 `res.data`。
 */
export interface ApiResponse<T> {
  success: boolean
  data: T
  message?: string
}

/**
 * 形态 A：分页列表信封。
 * 关键：`total` 与 `data` 平级（不在 data 里），取法为 `res.data` / `res.total`。
 * `total_pages` 可选 —— `/approvals/` 不返回该字段。
 */
export interface ApiListResponse<T> {
  success: boolean
  data: T[]
  total: number
  page: number
  page_size: number
  total_pages?: number
  message?: string
}

export * from './expense'
export * from './rule'
