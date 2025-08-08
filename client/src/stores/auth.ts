import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { ApiService, API_ENDPOINTS } from '@/services/api'
import { logAuthAction, logAuthError, logInfo } from '@/services/logger'

export const useAuthStore = defineStore('auth', () => {
  // State
  const currentUser = ref<{ id: string; email: string; name?: string } | null>(null)
  const accessToken = ref<string | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  // Getters
  const isAuthenticated = computed(() => !!currentUser.value?.id && !!accessToken.value)
  const userEmail = computed(() => currentUser.value?.email || '')

  // Actions
  async function login(email: string, password: string): Promise<boolean> {
    isLoading.value = true
    error.value = null

    try {
      logAuthAction('login', { email })
      
      const response = await ApiService.post(API_ENDPOINTS.AUTH_LOGIN, { email, password })
      
      if (!response.access_token || !response.user?.id) {
        throw new Error('Invalid response from server')
      }

      accessToken.value = response.access_token
      currentUser.value = response.user
      
      // Store token in localStorage
      localStorage.setItem('accessToken', response.access_token)
      
      logAuthAction('login', { success: true, userId: response.user.id })
      return true
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Login failed'
      logAuthError('login', err)
      error.value = errorMessage
      return false
    } finally {
      isLoading.value = false
    }
  }

  async function logout(): Promise<void> {
    try {
      logAuthAction('logout')
      
      if (accessToken.value) {
        await ApiService.post(API_ENDPOINTS.AUTH_LOGOUT)
      }
    } catch (err) {
      logAuthError('logout', err)
      // Continue with logout even if API call fails
    } finally {
      // Clear local state
      currentUser.value = null
      accessToken.value = null
      error.value = null
      
      // Clear localStorage
      localStorage.removeItem('accessToken')
      
      logAuthAction('logout', { success: true })
    }
  }

  async function checkAuthStatus(): Promise<boolean> {
    try {
      logAuthAction('checkAuthStatus')
      
      // Check if we have a token in localStorage
      const storedToken = localStorage.getItem('accessToken')
      if (!storedToken) {
        logInfo('Auth', 'No stored token found')
        return false
      }

      // Set token in state
      accessToken.value = storedToken
      
      // Verify token with backend
      try {
        const user = await ApiService.get(API_ENDPOINTS.AUTH_ME)
        
        // Validate user object
        if (!user?.id) {
          throw new Error('Invalid user data received')
        }
        
        currentUser.value = user
        logAuthAction('checkAuthStatus', { success: true, userId: user.id })
        return true
      } catch (err) {
        // If token verification fails, clear everything
        currentUser.value = null
        accessToken.value = null
        localStorage.removeItem('accessToken')
        throw err
      }
    } catch (err) {
      logAuthError('checkAuthStatus', err)
      return false
    }
  }

  async function createAccount(email: string, password: string, name: string): Promise<boolean> {
    isLoading.value = true
    error.value = null

    try {
      logAuthAction('createAccount', { email })
      
      const response = await ApiService.post(API_ENDPOINTS.AUTH_REGISTER, {
        email,
        password,
        name
      })
      
      // Auto-login after successful registration
      if (response.user && response.user.id) {
        return await login(email, password)
      }
      
      return true
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Account creation failed'
      logAuthError('createAccount', err)
      error.value = errorMessage
      return false
    } finally {
      isLoading.value = false
    }
  }

  // Initialize auth state
  checkAuthStatus()

  return {
    // State
    currentUser,
    accessToken,
    isLoading,
    error,
    
    // Getters
    isAuthenticated,
    userEmail,
    
    // Actions
    login,
    logout,
    checkAuthStatus,
    createAccount
  }
}) 