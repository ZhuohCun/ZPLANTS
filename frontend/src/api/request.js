import axios from 'axios'
import { ElMessage } from 'element-plus'
import { getToken, clearAuth } from '@/utils/auth'

const RAW_BACKEND_API_BASE_FROM_SOURCE = String(__BACKEND_API_BASE_FROM_SOURCE__ || '').trim()

function trimRightSlash(value) {
  return String(value || '').replace(/\/+$/, '')
}

function hasExplicitProtocol(value) {
  return /^[a-z][a-z0-9+.-]*:\/\//i.test(value)
}

function looksLikeHost(value) {
  return /^(localhost|\d{1,3}(?:\.\d{1,3}){3}|\[[0-9a-f:.]+\]|[a-z0-9-]+(?:\.[a-z0-9-]+)+)(?::\d+)?(?:\/.*)?$/i.test(value)
}

function isLocalOnlyHost(value) {
  try {
    const url = new URL(value)
    return ['localhost', '127.0.0.1', '0.0.0.0', '::1', '[::1]'].includes(url.hostname)
  } catch {
    return /^(localhost|127\.0\.0\.1|0\.0\.0\.0)(?::|\/|$)/i.test(String(value || '').replace(/^\/\//, ''))
  }
}

function remoteVisitorUsesThisSite() {
  if (typeof window === 'undefined') return false
  const host = window.location?.hostname || ''
  return Boolean(host && !['localhost', '127.0.0.1', '0.0.0.0', '::1', '[::1]'].includes(host))
}

function normalizeBackendApiBase(rawValue) {
  const raw = trimRightSlash(rawValue)
  if (!raw) return ''
  const browserProtocol = typeof window !== 'undefined' && window.location?.protocol ? window.location.protocol : 'http:'
  if (raw.startsWith('//')) {
    return `${browserProtocol}${raw}`
  }
  if (hasExplicitProtocol(raw)) {
    return raw
  }
  if (looksLikeHost(raw)) {
    return `${browserProtocol}//${raw}`
  }
  return raw
}

export const BACKEND_API_BASE = normalizeBackendApiBase(RAW_BACKEND_API_BASE_FROM_SOURCE)
export const BACKEND_PUBLIC_BASE = BACKEND_API_BASE.replace(/\/api\/?$/, '')
export const BACKEND_API_CONFIGURED_IN_SOURCE = RAW_BACKEND_API_BASE_FROM_SOURCE

export function backendAssetUrl(value) {
  const text = String(value || '').trim()
  if (!text) return ''
  if (/^https?:\/\//i.test(text) || text.startsWith('data:') || text.startsWith('blob:')) return text
  return `${BACKEND_PUBLIC_BASE}${text.startsWith('/') ? text : `/${text}`}`
}

export const DEFAULT_COVER_URL = backendAssetUrl('/uploads/plants/default-cover.png')

function buildNetworkErrorMessage(error) {
  if (error?.response) {
    return error?.response?.data?.msg || error.message || 'The connection failed. Please try again later.'
  }
  if (!BACKEND_API_BASE || !/^https?:\/\//i.test(BACKEND_API_BASE)) {
    return 'The connection failed. Ask the administrator to check the system service address.'
  }
  if (remoteVisitorUsesThisSite() && isLocalOnlyHost(BACKEND_API_BASE)) {
    return 'The connection failed because the service address still points to this machine. Use a server address that client devices can reach.'
  }
  if (typeof window !== 'undefined' && window.location?.protocol === 'https:' && BACKEND_API_BASE.toLowerCase().startsWith('http://')) {
    return 'The connection failed because this page uses a secure address. The system service must use a secure address as well.'
  }
  return 'The connection failed. Check the network and try again, or contact the administrator if it still does not work.'
}

const service = axios.create({
  baseURL: BACKEND_API_BASE,
  timeout: 0
})

service.interceptors.request.use(async (config) => {
  config.meta = config.meta || {}
  const token = getToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

service.interceptors.response.use(
  (response) => {
    const payload = response.data
    if (![0, 200].includes(Number(payload.code))) {
      if (!response?.config?.meta?.silentError) {
        ElMessage.error({ message: payload.msg || 'The request failed.', offset: 104 })
      }
      return Promise.reject(payload)
    }
    return payload
  },
  (error) => {
    const status = error?.response?.status
    if (status === 401) {
      clearAuth()
      location.href = '/login'
    }
    const silentForForbiddenGet = status === 403 && String(error?.config?.method || '').toLowerCase() === 'get'
    const silent = Boolean(error?.config?.meta?.silentError) || silentForForbiddenGet
    if (!silent) {
      ElMessage.error({ message: buildNetworkErrorMessage(error), offset: 104, duration: 9000, showClose: true })
    }
    return Promise.reject(error)
  }
)

export async function request(config) {
  return service(config)
}
