<template>
  <div id="app" class="min-h-screen bg-slate-900">
    <!-- Toast Container -->
    <ToastContainer />
    
    <!-- Router View -->
    <router-view />
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useAuthStore } from '../stores/auth'
import ToastContainer from './ui/ToastContainer.vue'

const authStore = useAuthStore()

onMounted(async () => {
  console.log('[App] Initializing application...')
  
  // Check authentication status on app start
  await authStore.checkAuthStatus()
  
  console.log('[App] Application initialized')
})
</script>

<style>
/* Global styles */
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
    'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
    sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

#app {
  font-family: 'Inter', sans-serif;
}

/* Toast animations */
@keyframes toastSlideIn {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

@keyframes toastSlideOut {
  from {
    transform: translateX(0);
    opacity: 1;
  }
  to {
    transform: translateX(100%);
    opacity: 0;
  }
}

.toast-enter-active {
  animation: toastSlideIn 0.3s ease-out;
}

.toast-leave-active {
  animation: toastSlideOut 0.3s ease-in;
}
</style> 