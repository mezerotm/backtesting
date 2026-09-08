<template>
  <div class="min-h-screen bg-slate-900 flex flex-col">
    <!-- Header -->
    <header class="site-header py-4 px-6 border-b border-slate-700 bg-slate-800">
      <div class="max-w-[85rem] mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between items-center">
          <div class="flex items-center gap-4">
            <router-link to="/" class="flex items-center gap-3 text-2xl font-bold text-white">
              <i class="fas fa-chart-line text-blue-500"></i>
              Finance Dashboard
            </router-link>
          </div>
          <div class="flex items-center gap-4">
            <router-link to="/" class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg flex items-center gap-2 transition-colors">
              <i class="fas fa-home"></i>
              <span>Go Home</span>
            </router-link>
          </div>
        </div>
      </div>
    </header>
    
    <!-- Main Content -->
    <main class="flex-grow flex items-center justify-center">
      <div class="max-w-2xl mx-auto px-4 text-center">
        <!-- 404 Icon -->
        <div class="mb-8">
          <div class="w-32 h-32 bg-gradient-to-r from-orange-500 to-red-500 rounded-full flex items-center justify-center mx-auto mb-6">
            <i class="fas fa-exclamation-triangle text-4xl text-white"></i>
          </div>
          <div class="text-8xl font-bold text-slate-700 mb-4">404</div>
        </div>
        
        <!-- Main Message -->
        <h1 class="text-4xl md:text-5xl font-bold text-white mb-6">
          <span class="bg-gradient-to-r from-orange-400 to-red-500 bg-clip-text text-transparent">
            Page Not Found
          </span>
        </h1>
        
        <p class="text-xl text-slate-300 mb-8 leading-relaxed">
          The page you're looking for doesn't exist or has been moved. 
          Don't worry, we'll help you get back on track.
        </p>
        
        <!-- Current URL Display -->
        <div class="bg-slate-800 rounded-lg p-4 mb-8 border border-slate-700">
          <p class="text-slate-400 text-sm mb-2">Attempted URL:</p>
          <p class="text-slate-300 font-mono text-sm break-all">{{ currentUrl }}</p>
        </div>
        
        <!-- Action Buttons -->
        <div class="flex flex-col sm:flex-row gap-4 justify-center">
          <router-link to="/" class="bg-blue-600 hover:bg-blue-700 text-white px-8 py-3 rounded-lg font-semibold transition-colors flex items-center justify-center gap-2">
            <i class="fas fa-home"></i>
            Go to Homepage
          </router-link>
          
          <button @click="goBack" class="bg-slate-700 hover:bg-slate-600 text-white px-8 py-3 rounded-lg font-semibold transition-colors flex items-center justify-center gap-2">
            <i class="fas fa-arrow-left"></i>
            Go Back
          </button>
        </div>
        
        <!-- Helpful Links -->
        <div class="mt-12 pt-8 border-t border-slate-700">
          <h3 class="text-lg font-semibold text-white mb-4">Helpful Links</h3>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <router-link to="/dashboard" class="bg-slate-800 hover:bg-slate-700 text-slate-300 px-4 py-3 rounded-lg transition-colors flex items-center gap-2">
              <i class="fas fa-chart-line"></i>
              Dashboard
            </router-link>
            
            <a href="mailto:support@financedashboard.com" class="bg-slate-800 hover:bg-slate-700 text-slate-300 px-4 py-3 rounded-lg transition-colors flex items-center gap-2">
              <i class="fas fa-envelope"></i>
              Contact Support
            </a>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const currentUrl = computed(() => window.location.href)

function goBack() {
  if (window.history.length > 1) {
    router.go(-1)
  } else {
    router.push('/')
  }
}
</script> 