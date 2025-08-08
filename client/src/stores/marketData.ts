import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useAuthStore } from './auth'
import type { RateLimitStats, ApiResponse } from '@/types'
import { ApiService, API_ENDPOINTS } from '@/services/api'

export const useMarketDataStore = defineStore('marketData', () => {
  // State
  const isSyncing = ref(false)
  const lastSyncTime = ref<Date | null>(null)
  const syncError = ref<string | null>(null)
  const rateLimitStats = ref<RateLimitStats | null>(null)

  // Getters
  const canSync = computed(() => !isSyncing.value)

  // Actions
  async function syncMarketData(): Promise<ApiResponse> {
    const authStore = useAuthStore()
    if (!authStore.isAuthenticated) {
      console.log('[MarketData] User not authenticated, skipping sync')
      return { success: false, error: 'User not authenticated' }
    }

    isSyncing.value = true
    syncError.value = null

    try {
      console.log('[MarketData] Starting market data sync...')
      
      // Use the unified market sync workflow endpoint
      const data = await ApiService.post(API_ENDPOINTS.MARKET_SYNC)
      lastSyncTime.value = new Date()
      
      console.log('[MarketData] Market data sync completed successfully')
      return { success: true, data }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error'
      syncError.value = errorMessage
      console.error('[MarketData] Market data sync failed:', err)
      return { success: false, error: errorMessage }
    } finally {
      isSyncing.value = false
    }
  }

  async function syncRobinhoodData(): Promise<ApiResponse> {
    const authStore = useAuthStore()
    if (!authStore.isAuthenticated) {
      console.log('[MarketData] User not authenticated, skipping Robinhood sync')
      return { success: false, error: 'User not authenticated' }
    }

    isSyncing.value = true
    syncError.value = null

    try {
      console.log('[MarketData] Starting Robinhood sync...')
      
      // Robinhood pull is handled inside the unified market sync workflow
      const data = await ApiService.post(API_ENDPOINTS.MARKET_SYNC)
      lastSyncTime.value = new Date()
      
      console.log('[MarketData] Robinhood sync completed successfully')
      return { success: true, data }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error'
      syncError.value = errorMessage
      console.error('[MarketData] Robinhood sync failed:', err)
      return { success: false, error: errorMessage }
    } finally {
      isSyncing.value = false
    }
  }

  // Backwards-compatible alias used by some pages
  async function fetchMarketData(): Promise<ApiResponse> {
    return syncMarketData()
  }

  async function getRateLimitStats(): Promise<RateLimitStats | null> {
    try {
      const data: RateLimitStats = await ApiService.get(API_ENDPOINTS.RATE_LIMIT_STATS)
      rateLimitStats.value = data
      return data
    } catch (err) {
      console.error('[MarketData] Failed to get rate limit stats:', err)
      return null
    }
  }

  async function resetRateLimit(): Promise<ApiResponse> {
    try {
      await ApiService.post(API_ENDPOINTS.RESET_RATE_LIMIT)
      console.log('[MarketData] Rate limit reset successfully')
      await getRateLimitStats()
      return { success: true }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error'
      console.error('[MarketData] Failed to reset rate limit:', err)
      return { success: false, error: errorMessage }
    }
  }

  return {
    // State
    isSyncing,
    lastSyncTime,
    syncError,
    rateLimitStats,
    
    // Getters
    canSync,
    
    // Actions
    syncMarketData,
    fetchMarketData,
    syncRobinhoodData,
    getRateLimitStats,
    resetRateLimit
  }
}) 