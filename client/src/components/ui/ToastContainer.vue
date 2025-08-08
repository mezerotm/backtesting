<template>
  <div class="fixed top-20 right-4 z-50 space-y-2">
    <TransitionGroup name="toast">
      <div
        v-for="toast in toastStore.toasts"
        :key="toast.id"
        :class="getToastClasses(toast.type)"
        class="p-4 rounded-lg shadow-lg max-w-sm"
      >
        <div class="flex items-start justify-between">
          <div class="flex-1">
            <p class="text-sm font-medium">{{ toast.message }}</p>
          </div>
          <button
            @click="toastStore.remove(toast.id)"
            class="ml-4 text-current opacity-70 hover:opacity-100"
          >
            <i class="fas fa-times"></i>
          </button>
        </div>
      </div>
    </TransitionGroup>
  </div>
</template>

<script setup>
import { useToastStore } from '../../stores/toast'

const toastStore = useToastStore()

function getToastClasses(type) {
  const baseClasses = 'text-white'
  
  switch (type) {
    case 'success':
      return `${baseClasses} bg-green-600`
    case 'error':
      return `${baseClasses} bg-red-600`
    case 'warning':
      return `${baseClasses} bg-yellow-600`
    case 'info':
    default:
      return `${baseClasses} bg-blue-600`
  }
}
</script> 