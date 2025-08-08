<template>
  <div class="min-h-screen bg-slate-900 flex flex-col">
    <!-- Header -->
    <header class="site-header py-4 px-6 border-b border-slate-700 bg-slate-800">
      <div class="max-w-[85rem] mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between items-center">
          <div class="flex items-center gap-4">
            <router-link to="/" class="flex items-center gap-3 text-2xl font-bold text-white">
              <i class="fas fa-chart-line text-blue-500"></i>
              GreenArrow Labs
            </router-link>
          </div>
          <div class="flex items-center gap-4">
            <button @click="checkServerStatus" class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg flex items-center gap-2 transition-colors">
              <i class="fas fa-sync-alt"></i>
              <span>Check Status</span>
            </button>
          </div>
        </div>
      </div>
    </header>
    
    <!-- Main Content -->
    <main class="flex-grow flex items-center justify-center">
      <div class="max-w-2xl mx-auto px-4 text-center">
        <!-- Server Down Icon -->
        <div class="mb-8">
          <div class="w-32 h-32 bg-gradient-to-r from-red-500 to-orange-500 rounded-full flex items-center justify-center mx-auto mb-6">
            <i class="fas fa-server text-4xl text-white"></i>
          </div>
          <div class="text-6xl font-bold text-slate-700 mb-4">⚠️</div>
        </div>
        
        <!-- Main Message -->
        <h1 class="text-4xl md:text-5xl font-bold text-white mb-6">
          <span class="bg-gradient-to-r from-red-400 to-orange-500 bg-clip-text text-transparent">
            Server Temporarily Unavailable
          </span>
        </h1>
        
        <p class="text-xl text-slate-300 mb-8 leading-relaxed">
          We're experiencing technical difficulties. Our team has been notified and is working to restore service as quickly as possible.
        </p>
        
        <!-- Status Indicators -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          <div class="bg-slate-800 rounded-lg p-4 border border-slate-700">
            <div class="flex items-center justify-center gap-2 mb-2">
              <div class="w-3 h-3 bg-red-500 rounded-full animate-pulse"></div>
              <span class="text-slate-400 text-sm">Backend API</span>
            </div>
            <p class="text-slate-300 font-semibold">Offline</p>
          </div>
          
          <div class="bg-slate-800 rounded-lg p-4 border border-slate-700">
            <div class="flex items-center justify-center gap-2 mb-2">
              <div class="w-3 h-3 bg-red-500 rounded-full animate-pulse"></div>
              <span class="text-slate-400 text-sm">Database</span>
            </div>
            <p class="text-slate-300 font-semibold">Offline</p>
          </div>
          
          <div class="bg-slate-800 rounded-lg p-4 border border-slate-700">
            <div class="flex items-center justify-center gap-2 mb-2">
              <div class="w-3 h-3 bg-green-500 rounded-full"></div>
              <span class="text-slate-400 text-sm">Frontend</span>
            </div>
            <p class="text-slate-300 font-semibold">Online</p>
          </div>
        </div>
        
        <!-- Action Buttons -->
        <div class="flex flex-col sm:flex-row gap-4 justify-center mb-8">
          <button @click="checkServerStatus" class="bg-blue-600 hover:bg-blue-700 text-white px-8 py-3 rounded-lg font-semibold transition-colors flex items-center justify-center gap-2">
            <i class="fas fa-sync-alt"></i>
            Check Server Status
          </button>
          
          <button @click="retryConnection" class="bg-green-600 hover:bg-green-700 text-white px-8 py-3 rounded-lg font-semibold transition-colors flex items-center justify-center gap-2">
            <i class="fas fa-redo"></i>
            Retry Connection
          </button>
        </div>
        
        <!-- Auto-retry Info -->
        <div class="bg-slate-800 rounded-lg p-4 border border-slate-700">
          <p class="text-slate-400 text-sm mb-2">Auto-retry in progress...</p>
          <div class="w-full bg-slate-700 rounded-full h-2">
            <div class="bg-blue-500 h-2 rounded-full animate-pulse" style="width: 60%"></div>
          </div>
          <p class="text-slate-300 text-sm mt-2">Next retry in {{ retryCountdown }} seconds</p>
        </div>
        
        <!-- Contact Info -->
        <div class="mt-12 pt-8 border-t border-slate-700">
          <h3 class="text-lg font-semibold text-white mb-4">Need Help?</h3>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <a href="mailto:support@greenarrowlabs.com" class="bg-slate-800 hover:bg-slate-700 text-slate-300 px-4 py-3 rounded-lg transition-colors flex items-center gap-2">
              <i class="fas fa-envelope"></i>
              Contact Support
            </a>
            
            <a href="https://status.greenarrowlabs.com" target="_blank" class="bg-slate-800 hover:bg-slate-700 text-slate-300 px-4 py-3 rounded-lg transition-colors flex items-center gap-2">
              <i class="fas fa-chart-line"></i>
              Status Page
            </a>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const retryCountdown = ref(30)
let countdownInterval: number | null = null

function checkServerStatus() {
  // Simulate server status check
  console.log('Checking server status...')
}

function retryConnection() {
  // Try to redirect to main app
  router.push('/')
}

onMounted(() => {
  // Start auto-retry countdown
  countdownInterval = window.setInterval(() => {
    retryCountdown.value--
    if (retryCountdown.value <= 0) {
      retryCountdown.value = 30
      retryConnection()
    }
  }, 1000)
})

onUnmounted(() => {
  if (countdownInterval) {
    clearInterval(countdownInterval)
  }
})
</script> 