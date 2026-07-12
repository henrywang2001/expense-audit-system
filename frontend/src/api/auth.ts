import { post, get } from '@/utils/request'
import type { LoginForm, RegisterForm, TokenResponse, User, ApiResponse } from '@/types'

export function login(data: LoginForm): Promise<TokenResponse> {
  return post<TokenResponse>('/auth/login', data)
}

export function register(data: RegisterForm): Promise<TokenResponse> {
  return post<TokenResponse>('/auth/register', data)
}

export function getUserInfo(): Promise<ApiResponse<User>> {
  return get<ApiResponse<User>>('/auth/me')
}

export function logout(): Promise<any> {
  return post('/auth/logout')
}
