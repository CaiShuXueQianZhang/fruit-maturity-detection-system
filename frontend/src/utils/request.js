import axios from 'axios'
import { ElMessage } from 'element-plus'

const service = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api',
  timeout: 120000
})

const getErrorMessage = (error) => {
  const data = error.response?.data
  if (typeof data?.detail === 'string') return data.detail
  if (Array.isArray(data?.detail)) return data.detail.map(item => item.msg || item.message).filter(Boolean).join('；')
  if (typeof data?.message === 'string') return data.message
  if (error.code === 'ECONNABORTED') return '请求超时，请稍后重试'
  if (!error.response) return '无法连接服务器，请确认后端服务已启动'
  return '服务器处理失败，请稍后重试'
}

// 请求拦截器
service.interceptors.request.use(
  config => {
    try {
      const token = localStorage.getItem('token')
      if (token) {
        config.headers = config.headers || {}
        config.headers.Authorization = `Bearer ${token}`
      }
    } catch (e) {
      // ignore
    }
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 响应拦截器
service.interceptors.response.use(
  response => {
    return response.data
  },
  error => {
    const message = getErrorMessage(error)
    const url = error.config?.url || ''
    if (error.response?.status === 401 && !url.includes('/auth/login') && !url.includes('/auth/register')) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    if (!error.config?.skipErrorMessage) {
      ElMessage.error(message)
    }
    return Promise.reject(error)
  }
)

export default service