<template>
  <div class="min-h-screen bg-slate-900 flex flex-col">
    <!-- Header with logo and proper styling -->
    <header class="site-header py-4 px-6 border-b border-slate-700 bg-slate-800">
      <div class="max-w-[85rem] mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between items-center">
          <div class="flex items-center gap-4">
                                    <a href="/" class="flex items-center gap-3 text-2xl font-bold text-white">
                          <img src="/icons/favicon-32x32.png" alt="GreenArrow Labs Logo" class="w-10 h-10">
                          GreenArrow Labs
                        </a>
          </div>
          <div class="flex items-center gap-4">
            <!-- User Email Button (shows logout option when clicked) -->
            <div class="relative">
              <button
                @click="toggleUserMenu"
                class="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg flex items-center gap-2 transition-colors"
              >
                <i class="fas fa-user"></i>
                <span>{{ authStore.userEmail }}</span>
              </button>
              
              <!-- User Menu Dropdown -->
              <div 
                v-if="showUserMenu"
                class="absolute right-0 mt-2 bg-slate-800 border border-slate-700 rounded-lg shadow-lg z-50 min-w-[200px]"
                @click.stop
              >
                <div class="p-2">
                  <button
                    @click="handleLogout"
                    class="w-full text-left px-4 py-2 text-white hover:bg-slate-700 rounded flex items-center gap-2 transition-colors"
                  >
                    <i class="fas fa-sign-out-alt"></i>
                    Logout
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <main class="flex-grow py-6">
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
            &copy; 2025 GreenArrow Labs. All rights reserved.
          </div>
        </div>
      </div>
    </footer>
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

// Toggle user menu
const toggleUserMenu = () => {
  showUserMenu.value = !showUserMenu.value
}

// Close user menu when clicking outside
const closeUserMenu = (event) => {
  const userButton = event.target.closest('button')
  const userMenu = event.target.closest('.absolute')
  
  if (!userButton && !userMenu) {
    showUserMenu.value = false
  }
}

// Handle logout with confirmation like the original
const handleLogout = async () => {
  // Show logout confirmation like the original
  if (confirm('Are you sure you want to logout?')) {
    try {
      await authStore.logout()
      toastStore.show('Logged out successfully', 'info')
      
      // Redirect to landing page after a short delay
      setTimeout(() => {
        router.push('/')
      }, 1500)
    } catch (error) {
      console.error('Logout error:', error)
      toastStore.show('Logout failed', 'error')
    }
  }
  
  // Close the user menu
  showUserMenu.value = false
}

let syncInterval = null

onMounted(() => {
  // Initialize widgets
  widgetStore.initializeWidgets()
  
  // Load initial data
  portfolioStore.fetchPortfolioData()
  
  // Set up periodic data refresh
  syncInterval = setInterval(() => {
    portfolioStore.fetchPortfolioData()
    marketDataStore.fetchMarketData()
  }, 600000) // 10 minutes
  
  // Add click outside listener for user menu
  document.addEventListener('click', closeUserMenu)
})

onUnmounted(() => {
  if (syncInterval) {
    clearInterval(syncInterval)
  }
  
  // Remove click outside listener
  document.removeEventListener('click', closeUserMenu)
})
</script> 