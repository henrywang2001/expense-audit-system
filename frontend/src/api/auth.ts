import { post, get, put } from '@/utils/request'
import type { LoginForm, RegisterForm, TokenResponse, User, ApiResponse } from '@/types'

export function login(data: LoginForm): Promise<ApiResponse<TokenResponse>> {
  return post<ApiResponse<TokenResponse>>('/auth/login', data)
}

export function register(data: RegisterForm): Promise<ApiResponse<TokenResponse>> {
  return post<ApiResponse<TokenResponse>>('/auth/register', data)
}

// ⚠️ GET /auth/me 返回的是【裸的用户对象】，没有 success/data 信封。
//    因此这里返回 Promise<User>，调用方直接用 res，切勿写 res.data。
export function getUserInfo(): Promise<User> {
  return get<User>('/auth/me')
}

// ⚠️ PUT /auth/me 同样是裸响应
export function updateUserInfo(data: Partial<User>): Promise<User> {
  return put<User>('/auth/me', data)
}

export function logout(): Promise<{ success: boolean; message: string }> {
  return post<{ success: boolean; message: string }>('/auth/logout')
}
