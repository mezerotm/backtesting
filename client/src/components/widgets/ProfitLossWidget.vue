<template>
  <!-- Profit/Loss Action Bar (only shown when expanded) -->
  <div 
    v-show="widgetStore.showProfitLossActionBar"
    class="bg-slate-800 rounded-xl shadow flex flex-wrap gap-3 justify-between items-center w-full p-6 mb-2 widget-action-bar"
  >
    <h2 class="text-lg font-bold text-white flex items-center gap-2 cursor-pointer select-none" @click.stop="widgetStore.toggleWidget('profitLoss')">
      Profit/Loss
      <button 
        @click.stop="widgetStore.toggleWidget('profitLoss')"
        class="ml-2 text-slate-400 hover:text-blue-400 focus:outline-none transition-transform minimize-btn"
        title="Minimize Profit/Loss"
      >
        <i :class="widgetStore.getMinimizeIcon('profitLoss')"></i>
      </button>
    </h2>
    <div class="flex items-center gap-4">
      <!-- No action buttons for profit/loss -->
    </div>
  </div>

  <!-- Profit/Loss Card -->
  <div class="bg-slate-800 rounded-xl shadow-sm p-6 w-full" :class="{ 'mt-2': widgetStore.showProfitLossActionBar }">
    <!-- Collapsed Header (shown when minimized) -->
    <div v-show="widgetStore.isProfitLossMinimized" class="flex justify-between items-center">
      <h2 class="text-lg font-bold text-white flex items-center gap-2 cursor-pointer select-none" @click.stop="widgetStore.toggleWidget('profitLoss')">
        Profit/Loss
        <button 
          @click.stop="widgetStore.toggleWidget('profitLoss')"
          class="ml-2 text-slate-400 hover:text-blue-400 focus:outline-none transition-transform minimize-btn"
          title="Expand Profit/Loss"
        >
          <i :class="widgetStore.getMinimizeIcon('profitLoss')"></i>
        </button>
      </h2>
    </div>

    <!-- Content (hidden when minimized) -->
    <div v-show="!widgetStore.isProfitLossMinimized" class="widget-content">
      <div class="mb-4 text-gray-400">
        Track your realized and unrealized profit/loss here.
      </div>
      
      <!-- Summary Section -->
      <div class="mb-6">
        <h3 class="text-md font-semibold text-white mb-3">Summary</h3>
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div class="text-center">
            <div class="text-2xl font-bold" :class="getPLClass(summary.total)">{{ formatCurrency(summary.total) }}</div>
            <div class="text-xs text-gray-400">Total P/L</div>
          </div>
          <div class="text-center">
            <div class="text-2xl font-bold text-green-400">{{ formatCurrency(summary.unrealized) }}</div>
            <div class="text-xs text-gray-400">Unrealized</div>
          </div>
          <div class="text-center">
            <div class="text-2xl font-bold text-blue-400">{{ formatCurrency(summary.realized) }}</div>
            <div class="text-xs text-gray-400">Realized</div>
          </div>
        </div>
      </div>

      <!-- Chart Section -->
      <div class="mb-6">
        <div class="flex flex-wrap gap-2 justify-between items-center mb-3">
          <h3 class="text-md font-semibold text-white">Performance Chart</h3>
          <div class="flex flex-wrap gap-1">
            <button 
              v-for="period in timeRanges" 
              :key="period.value"
              @click="selectedTimeRange = period.value"
              :class="[
                'time-btn px-3 py-1 text-xs rounded transition-colors',
                selectedTimeRange === period.value
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-600 text-gray-300 hover:bg-slate-500'
              ]"
            >
              {{ period.label }}
            </button>
          </div>
        </div>
        <div class="bg-slate-700 rounded-lg p-4 h-48">
          <div class="h-full flex items-center justify-center">
            <div class="text-gray-400">Performance chart coming soon...</div>
          </div>
        </div>
      </div>

      <!-- P/L Details Table -->
      <div class="pb-6">
        <h3 class="text-md font-semibold text-white mb-1">P/L Details</h3>
        <div class="overflow-x-auto overflow-y-auto" style="max-height: 250px; border: 1px solid #374151; border-radius: 0.375rem; margin-bottom: 8px;">
          <table class="min-w-full divide-y divide-slate-700 text-sm">
            <thead class="bg-slate-800 sticky top-0 z-10">
              <tr>
                <th class="px-3 py-2 text-left text-xs font-medium text-gray-300 uppercase">Symbol</th>
                <th class="px-3 py-2 text-left text-xs font-medium text-gray-300 uppercase">Type</th>
                <th class="px-3 py-2 text-left text-xs font-medium text-gray-300 uppercase">Amount</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="isLoading">
                <td colspan="3" class="text-center text-gray-400 py-4">
                  <div class="flex justify-center items-center space-x-2">
                    <div class="animate-spin inline-block w-4 h-4 border-[2px] border-current border-t-transparent text-blue-600 rounded-full" role="status" aria-label="loading">
                      <span class="sr-only">Loading P/L data...</span>
                    </div>
                    <span>Loading P/L data...</span>
                  </div>
                </td>
              </tr>
              <tr v-else-if="profitLossDetails.length === 0">
                <td colspan="3" class="text-center text-gray-400 py-4">No P/L data.</td>
              </tr>
              <tr v-for="pl in profitLossDetails" :key="pl.symbol" class="hover:bg-slate-600">
                <td class="px-3 py-2 text-white">{{ pl.symbol }}</td>
                <td class="px-3 py-2 text-gray-300">{{ pl.type }}</td>
                <td class="px-3 py-2" :class="getPLClass(pl.amount)">
                  {{ formatCurrency(pl.amount) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useToastStore } from '../../stores/toast'
import { useWidgetStore } from '../../stores/widgets'

const toastStore = useToastStore()
const widgetStore = useWidgetStore()

const isLoading = ref(false)
const selectedTimeRange = ref('YTD')

const timeRanges = [
  { value: '1W', label: '1W' },
  { value: '1M', label: '1M' },
  { value: '3M', label: '3M' },
  { value: 'YTD', label: 'YTD' },
  { value: 'MAX', label: 'MAX' }
]

const summary = ref({
  total: 0,
  unrealized: 0,
  realized: 0
})

const profitLossDetails = ref([])

onMounted(async () => {
  await loadProfitLossData()
})

async function loadProfitLossData() {
  isLoading.value = true
  try {
    // TODO: Replace with real API call
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    // Mock data
    summary.value = {
      total: 1250.50,
      unrealized: 850.25,
      realized: 400.25
    }
    
    profitLossDetails.value = [
      {
        symbol: 'AAPL',
        type: 'Unrealized',
        amount: 250.75
      },
      {
        symbol: 'NVDA',
        type: 'Unrealized',
        amount: 599.50
      },
      {
        symbol: 'TSLA',
        type: 'Realized',
        amount: 400.25
      }
    ]
  } catch (error) {
    toastStore.show('Failed to load P/L data', 'error')
  } finally {
    isLoading.value = false
  }
}

function getPLClass(value) {
  if (!value && value !== 0) return 'text-gray-400'
  return value >= 0 ? 'text-green-400' : 'text-red-400'
}

function formatCurrency(value) {
  if (!value && value !== 0) return '$0.00'
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD'
  }).format(value)
}
</script> 