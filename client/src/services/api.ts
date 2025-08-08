// Centralized API service
import { useAuthStore } from '@/stores/auth'
import { logApiRequest, logApiResponse, logApiError } from './logger'

const API_BASE_URL = import.meta.env.VITE_API_URL || ''

// Debug logging
console.log('[API Service] VITE_API_URL:', import.meta.env.VITE_API_URL)
console.log('[API Service] API_BASE_URL:', API_BASE_URL)

export class ApiService {
  private static getUrl(endpoint: string): string {
    const url = `${API_BASE_URL}${endpoint}`
    console.log('[API Service] Generated URL:', url)
    return url
  }

  static async request<T = any>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = this.getUrl(endpoint)
    const method = options.method || 'GET'
    
    // Log API request
    logApiRequest(method, endpoint, options.body ? JSON.parse(options.body as string) : undefined)
    
    // Get auth token from localStorage directly to avoid circular dependency
    const token = localStorage.getItem('accessToken')
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    }
    
    // Add custom headers
    if (options.headers) {
      Object.assign(headers, options.headers)
    }
    
    // Add Authorization header if token exists
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }
    
    const defaultOptions: RequestInit = {
      credentials: 'include', // Keep this to support both token and cookie auth
      mode: 'cors', // Explicitly set CORS mode
      headers,
      ...options,
    }

    try {
      console.log('[API Service] Making fetch request to:', url)
      console.log('[API Service] Request options:', {
        method: defaultOptions.method,
        headers: defaultOptions.headers,
        credentials: defaultOptions.credentials,
        mode: defaultOptions.mode
      })
      
      const response = await fetch(url, defaultOptions)
      
      console.log('[API Service] Response received:', {
        status: response.status,
        statusText: response.statusText,
        headers: Object.fromEntries(response.headers.entries())
      })
      
      // Log API response
      const responseData = await response.json().catch((e) => {
        console.log('[API Service] Failed to parse JSON response:', e)
        return {}
      })
      logApiResponse(method, endpoint, response.status, responseData)
      
      if (!response.ok) {
        // Check if the error is due to authentication
        if (response.status === 401) {
          // Clear invalid token
          localStorage.removeItem('accessToken')
          // Redirect to login if not already there
          if (!window.location.pathname.includes('/login')) {
            window.location.href = '/login'
          }
        }
        const errorData = responseData.detail || `HTTP ${response.status}: ${response.statusText}`
        logApiError(method, endpoint, errorData)
        throw new Error(errorData)
      }

      console.log('[API Service] Request successful, returning data:', responseData)
      return responseData
    } catch (error) {
      console.log('[API Service] Fetch error details:', {
        name: (error as Error).name,
        message: (error as Error).message,
        stack: (error as Error).stack
      })
      logApiError(method, endpoint, error)
      throw error
    }
  }

  static async get<T = any>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'GET' })
  }

  static async post<T = any>(endpoint: string, data?: any): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  static async put<T = any>(endpoint: string, data?: any): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  }

  static async delete<T = any>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'DELETE' })
  }
}

// API endpoints
export const API_ENDPOINTS = {
  // Auth
  AUTH_LOGIN: '/api/auth/login',
  AUTH_LOGOUT: '/api/auth/logout',
  AUTH_ME: '/api/auth/me',
  AUTH_REGISTER: '/api/auth/register',
  
  // Portfolio
  PORTFOLIO_SUMMARY: '/api/portfolio/summary',
  PORTFOLIO_SETTINGS: '/api/portfolio/settings',
  PORTFOLIO_POSITIONS: '/api/portfolio/',
  
  // Market Data & Workflows
  MARKET_SYNC: '/api/workflows/market-sync',  // Main workflow for portfolio updates
  SYMBOL_SYNC: '/api/workflows/symbol-sync',  // For updating specific symbols
  WORKFLOW_STATUS: '/api/workflows/status',   // Get sync status
  RATE_LIMIT_STATS: '/api/market-data/rate-limit-stats',
  RESET_RATE_LIMIT: '/api/market-data/reset-rate-limit',
} as const 