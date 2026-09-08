<template>
  <div class="min-h-screen bg-slate-900 flex flex-col">
    <!-- Main Content Area -->
    <div class="flex-1 flex flex-col min-w-0">
      <!-- Header with logo and proper styling -->
      <header class="site-header py-4 px-6 border-b border-slate-700 bg-slate-800">
        <div class="max-w-[85rem] mx-auto px-4 sm:px-6 lg:px-8">
          <div class="flex flex-wrap justify-between items-center gap-3">
            <div class="flex items-center gap-3">
              <a href="/" class="flex items-center gap-3 text-lg sm:text-2xl font-bold text-white">
                <img src="/icons/favicon-32x32.png" alt="Finance Dashboard Logo" class="w-8 h-8 sm:w-10 sm:h-10">
                Finance Dashboard
              </a>
            </div>
            <div class="flex items-center gap-4">
              <!-- Connection indicator dot -->
              <span
                class="connection-dot"
                :class="{ connected: isConnected }"
                title="Connected"
                aria-label="Connection status"
              ></span>
              <!-- Compact hamburger/gear button (top-right) opens the user menu -->
              <div class="relative">
                <button
                  @click="toggleUserMenu"
                  class="bg-green-600 hover:bg-green-700 text-white w-11 h-11 rounded-lg flex items-center justify-center transition-colors"
                  aria-haspopup="true"
                  :aria-expanded="showUserMenu"
                  aria-label="Account menu"
                >
                  <!-- 3-bar hamburger on mobile (hidden sm:inline), user icon on desktop -->
                  <i class="fa-solid fa-bars text-lg sm:hidden" aria-hidden="true"></i>
                  <i class="fa-solid fa-user text-lg hidden sm:inline" aria-hidden="true"></i>
                </button>

                <!-- User Menu Dropdown (Settings/Account only) -->
                <div
                  v-if="showUserMenu"
                  class="absolute right-0 mt-2 w-64 bg-slate-800 border border-slate-700 rounded-xl shadow-lg z-50"
                  @click.stop
                >
                  <div class="py-2.5 flex flex-col">
                    <button
                      @click="openPortfolioSettings"
                      class="w-full text-left px-5 py-3.5 text-white hover:bg-slate-700 rounded-lg flex items-center gap-3 transition-colors min-h-[44px]"
                    >
                      <i class="fa-solid fa-gear w-4 text-center"></i>
                      <span>Settings / Account</span>
                    </button>
                    
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </header>

      <!-- Main Content -->
      <main class="flex-grow py-6 overflow-y-auto">
        <div class="max-w-[85rem] mx-auto px-4 sm:px-6 lg:px-8">
          <div class="h-full">
            <!-- Portfolio Widget Section -->
            <div class="max-w-[85rem] mx-auto w-full">
              <PortfolioWidget />
            </div>
            <!-- Divider -->
            <div class="max-w-[85rem] mx-auto w-full flex justify-center py-2">
              <div class="border-t border-slate-700 w-full"></div>
            </div>
            <!-- Orders Widget Section -->
            <div class="max-w-[85rem] mx-auto w-full">
              <OrdersWidget />
            </div>
            <!-- Divider -->
            <div class="max-w-[85rem] mx-auto w-full flex justify-center py-2">
              <div class="border-t border-slate-700 w-full"></div>
            </div>
            <!-- Dividends Widget Section -->
            <div class="max-w-[85rem] mx-auto w-full">
              <DividendsWidget />
            </div>
            <!-- Divider -->
            <div class="max-w-[85rem] mx-auto w-full flex justify-center py-2">
              <div class="border-t border-slate-700 w-full"></div>
            </div>
            <!-- Profit/Loss Widget Section -->
            <div class="max-w-[85rem] mx-auto w-full">
              <ProfitLossWidget />
            </div>
            <!-- Divider -->
            <div class="max-w-[85rem] mx-auto w-full flex justify-center py-2">
              <div class="border-t border-slate-700 w-full"></div>
            </div>
            <!-- Reports Area -->
            <div class="max-w-[85rem] mx-auto w-full">
              <ReportWidget />
            </div>
          </div>
        </div>
      </main>

      <!-- Footer -->
      <footer class="site-footer py-4 px-6 border-t border-slate-700 bg-slate-800">
        <div class="max-w-[85rem] mx-auto px-4 sm:px-6 lg:px-8">
          <div class="flex flex-col md:flex-row justify-between items-center gap-4">
            <div class="text-slate-400 text-sm">
              &copy; 2026 Finance Dashboard. All rights reserved.
              <span class="text-xs text-slate-500 ml-2">v1.0.0</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import { usePortfolioStore } from '../../stores/portfolio'
import { useMarketDataStore } from '../../stores/marketData'
import { useToastStore } from '../../stores/toast'
import { useWidgetStore } from '../../stores/widgets'
import PortfolioWidget from '../widgets/PortfolioWidget.vue'
import OrdersWidget from '../widgets/OrdersWidget.vue'
import DividendsWidget from '../widgets/DividendsWidget.vue'
import ProfitLossWidget from '../widgets/ProfitLossWidget.vue'
import ReportWidget from '../widgets/ReportWidget.vue'

const router = useRouter()
const authStore = useAuthStore()
const portfolioStore = usePortfolioStore()
const marketDataStore = useMarketDataStore()
const toastStore = useToastStore()
const widgetStore = useWidgetStore()

// User menu state
const showUserMenu = ref(false)

// Connection health state
const isConnected = ref(false)
let healthCheckInterval = null

const checkHealth = async () => {
  try {
    const response = await fetch('/health', { method: 'GET', signal: AbortSignal.timeout(5000) })
    isConnected.value = response.ok
  } catch {
    isConnected.value = false
  }
}

// Toggle user menu
const toggleUserMenu = () => {
  showUserMenu.value = !showUserMenu.value
}

// Open the Robinhood/portfolio settings from the header menu.
// PortfolioWidget listens for this window event to reveal its Settings modal.
const openPortfolioSettings = () => {
  showUserMenu.value = false
  window.dispatchEvent(new CustomEvent('open-portfolio-settings'))
}

// Close user menu when clicking outside
const closeUserMenu = (event) => {
  const userButton = event.target.closest('button')
  const userMenu = event.target.closest('.absolute')
  
  if (!userButton && !userMenu) {
    showUserMenu.value = false
  }
}



let syncInterval = null

onMounted(() => {
  // Initialize widgets
  widgetStore.initializeWidgets()
  
  // Load initial data
  portfolioStore.fetchPortfolioData()
  
  // Set up health check polling
  checkHealth()
  healthCheckInterval = setInterval(checkHealth, 30000) // every 30 seconds
  
  // Set up periodic data refresh
  syncInterval = setInterval(() => {
    portfolioStore.fetchPortfolioData()
    marketDataStore.fetchMarketData()
  }, 600000) // 10 minutes
  
  // Add click outside listener for user menu
  document.addEventListener('click', closeUserMenu)
})

onUnmounted(() => {
  if (healthCheckInterval) {
    clearInterval(healthCheckInterval)
  }
  if (syncInterval) {
    clearInterval(syncInterval)
  }
  
  // Remove click outside listener
  document.removeEventListener('click', closeUserMenu)
})
</script>

<style scoped>
/* Connection status dot — red when disconnected, green pulsing when connected */
.connection-dot {
  display: inline-block;
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background-color: #ef4444;
  transition: background-color 0.3s ease, box-shadow 0.3s ease;
  flex-shrink: 0;
}
.connection-dot.connected {
  background-color: #22c55e;
  box-shadow: 0 0 6px rgba(34, 197, 94, 0.7);
  animation: pulse 2s ease-in-out infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.55; }
}
</style> 