import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

type WidgetState = {
  isMinimized: boolean
  showActionBar: boolean
}

type WidgetStates = {
  portfolio: WidgetState
  orders: WidgetState
  dividends: WidgetState
  profitLoss: WidgetState
  reports: WidgetState
}

type WidgetName = keyof WidgetStates

export const useWidgetStore = defineStore('widgets', () => {
  // Widget states - all start minimized by default
  const widgetStates = ref<WidgetStates>({
    portfolio: { isMinimized: true, showActionBar: false },
    orders: { isMinimized: true, showActionBar: false },
    dividends: { isMinimized: true, showActionBar: false },
    profitLoss: { isMinimized: true, showActionBar: false },
    reports: { isMinimized: true, showActionBar: false }
  })

  // Computed getters for each widget
  const isPortfolioMinimized = computed(() => widgetStates.value.portfolio.isMinimized)
  const isOrdersMinimized = computed(() => widgetStates.value.orders.isMinimized)
  const isDividendsMinimized = computed(() => widgetStates.value.dividends.isMinimized)
  const isProfitLossMinimized = computed(() => widgetStates.value.profitLoss.isMinimized)
  const isReportsMinimized = computed(() => widgetStates.value.reports.isMinimized)

  const showPortfolioActionBar = computed(() => widgetStates.value.portfolio.showActionBar)
  const showOrdersActionBar = computed(() => widgetStates.value.orders.showActionBar)
  const showDividendsActionBar = computed(() => widgetStates.value.dividends.showActionBar)
  const showProfitLossActionBar = computed(() => widgetStates.value.profitLoss.showActionBar)
  const showReportsActionBar = computed(() => widgetStates.value.reports.showActionBar)

  // Global widget management functions
  function isMinimized(widgetName: WidgetName): boolean {
    return widgetStates.value[widgetName]?.isMinimized ?? true
  }

  function showActionBar(widgetName: WidgetName): boolean {
    return widgetStates.value[widgetName]?.showActionBar ?? false
  }

  function toggleWidget(widgetName: WidgetName) {
    if (widgetStates.value[widgetName]) {
      const state = widgetStates.value[widgetName]
      state.isMinimized = !state.isMinimized
      state.showActionBar = !state.isMinimized // Action bar shows when NOT minimized (expanded)
    }
  }

  function getMinimizeIcon(widgetName: WidgetName): string {
    const isMinimized = widgetStates.value[widgetName]?.isMinimized ?? true
    return isMinimized ? 'fa-solid fa-chevron-down' : 'fa-solid fa-chevron-up'
  }

  function minimizeWidget(widgetName: WidgetName) {
    if (widgetStates.value[widgetName]) {
      widgetStates.value[widgetName].isMinimized = true
      widgetStates.value[widgetName].showActionBar = false // Hide action bar when minimized
    }
  }

  function expandWidget(widgetName: WidgetName) {
    if (widgetStates.value[widgetName]) {
      widgetStates.value[widgetName].isMinimized = false
      widgetStates.value[widgetName].showActionBar = true // Show action bar when expanded
    }
  }

  // Initialize all widgets as minimized
  function initializeWidgets() {
    Object.keys(widgetStates.value).forEach(widgetName => {
      minimizeWidget(widgetName as WidgetName)
    })
  }

  return {
    // State
    widgetStates,
    
    // Computed getters
    isPortfolioMinimized,
    isOrdersMinimized,
    isDividendsMinimized,
    isProfitLossMinimized,
    isReportsMinimized,
    showPortfolioActionBar,
    showOrdersActionBar,
    showDividendsActionBar,
    showProfitLossActionBar,
    showReportsActionBar,
    
    // Actions
    isMinimized,
    showActionBar,
    toggleWidget,
    getMinimizeIcon,
    minimizeWidget,
    expandWidget,
    initializeWidgets
  }
}) 