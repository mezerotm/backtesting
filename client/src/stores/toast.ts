import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Toast, ToastType } from '@/types'

export const useToastStore = defineStore('toast', () => {
  const toasts = ref<Toast[]>([])
  const maxToasts = 5

  function show(message: string, type: ToastType = 'info', duration = 5000): number {
    const id = Date.now() + Math.random()
    const toast: Toast = {
      id,
      message,
      type,
      timestamp: new Date()
    }

    toasts.value.push(toast)

    // Remove oldest toast if we exceed max
    if (toasts.value.length > maxToasts) {
      toasts.value.shift()
    }

    // Auto remove after duration
    if (duration > 0) {
      setTimeout(() => {
        remove(id)
      }, duration)
    }

    return id
  }

  function remove(id: number): void {
    const index = toasts.value.findIndex(toast => toast.id === id)
    if (index !== -1) {
      toasts.value.splice(index, 1)
    }
  }

  function removeAll(): void {
    toasts.value = []
  }

  function removeByType(type: ToastType): void {
    toasts.value = toasts.value.filter(toast => toast.type !== type)
  }

  return {
    toasts,
    show,
    remove,
    removeAll,
    removeByType
  }
}) 