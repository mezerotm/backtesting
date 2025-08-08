<template>
  <div class="min-h-screen bg-slate-900 flex flex-col">
    <!-- Header -->
    <header class="site-header py-4 px-6 border-b border-slate-700 bg-slate-800">
      <div class="max-w-[85rem] mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between items-center">
          <div class="flex items-center gap-4">
            <router-link to="/" class="flex items-center gap-3 text-2xl font-bold text-white">
              <img src="/icons/logo-32x32.png" alt="GreenArrow Labs Logo" class="w-10 h-10">
              GreenArrow Labs
            </router-link>
          </div>
          <div class="flex items-center gap-4">
            <button
              @click="showLoginModal = true"
              class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg flex items-center gap-2 transition-colors"
            >
              <i class="fas fa-sign-in-alt"></i>
              <span>Login</span>
            </button>
          </div>
        </div>
      </div>
    </header>

    <!-- Hero Section -->
    <main class="flex-grow">
      <!-- Hero Background with Gradient -->
      <div class="relative overflow-hidden bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
        <!-- Animated Background Elements -->
        <div class="absolute inset-0">
          <div class="absolute top-20 left-10 w-72 h-72 bg-green-500/10 rounded-full blur-3xl animate-pulse"></div>
          <div class="absolute bottom-20 right-10 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl animate-pulse delay-1000"></div>
          <div class="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-80 h-80 bg-purple-500/5 rounded-full blur-3xl animate-pulse delay-500"></div>
        </div>
        
        <!-- Hero Content -->
        <div class="relative z-10 max-w-[85rem] mx-auto px-4 sm:px-6 lg:px-8 py-20">
          <div class="text-center">
            <!-- Main Headline -->
            <h1 class="text-5xl md:text-7xl font-bold text-white mb-6 leading-tight">
              <span class="bg-gradient-to-r from-green-400 to-blue-500 bg-clip-text text-transparent">
                Trade Like a Pro
              </span>
            </h1>
            
            <!-- Subheadline -->
            <p class="text-xl md:text-2xl text-slate-300 mb-8 max-w-3xl mx-auto leading-relaxed">
              Transform from intermediate to professional trader with institutional-grade tools.
              <span class="text-green-400 font-semibold">Built by retail, for retail - no hidden information.</span>
            </p>
            
            <!-- CTA Buttons -->
            <div class="flex flex-col sm:flex-row gap-4 justify-center items-center mb-16">
              <router-link
                to="/create-account"
                class="bg-gradient-to-r from-green-500 to-green-600 hover:from-green-600 hover:to-green-700 text-white px-8 py-4 rounded-lg text-lg font-semibold flex items-center gap-3 transition-all transform hover:scale-105 shadow-lg"
              >
                <i class="fa-solid fa-rocket"></i>
                Get Started Free
              </router-link>
              <button class="border-2 border-slate-600 hover:border-slate-500 text-slate-300 hover:text-white px-8 py-4 rounded-lg text-lg font-semibold transition-all">
                Learn More
              </button>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Features Section -->
      <div class="py-20 bg-slate-800">
        <div class="max-w-[85rem] mx-auto px-4 sm:px-6 lg:px-8">
          <div class="text-center mb-16">
            <h2 class="text-4xl font-bold text-white mb-4">Why Choose GreenArrow Labs?</h2>
            <p class="text-xl text-slate-300 max-w-2xl mx-auto">
              Institutional-grade tools for retail traders. Think like a market maker, trade like a hedge fund.
            </p>
          </div>
          
          <div class="grid grid-cols-1 md:grid-cols-3 gap-12">
            <!-- Feature 1 -->
            <div class="bg-slate-700 rounded-xl p-10 hover:bg-slate-600 transition-all transform hover:scale-105">
              <div class="w-16 h-16 bg-gradient-to-r from-green-500 to-green-600 rounded-lg flex items-center justify-center mb-8">
                <i class="fa-solid fa-chart-pie text-2xl text-white"></i>
              </div>
              <h3 class="text-xl font-bold text-white mb-6">Portfolio Management</h3>
              <p class="text-slate-300 leading-relaxed">
                Hedge fund-level portfolio analysis with beta calculations, 
                correlation matrices, and institutional-grade performance metrics.
              </p>
            </div>
            
            <!-- Feature 2 -->
            <div class="bg-slate-700 rounded-xl p-10 hover:bg-slate-600 transition-all transform hover:scale-105">
              <div class="w-16 h-16 bg-gradient-to-r from-blue-500 to-blue-600 rounded-lg flex items-center justify-center mb-8">
                <i class="fa-solid fa-robot text-2xl text-white"></i>
              </div>
              <h3 class="text-xl font-bold text-white mb-6">AI Finance Assistant</h3>
              <p class="text-slate-300 leading-relaxed">
                Ask direct questions about your portfolio with programmatic finance calculations.
                AI-powered insights with mathematical precision to prevent hallucinations.
              </p>
            </div>
            
            <!-- Feature 3 -->
            <div class="bg-slate-700 rounded-xl p-10 hover:bg-slate-600 transition-all transform hover:scale-105">
              <div class="w-16 h-16 bg-gradient-to-r from-purple-500 to-purple-600 rounded-lg flex items-center justify-center mb-8">
                <i class="fa-solid fa-shield-halved text-2xl text-white"></i>
              </div>
              <h3 class="text-xl font-bold text-white mb-6">Risk Controls</h3>
              <p class="text-slate-300 leading-relaxed">
                Professional risk management with position sizing, drawdown limits,
                and real-time portfolio monitoring to protect your capital.
              </p>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Stats Section -->
      <div class="py-20 bg-slate-900">
        <div class="max-w-[85rem] mx-auto px-4 sm:px-6 lg:px-8">
          <div class="grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
            <div>
              <div class="text-4xl font-bold text-green-400 mb-2">Real-Time</div>
              <div class="text-slate-400">Market Data</div>
            </div>
            <div>
              <div class="text-4xl font-bold text-blue-400 mb-2">100+</div>
              <div class="text-slate-400">Technical Indicators</div>
            </div>
            <div>
              <div class="text-4xl font-bold text-purple-400 mb-2">10M+</div>
              <div class="text-slate-400">Data Points</div>
            </div>
            <div>
              <div class="text-4xl font-bold text-yellow-400 mb-2">Research</div>
              <div class="text-slate-400">Platform</div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- CTA Section -->
      <div class="py-20 bg-gradient-to-r from-green-600 to-blue-600">
        <div class="max-w-[85rem] mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 class="text-4xl font-bold text-white mb-4">Ready to Trade Like a Professional?</h2>
          <p class="text-xl text-white/90 mb-8 max-w-2xl mx-auto">
            Join retail traders who are leveling up with institutional-grade tools.
            No hidden information, no institutional advantages - just pure retail power.
          </p>
          <router-link
            to="/create-account"
            class="bg-white text-green-600 hover:bg-slate-100 px-8 py-4 rounded-lg text-lg font-semibold flex items-center gap-3 mx-auto transition-all transform hover:scale-105"
          >
            <i class="fa-solid fa-arrow-up"></i>
            Start Your Journey
          </router-link>
        </div>
      </div>
    </main>

    <!-- Footer -->
    <footer class="site-footer py-8 px-6 border-t border-slate-700 bg-slate-800">
      <div class="max-w-[85rem] mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex flex-col md:flex-row justify-between items-center gap-4">
          <div class="text-slate-400 text-sm">
            &copy; 2025 GreenArrow Labs. All rights reserved.
          </div>
          <div class="flex items-center gap-6 text-slate-400 text-sm">
            <a href="#" class="hover:text-white transition-colors">Privacy</a>
            <a href="#" class="hover:text-white transition-colors">Terms</a>
            <a href="#" class="hover:text-white transition-colors">Support</a>
          </div>
        </div>
      </div>
    </footer>

    <!-- Login Modal -->
    <div
      v-if="showLoginModal"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      @click="showLoginModal = false"
    >
      <div
        class="bg-slate-800 rounded-lg p-8 w-full max-w-md mx-4"
        @click.stop
      >
        <div class="flex justify-between items-center mb-6">
          <h3 class="text-xl font-bold text-white">
            {{ isRegistering ? 'Create Account' : 'Login' }}
          </h3>
          <button
            @click="showLoginModal = false"
            class="text-gray-400 hover:text-white"
          >
            <i class="fas fa-times"></i>
          </button>
        </div>

        <!-- Login Form -->
        <form @submit.prevent="handleSubmit" class="space-y-4">
          <div>
            <label for="email" class="block text-sm font-medium text-gray-300 mb-1">
              Email
            </label>
            <input
              id="email"
              v-model="form.email"
              type="email"
              required
              autofocus
              class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-white placeholder-gray-400 focus:outline-none focus:border-blue-500"
              placeholder="Enter your email"
            />
          </div>

          <div>
            <label for="password" class="block text-sm font-medium text-gray-300 mb-1">
              Password
            </label>
            <input
              id="password"
              v-model="form.password"
              type="password"
              required
              class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-white placeholder-gray-400 focus:outline-none focus:border-blue-500"
              placeholder="Enter your password"
            />
          </div>

          <div v-if="isRegistering">
            <label for="confirmPassword" class="block text-sm font-medium text-gray-300 mb-1">
              Confirm Password
            </label>
            <input
              id="confirmPassword"
              v-model="form.confirmPassword"
              type="password"
              required
              class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-white placeholder-gray-400 focus:outline-none focus:border-blue-500"
              placeholder="Confirm your password"
            />
          </div>

          <div v-if="authStore.error" class="text-red-400 text-sm">
            {{ authStore.error }}
          </div>

          <button
            type="submit"
            :disabled="authStore.isLoading"
            class="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800 text-white py-2 px-4 rounded-md transition-colors"
          >
            <span v-if="authStore.isLoading">Loading...</span>
            <span v-else>{{ isRegistering ? 'Create Account' : 'Login' }}</span>
          </button>
        </form>

        <div class="mt-4 text-center">
          <button
            @click="isRegistering = !isRegistering"
            class="text-blue-400 hover:text-blue-300 text-sm"
          >
            {{ isRegistering ? 'Already have an account? Login' : 'Need an account? Register' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import { useToastStore } from '../../stores/toast'

const router = useRouter()
const authStore = useAuthStore()
const toastStore = useToastStore()

const showLoginModal = ref(false)
const isRegistering = ref(false)

const form = reactive({
  email: '',
  password: '',
  confirmPassword: ''
})

// Watch for modal opening and focus email input
watch(showLoginModal, async (newValue) => {
  if (newValue) {
    // Wait for modal to render, then focus email input
    await nextTick()
    const emailInput = document.getElementById('email') as HTMLInputElement
    if (emailInput) {
      emailInput.focus()
    }
  }
})

async function handleSubmit() {
  console.log('[LandingPage] handleSubmit called', { isRegistering: isRegistering.value, email: form.email })
  
  if (isRegistering.value) {
    if (form.password !== form.confirmPassword) {
      toastStore.show('Passwords do not match', 'error')
      return
    }
    
    const success = await authStore.createAccount(form.email, form.password)
    console.log('[LandingPage] createAccount result:', { success, error: authStore.error })
    if (success) {
      toastStore.show('Account created successfully!', 'success')
      showLoginModal.value = false
      console.log('[LandingPage] Redirecting to dashboard after account creation')
      router.push('/dashboard')
    } else {
      toastStore.show(authStore.error || 'Account creation failed', 'error')
    }
  } else {
    const success = await authStore.login(form.email, form.password)
    console.log('[LandingPage] login result:', { success, error: authStore.error, isAuthenticated: authStore.isAuthenticated })
    if (success) {
      toastStore.show('Login successful!', 'success')
      showLoginModal.value = false
      console.log('[LandingPage] Redirecting to dashboard after login')
      router.push('/dashboard')
    } else {
      toastStore.show(authStore.error || 'Login failed', 'error')
    }
  }
}
</script> 