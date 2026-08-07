import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios'
import { ElMessage } from 'element-plus'
import { getToken, removeToken } from './helpers'
import router from '@/router'

const baseURL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

const instance: AxiosInstance = axios.create({
  baseURL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request interceptor
instance.interceptors.request.use(
  (config) => {
    const token = getToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor
instance.interceptors.response.use(
  (response: AxiosResponse) => {
    const { data } = response
    // 后端三态响应（A: 分页信封 / B: 对象信封 / C: 裸响应）统一在此剥掉 axios 的一层，
    // 业务层拿到的 `res` 即后端 payload 本身。
    // ⚠️ 契约中没有 `code` 字段，切勿在此再加基于 code 的短路判断（会误杀裸响应）。
    return data
  },
  (error) => {
    if (error.response) {
      const { status, data } = error.response
      switch (status) {
        case 401:
          removeToken()
          ElMessage.error('登录已过期，请重新登录')
          router.push('/login')
          break
        case 403:
          ElMessage.error('权限不足')
          break
        case 404:
          ElMessage.error('请求的资源不存在')
          break
        case 422: {
          // 本项目自定义异常处理器返回 {success:false, message, detail:{errors:[{field,message}]}}
          // 同时兼容 FastAPI 原生的 detail 数组形态与纯字符串形态。
          const detail = data?.detail
          const errors = detail?.errors
          if (Array.isArray(errors) && errors.length > 0) {
            const messages = errors
              .map((e: any) => (e?.field ? `${e.field}: ${e.message}` : e?.message))
              .filter(Boolean)
              .join('；')
            ElMessage.error(messages || data?.message || '请求参数错误')
          } else if (Array.isArray(detail) && detail.length > 0) {
            const messages = detail
              .map((e: any) => e?.msg || e?.message)
              .filter(Boolean)
              .join('；')
            ElMessage.error(messages || data?.message || '请求参数错误')
          } else if (typeof detail === 'string' && detail) {
            ElMessage.error(detail)
          } else {
            ElMessage.error(data?.message || '请求参数错误')
          }
          break
        }
        case 500:
          ElMessage.error('服务器内部错误')
          break
        default:
          ElMessage.error(data?.message || `请求错误 (${status})`)
      }
    } else if (error.code === 'ECONNABORTED') {
      ElMessage.error('请求超时')
    } else {
      ElMessage.error('网络连接异常')
    }
    return Promise.reject(error)
  }
)

// ⚠️ 注意：响应拦截器已 `return data`，所以实例方法返回的是 `AxiosResponse`，
// 业务层拿到的 `T` 实际是 `data` 的载荷类型。为消除 `AxiosResponse` 与 `Promise<T>` 的
// 类型错位（否则每个调用点都会报类型错误），这里统一做一次 `as unknown as Promise<T>` 断言。
// 切勿改动拦截器的 `return data`（那是三态信封剥层的核心约定）。
export function get<T = any>(url: string, params?: any, config?: AxiosRequestConfig): Promise<T> {
  return instance.get(url, { params, ...config }) as unknown as Promise<T>
}

export function post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
  return instance.post(url, data, config) as unknown as Promise<T>
}

export function put<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
  return instance.put(url, data, config) as unknown as Promise<T>
}

export function del<T = any>(url: string, config?: AxiosRequestConfig): Promise<T> {
  return instance.delete(url, config) as unknown as Promise<T>
}

export function upload<T = any>(url: string, file: File, fieldName: string = 'file'): Promise<T> {
  const formData = new FormData()
  formData.append(fieldName, file)
  // 不要手写 Content-Type：手写会丢失 multipart 的 boundary，
  // 交给 axios 依据 FormData 自动生成。
  return instance.post(url, formData) as unknown as Promise<T>
}

export default instance
