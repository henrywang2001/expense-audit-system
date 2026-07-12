export interface User {
  id: number
  username: string
  email: string
  full_name: string
  department: string
  role: 'employee' | 'finance' | 'admin'
  is_active: boolean
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
  token_type: string
}

export interface ApiResponse<T> {
  code: number
  message: string
  data: T
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}
