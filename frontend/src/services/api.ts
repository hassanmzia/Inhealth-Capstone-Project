import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios'
import { useAuthStore } from '@/store/authStore'

const BASE_URL = import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || '/api/v1'

// ─── Create Axios Instance ────────────────────────────────────────────────────

export const api: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  },
})

// ─── Request Interceptor: JWT Injection ───────────────────────────────────────

api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = useAuthStore.getState().token
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }

    // Inject tenant header
    const user = useAuthStore.getState().user
    if (user?.tenantId) {
      config.headers['X-Tenant-ID'] = user.tenantId
    }

    return config
  },
  (error) => Promise.reject(error),
)

// ─── Response Interceptor: Token Refresh & Error Handling ─────────────────────

let isRefreshing = false
let isRedirecting = false
let failedQueue: Array<{
  resolve: (token: string) => void
  reject: (error: unknown) => void
}> = []

function processQueue(error: unknown, token: string | null = null) {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error)
    } else if (token) {
      prom.resolve(token)
    }
  })
  failedQueue = []
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean }

    // Handle 401 Unauthorized — attempt token refresh
    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        // Queue the request until refresh completes
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        }).then((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`
          return api(originalRequest)
        })
      }

      originalRequest._retry = true
      isRefreshing = true

      try {
        const refreshToken = useAuthStore.getState().refreshToken
        if (!refreshToken) {
          throw new Error('No refresh token available')
        }

        const response = await axios.post(`${BASE_URL}/auth/token/refresh/`, {
          refresh: refreshToken,
        })

        const newToken: string = response.data.access
        useAuthStore.getState().setToken(newToken)
        processQueue(null, newToken)

        originalRequest.headers.Authorization = `Bearer ${newToken}`
        return api(originalRequest)
      } catch (refreshError) {
        processQueue(refreshError)
        useAuthStore.getState().logout()
        // Guard against multiple redirects from concurrent 401 responses
        if (!isRedirecting) {
          isRedirecting = true
          window.location.href = '/login'
        }
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }

    // Handle other errors
    const errorMessage = getErrorMessage(error)

    // Log to console in dev
    if (import.meta.env.DEV) {
      console.error('[API Error]', {
        status: error.response?.status,
        url: originalRequest?.url,
        message: errorMessage,
        data: error.response?.data,
      })
    }

    // Attach human-readable message
    const enhancedError = error as AxiosError & { userMessage: string }
    enhancedError.userMessage = errorMessage

    return Promise.reject(enhancedError)
  },
)

// ─── FHIR-specific instance ────────────────────────────────────────────────────

export const fhirApi: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_FHIR_URL || '/fhir/R4',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/fhir+json',
    Accept: 'application/fhir+json',
  },
})

fhirApi.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  const user = useAuthStore.getState().user
  if (user?.tenantId) {
    config.headers['X-Tenant-ID'] = user.tenantId
  }
  return config
})

fhirApi.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    const enhancedError = error as AxiosError & { userMessage: string }
    enhancedError.userMessage = getErrorMessage(error)
    return Promise.reject(enhancedError)
  },
)

// ─── Error message extraction ─────────────────────────────────────────────────

function getErrorMessage(error: AxiosError): string {
  if (!error.response) {
    if (error.code === 'ECONNABORTED') return 'Request timed out. Please try again.'
    if (error.code === 'ERR_NETWORK') return 'Network error. Check your connection.'
    return 'An unexpected error occurred.'
  }

  const status = error.response.status
  const data = error.response.data as Record<string, unknown>

  // Try to extract message from various response formats
  const raw =
    data?.detail ||
    data?.message ||
    data?.error ||
    ((data?.errors as string[])?.join(', ')) ||
    data?.non_field_errors

  if (raw) {
    if (typeof raw === 'string') return raw
    // DRF sometimes returns detail as an object or array
    if (Array.isArray(raw)) return raw.map(String).join(', ')
    if (typeof raw === 'object') return JSON.stringify(raw)
    return String(raw)
  }

  switch (status) {
    case 400: return 'Invalid request. Please check your input.'
    case 401: return 'Authentication required. Please log in.'
    case 403: return 'You do not have permission to perform this action.'
    case 404: return 'The requested resource was not found.'
    case 409: return 'Conflict with existing data.'
    case 422: return 'Validation error. Please check your input.'
    case 429: return 'Too many requests. Please slow down.'
    case 500: return 'Server error. Please try again later.'
    case 502: return 'Service temporarily unavailable.'
    case 503: return 'Service unavailable. Please try again later.'
    default: return `Request failed with status ${status}.`
  }
}

export default api
