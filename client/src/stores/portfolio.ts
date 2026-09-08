import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useAuthStore } from './auth'
import type { Position, PortfolioSettings, PortfolioSummary, ApiResponse } from '@/types'
import { ApiService, API_ENDPOINTS } from '@/services/api'
import { logInfo, logWidgetAction, logWidgetError } from '@/services/logger'

export const usePortfolioStore = defineStore('portfolio', () => {
  // State
  const positions = ref<Position[]>([])
  const portfolioCash = ref(0)
  const portfolioBTCDollar = ref(0)
  const btcAvgBuyPrice = ref(0)
  const isLoading = ref(false)
  const isSyncing = ref(false)
  const error = ref<string | null>(null)
  const lastUpdated = ref<Date | null>(null)

  // Getters
  const totalPortfolioValue = computed(() => {
    const positionsValue = positions.value.reduce((sum, pos) => sum + (pos.market_value || 0), 0)
    return positionsValue + portfolioCash.value + portfolioBTCDollar.value
  })

  const cryptoPositions = computed(() => 
    positions.value.filter(pos => pos.is_crypto)
  )

  const stockPositions = computed(() => 
    positions.value.filter(pos => !pos.is_crypto)
  )

  const sortedPositions = computed(() => {
    const totalValue = totalPortfolioValue.value
    
    // Process all positions to ensure they have proper calculations
    const processedPositions = positions.value.map(pos => {
      // Add BTC notes calculation
      let notes = pos.notes || ''
      if (pos.symbol === 'BTC' && portfolioBTCDollar.value && btcAvgBuyPrice.value) {
        const btcQuantity = portfolioBTCDollar.value / btcAvgBuyPrice.value
        notes = `₿${btcQuantity.toFixed(8)}`
      }
      
      return {
        ...pos,
        percent_of_portfolio: totalValue > 0 ? ((pos.market_value || 0) / totalValue) * 100 : 0,
        todays_return: pos.todays_return || 0,
        total_return: pos.total_return || 0,
        total_return_percent: pos.total_return_percent || 0,
        beta: pos.beta || 0,
        delta: pos.delta || 0,
        notes: notes
      }
    })

    // Create CASH position with special styling
    const cashPosition: Position = {
      id: 'cash',
      symbol: 'CASH',
      amount: portfolioCash.value,
      avg_buy_price: 0,
      market_value: portfolioCash.value,
      percent_of_portfolio: portfolioCash.value > 0 && totalValue > 0 ? (portfolioCash.value / totalValue) * 100 : 0,
      todays_return: 0,
      total_return: 0,
      total_return_percent: 0,
      beta: 0,
      delta: 0,
      notes: portfolioCash.value > 0 ? `$${portfolioCash.value.toFixed(2)}` : '',
      is_crypto: false,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      is_cash: true // Special flag for styling
    }

    // Create BTC position from settings (not from positions array) with special styling
    const btcPosition: Position = {
      id: 'btc',
      symbol: 'BTC',
      amount: portfolioBTCDollar.value,
      avg_buy_price: btcAvgBuyPrice.value,
      market_value: portfolioBTCDollar.value,
      percent_of_portfolio: portfolioBTCDollar.value > 0 && totalValue > 0 ? (portfolioBTCDollar.value / totalValue) * 100 : 0,
      todays_return: 0,
      total_return: 0,
      total_return_percent: 0,
      beta: 0,
      delta: 0,
      notes: portfolioBTCDollar.value > 0 && btcAvgBuyPrice.value > 0 ? `₿${(portfolioBTCDollar.value / btcAvgBuyPrice.value).toFixed(8)}` : '',
      is_crypto: true,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      is_btc: true // Special flag for styling
    }

    // Filter out any BTC position from the processed positions to avoid duplication
    const otherPositions = processedPositions.filter(pos => pos.symbol !== 'BTC')

    // Always return CASH first, then BTC, then other positions
    const result = []
    if (portfolioCash.value > 0) {
      result.push(cashPosition)
    }
    if (portfolioBTCDollar.value > 0) {
      result.push(btcPosition)
    }
    result.push(...otherPositions)
    
    return result
  })

  // Actions
  async function fetchPortfolioData(): Promise<void> {
    const authStore = useAuthStore()
    if (!authStore.isAuthenticated) {
      logInfo('Portfolio', 'User not authenticated, skipping fetch')
      return
    }

    isLoading.value = true
    error.value = null

    try {
      logWidgetAction('Portfolio', 'fetchPortfolioData', { userId: authStore.currentUser?.id })
      
      // Fetch portfolio summary (which includes positions)
      const summaryData: PortfolioSummary = await ApiService.get(API_ENDPOINTS.PORTFOLIO_SUMMARY)
      logInfo('Portfolio', 'Received summary data', { positionsCount: summaryData.positions?.length || 0 })
      
      // Extract positions from summary data
      positions.value = summaryData.positions || []
      
      // Fetch portfolio settings separately
      try {
        const settingsData: PortfolioSettings = await ApiService.get(API_ENDPOINTS.PORTFOLIO_SETTINGS)
        logInfo('Portfolio', 'Received settings data', settingsData)
        
        portfolioCash.value = settingsData.total_portfolio_cash || 0
        portfolioBTCDollar.value = settingsData.total_portfolio_btc || 0
        btcAvgBuyPrice.value = settingsData.btc_avg_buy_price || 0
      } catch (error) {
        logInfo('Portfolio', 'No portfolio settings found, using defaults')
        portfolioCash.value = 0
        portfolioBTCDollar.value = 0
        btcAvgBuyPrice.value = 0
      }
      
      lastUpdated.value = new Date()
      
      logWidgetAction('Portfolio', 'fetchPortfolioData', { 
        success: true, 
        positionsCount: positions.value.length,
        totalValue: totalPortfolioValue.value 
      })
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error'
      logWidgetError('Portfolio', 'fetchPortfolioData', err)
      error.value = errorMessage
    } finally {
      isLoading.value = false
    }
  }

  async function updatePortfolioSettings(settings: Partial<PortfolioSettings>): Promise<ApiResponse> {
    try {
      logWidgetAction('Portfolio', 'updatePortfolioSettings', settings)
      
      // Ensure all numeric values are valid numbers
      const validatedSettings = {
        ...settings,
        total_portfolio_btc: typeof settings.total_portfolio_btc === 'number' ? settings.total_portfolio_btc : 0,
        btc_avg_buy_price: typeof settings.btc_avg_buy_price === 'number' ? settings.btc_avg_buy_price : 0,
        robinhood_enabled: Boolean(settings.robinhood_enabled),
        robinhood_username: settings.robinhood_username?.trim() || null,
        robinhood_password: settings.robinhood_password?.trim() || null,
        robinhood_mfa: settings.robinhood_mfa?.trim() || null
      }
      
      // Log the validated settings (excluding sensitive data)
      logWidgetAction('Portfolio', 'updatePortfolioSettings', {
        ...validatedSettings,
        robinhood_password: validatedSettings.robinhood_password ? '***' : null,
        robinhood_mfa: validatedSettings.robinhood_mfa ? '***' : null
      })
      
      const result = await ApiService.put(API_ENDPOINTS.PORTFOLIO_SETTINGS, validatedSettings)
      
      // Update local state with server response values
      if (result && result.data) {
        portfolioCash.value = result.data.total_portfolio_cash || 0
        portfolioBTCDollar.value = result.data.total_portfolio_btc || 0
        btcAvgBuyPrice.value = result.data.btc_avg_buy_price || 0
      } else {
        // Fallback to validated values if server response is missing
        portfolioCash.value = validatedSettings.total_portfolio_cash || 0
        portfolioBTCDollar.value = validatedSettings.total_portfolio_btc
        btcAvgBuyPrice.value = validatedSettings.btc_avg_buy_price
      }
      
      logWidgetAction('Portfolio', 'updatePortfolioSettings', { success: true })
      return { success: true, data: result }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error'
      logWidgetError('Portfolio', 'updatePortfolioSettings', { error: errorMessage, settings })
      return { success: false, error: errorMessage }
    }
  }

  async function syncMarketData(): Promise<ApiResponse> {
    try {
      isSyncing.value = true
      error.value = null
      logWidgetAction('Portfolio', 'syncMarketData')
      
      const result = await ApiService.post(API_ENDPOINTS.MARKET_SYNC)
      
      // Refresh portfolio data after sync
      await fetchPortfolioData()
      
      logWidgetAction('Portfolio', 'syncMarketData', { success: true })
      return { success: true, data: result }
    } catch (err) {
      logWidgetError('Portfolio', 'syncMarketData', err)
      return { success: false, error: err instanceof Error ? err.message : 'Unknown error' }
    } finally {
      isSyncing.value = false
    }
  }

  async function addPosition(position: Partial<Position>): Promise<ApiResponse<Position>> {
    try {
      logWidgetAction('Portfolio', 'addPosition', position)
      
      const result = await ApiService.post(API_ENDPOINTS.PORTFOLIO_POSITIONS, position)
      
      // Refresh portfolio data
      await fetchPortfolioData()
      
      logWidgetAction('Portfolio', 'addPosition', { success: true, positionId: result.id })
      return { success: true, data: result }
    } catch (err) {
      logWidgetError('Portfolio', 'addPosition', err)
      return { success: false, error: err instanceof Error ? err.message : 'Unknown error' }
    }
  }

  async function updatePosition(id: string, updates: Partial<Position>): Promise<ApiResponse<Position>> {
    try {
      logWidgetAction('Portfolio', 'updatePosition', { id, updates })
      
      const result = await ApiService.put(`${API_ENDPOINTS.PORTFOLIO_POSITIONS}/${id}`, updates)
      
      // Refresh portfolio data
      await fetchPortfolioData()
      
      logWidgetAction('Portfolio', 'updatePosition', { success: true, positionId: id })
      return { success: true, data: result }
    } catch (err) {
      logWidgetError('Portfolio', 'updatePosition', err)
      return { success: false, error: err instanceof Error ? err.message : 'Unknown error' }
    }
  }

  async function deletePosition(id: string): Promise<ApiResponse> {
    try {
      logWidgetAction('Portfolio', 'deletePosition', { id })
      
      const result = await ApiService.delete(`${API_ENDPOINTS.PORTFOLIO_POSITIONS}/${id}`)
      
      // Refresh portfolio data
      await fetchPortfolioData()
      
      logWidgetAction('Portfolio', 'deletePosition', { success: true, positionId: id })
      return { success: true, data: result }
    } catch (err) {
      logWidgetError('Portfolio', 'deletePosition', err)
      return { success: false, error: err instanceof Error ? err.message : 'Unknown error' }
    }
  }

  function clearPortfolio(): void {
    logWidgetAction('Portfolio', 'clearPortfolio')
    positions.value = []
    portfolioCash.value = 0
    portfolioBTCDollar.value = 0
    btcAvgBuyPrice.value = 0
    error.value = null
    lastUpdated.value = null
  }

  return {
    // State
    positions,
    portfolioCash,
    portfolioBTCDollar,
    btcAvgBuyPrice,
    isLoading,
    isSyncing,
    error,
    lastUpdated,

    // Getters
    totalPortfolioValue,
    cryptoPositions,
    stockPositions,
    sortedPositions,

    // Actions
    fetchPortfolioData,
    updatePortfolioSettings,
    syncMarketData,  // Renamed from pullRobinhoodData
    addPosition,
    updatePosition,
    deletePosition,
    clearPortfolio
  }
})