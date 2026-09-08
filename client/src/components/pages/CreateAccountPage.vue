<template>
  <div class="min-h-screen bg-slate-900 flex flex-col">
    <!-- Header -->
    <header class="site-header py-4 px-6 border-b border-slate-700 bg-slate-800">
      <div class="max-w-[85rem] mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between items-center">
          <div class="flex items-center gap-4">
            <router-link to="/" class="flex items-center gap-3 text-2xl font-bold text-white">
              <img src="/icons/logo-32x32.png" alt="Finance Dashboard Logo" class="w-10 h-10">
              Finance Dashboard
            </router-link>
          </div>
          <div class="flex items-center gap-4">
            <!-- Back to Landing Button -->
            <router-link to="/" class="text-slate-300 hover:text-white transition-colors">
              <i class="fas fa-arrow-left mr-2"></i>
              Back to Home
            </router-link>
            <!-- Login Button -->
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
    
    <!-- Main Content -->
    <main class="flex-grow flex items-center justify-center py-12">
      <div class="max-w-md w-full mx-auto px-4">
        <!-- Create Account Card -->
        <div class="bg-slate-800 rounded-xl p-8 shadow-2xl border border-slate-700">
          <div class="text-center mb-8">
            <div class="w-16 h-16 bg-gradient-to-r from-green-500 to-green-600 rounded-lg flex items-center justify-center mx-auto mb-4">
              <i class="fa-solid fa-user-plus text-2xl text-white"></i>
            </div>
            <h1 class="text-3xl font-bold text-white mb-2">Create Your Account</h1>
            <p class="text-slate-400">Join thousands of traders using Finance Dashboard</p>
          </div>
          
          <!-- Registration Form -->
          <form @submit.prevent="handleSubmit" class="space-y-6">
            <div>
              <label for="name" class="block text-sm font-medium text-gray-300 mb-2">Full Name</label>
              <input 
                type="text" 
                id="name" 
                v-model="form.name"
                required
                class="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent transition-all"
                placeholder="Enter your full name"
              >
            </div>
            
            <div>
              <label for="email" class="block text-sm font-medium text-gray-300 mb-2">Email Address</label>
              <input 
                type="email" 
                id="email" 
                v-model="form.email"
                required
                class="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent transition-all"
                placeholder="Enter your email address"
              >
            </div>
            
            <div>
              <label for="password" class="block text-sm font-medium text-gray-300 mb-2">Password</label>
              <input 
                type="password" 
                id="password" 
                v-model="form.password"
                required
                class="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent transition-all"
                placeholder="Create a strong password"
              >
              <p class="text-xs text-slate-500 mt-1">Must be at least 8 characters long</p>
            </div>
            
            <div>
              <label for="confirmPassword" class="block text-sm font-medium text-gray-300 mb-2">Confirm Password</label>
              <input 
                type="password" 
                id="confirmPassword" 
                v-model="form.confirmPassword"
                required
                class="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent transition-all"
                placeholder="Confirm your password"
              >
            </div>
            
            <!-- Terms and Conditions -->
            <div class="flex items-start space-x-3">
              <input 
                type="checkbox" 
                id="terms" 
                v-model="form.terms"
                required
                class="mt-1 w-4 h-4 text-green-600 bg-slate-700 border-slate-600 rounded focus:ring-green-500 focus:ring-2"
              >
              <label for="terms" class="text-sm text-slate-300">
                I agree to the 
                <a href="#" class="text-green-400 hover:text-green-300 underline">Terms of Service</a>
                and 
                <a href="#" class="text-green-400 hover:text-green-300 underline">Privacy Policy</a>
              </label>
            </div>
            
            <!-- Submit Button -->
            <button 
              type="submit"
              :disabled="authStore.isLoading"
              class="w-full bg-gradient-to-r from-green-500 to-green-600 hover:from-green-600 hover:to-green-700 disabled:from-green-800 disabled:to-green-900 text-white py-3 px-4 rounded-lg font-semibold transition-all transform hover:scale-105 shadow-lg"
            >
              <i class="fa-solid fa-rocket mr-2"></i>
              <span v-if="authStore.isLoading">Creating Account...</span>
              <span v-else>Create Account</span>
            </button>
          </form>
          
          <!-- Error Display -->
          <div v-if="authStore.error" class="mt-4 text-red-400 text-sm">
            {{ authStore.error }}
          </div>
          
          <!-- Login Link -->
          <div class="text-center mt-6">
            <p class="text-slate-400">
              Already have an account? 
              <button @click="showLoginModal = true" class="text-green-400 hover:text-green-300 font-medium">
                Sign in here
              </button>
            </p>
          </div>
        </div>
        
        <!-- Features Preview -->
        <div class="mt-8 grid grid-cols-1 gap-4">
          <div class="bg-slate-800 rounded-lg p-4 border border-slate-700">
            <div class="flex items-center space-x-3">
              <div class="w-8 h-8 bg-green-500/20 rounded-lg flex items-center justify-center">
                <i class="fa-solid fa-chart-line text-green-400 text-sm"></i>
              </div>
              <div>
                <h3 class="text-white font-medium">Advanced Backtesting</h3>
                <p class="text-slate-400 text-sm">Test strategies with historical data</p>
              </div>
            </div>
          </div>
          
          <div class="bg-slate-800 rounded-lg p-4 border border-slate-700">
            <div class="flex items-center space-x-3">
              <div class="w-8 h-8 bg-blue-500/20 rounded-lg flex items-center justify-center">
                <i class="fa-solid fa-brain text-blue-400 text-sm"></i>
              </div>
              <div>
                <h3 class="text-white font-medium">AI-Powered Insights</h3>
                <p class="text-slate-400 text-sm">Get intelligent trading recommendations</p>
              </div>
            </div>
          </div>
          
          <div class="bg-slate-800 rounded-lg p-4 border border-slate-700">
            <div class="flex items-center space-x-3">
              <div class="w-8 h-8 bg-purple-500/20 rounded-lg flex items-center justify-center">
                <i class="fa-solid fa-shield-halved text-purple-400 text-sm"></i>
              </div>
              <div>
                <h3 class="text-white font-medium">Risk Management</h3>
                <p class="text-slate-400 text-sm">Protect your capital with advanced tools</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>

    <!-- Footer -->
    <footer class="site-footer py-8 px-6 border-t border-slate-700 bg-slate-800">
      <div class="max-w-[85rem] mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex flex-col md:flex-row justify-between items-center gap-4">
          <div class="text-slate-400 text-sm">
            &copy; 2026 Finance Dashboard. All rights reserved.
            <span class="text-xs text-slate-500 ml-2">v1.0.0</span>
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
          <h3 class="text-xl font-bold text-white">Login to Finance Dashboard</h3>
          <button
            @click="showLoginModal = false"
            class="text-gray-400 hover:text-white"
          >
            <i class="fas fa-times"></i>
          </button>
        </div>

        <!-- Login Form -->
        <form @submit.prevent="handleLogin" class="space-y-4">
          <div>
            <label for="loginEmail" class="block text-sm font-medium text-gray-300 mb-1">
              Email
            </label>
            <input
              id="loginEmail"
              v-model="loginForm.email"
              type="email"
              required
              class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-white placeholder-gray-400 focus:outline-none focus:border-blue-500"
              placeholder="Enter your email"
            />
          </div>

          <div>
            <label for="loginPassword" class="block text-sm font-medium text-gray-300 mb-1">
              Password
            </label>
            <input
              id="loginPassword"
              v-model="loginForm.password"
              type="password"
              required
              class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-white placeholder-gray-400 focus:outline-none focus:border-blue-500"
              placeholder="Enter your password"
            />
          </div>

          <div class="flex items-center justify-between">
            <button
              type="submit"
              :disabled="authStore.isLoading"
              class="bg-green-600 hover:bg-green-700 disabled:bg-green-800 text-white px-4 py-2 rounded-md transition-colors"
            >
              <span v-if="authStore.isLoading">Loading...</span>
              <span v-else>Login</span>
            </button>
            <button 
              type="button" 
              @click="showLoginModal = false"
              class="text-green-400 hover:text-green-300 text-sm"
            >
              Create Account
            </button>
          </div>
        </form>

        <div v-if="authStore.error" class="mt-4 text-red-400 text-sm">
          {{ authStore.error }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import { useToastStore } from '../../stores/toast'

const router = useRouter()
const authStore = useAuthStore()
const toastStore = useToastStore()

const showLoginModal = ref(false)

const form = reactive({
  name: '',
  email: '',
  password: '',
  confirmPassword: '',
  terms: false
})

const loginForm = reactive({
  email: '',
  password: ''
})

async function handleSubmit() {
  if (form.password !== form.confirmPassword) {
    toastStore.show('Passwords do not match', 'error')
    return
  }
  
  if (form.password.length < 8) {
    toastStore.show('Password must be at least 8 characters long', 'error')
    return
  }
  
  if (!form.terms) {
    toastStore.show('You must agree to the Terms of Service and Privacy Policy', 'error')
    return
  }
  
  const ok = await authStore.createAccount(form.email, form.password, form.name)
  if (ok) {
    toastStore.show('Account created successfully!', 'success')
    router.push('/dashboard')
  } else {
    toastStore.show(authStore.error || 'Account creation failed', 'error')
  }
}

async function handleLogin() {
  const ok = await authStore.login(loginForm.email, loginForm.password)
  if (ok) {
    toastStore.show('Login successful!', 'success')
    showLoginModal.value = false
    router.push('/dashboard')
  } else {
    toastStore.show(authStore.error || 'Login failed', 'error')
  }
}
</script> 