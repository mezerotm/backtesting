import { createApp } from 'vue'
import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { createPinia } from 'pinia'
import { useAuthStore } from './stores/auth'

// Import components
import App from './components/App.vue'
import LandingPage from './components/pages/LandingPage.vue'
import DashboardPage from './components/pages/DashboardPage.vue'
import CreateAccountPage from './components/pages/CreateAccountPage.vue'
import NotFoundPage from './components/pages/NotFoundPage.vue'
import ServerDownPage from './components/pages/ServerDownPage.vue'

// Define routes with proper typing
const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'landing',
    component: LandingPage,
    meta: { requiresAuth: false }
  },
  {
    path: '/landing.html',
    name: 'landing-alt',
    component: LandingPage,
    meta: { requiresAuth: false }
  },
  {
    path: '/create-account',
    name: 'create-account',
    component: CreateAccountPage,
    meta: { requiresAuth: false }
  },
  {
    path: '/create-account.html',
    name: 'create-account-alt',
    component: CreateAccountPage,
    meta: { requiresAuth: false }
  },
  {
    path: '/dashboard',
    name: 'dashboard',
    component: DashboardPage,
    meta: { requiresAuth: true }
  },
  {
    path: '/dashboard.html',
    name: 'dashboard-alt',
    component: DashboardPage,
    meta: { requiresAuth: true }
  },
  {
    path: '/server-down',
    name: 'server-down',
    component: ServerDownPage,
    meta: { requiresAuth: false }
  },
  {
    path: '/server-down.html',
    name: 'server-down-alt',
    component: ServerDownPage,
    meta: { requiresAuth: false }
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: NotFoundPage,
    meta: { requiresAuth: false }
  }
]

// Create router
const router = createRouter({
  history: createWebHistory(),
  routes
})

// Navigation guard for authentication
router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()
  
  console.log('[Router] Navigation guard triggered', {
    to: to.name,
    from: from.name,
    isAuthenticated: authStore.isAuthenticated,
    requiresAuth: to.meta.requiresAuth
  })

  // First check authentication status
  if (!authStore.isAuthenticated) {
    try {
      await authStore.checkAuthStatus()
    } catch (err) {
      console.error('[Router] Auth check failed:', err)
    }
  }
  
  // Check if route requires authentication
  if (to.meta.requiresAuth) {
    if (!authStore.isAuthenticated) {
      console.log('[Router] Route requires auth, redirecting to landing')
      next({ name: 'landing' })
      return
    }
  }
  
  // If user is authenticated and trying to access landing page, redirect to dashboard
  if (authStore.isAuthenticated && to.name === 'landing') {
    console.log('[Router] User authenticated, redirecting to dashboard')
    next({ name: 'dashboard' })
    return
  }
  
  console.log('[Router] Proceeding to route:', to.name)
  next()
})

// Create Pinia store
const pinia = createPinia()

// Create Vue app
const app = createApp(App)

// Use plugins
app.use(pinia)  // Important: Initialize Pinia before using it in router
app.use(router)

// Global error handler
app.config.errorHandler = (err: unknown, _vm: any, info: string) => {
  console.error('[Vue Error]', err, info)
  // You can add toast notification here
}

// Mount app
app.mount('#app')

// Export for debugging
declare global {
  interface Window {
    VueApp: typeof app
    VueRouter: typeof router
  }
}

window.VueApp = app
window.VueRouter = router 