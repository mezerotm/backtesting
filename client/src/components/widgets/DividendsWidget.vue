<template>
  <!-- Dividends Action Bar (only shown when expanded) -->
  <div 
    v-show="widgetStore.showDividendsActionBar"
    class="bg-slate-800 rounded-xl shadow flex flex-wrap gap-3 justify-between items-center w-full p-6 mb-2 widget-action-bar"
  >
    <h2 class="text-lg font-bold text-white flex items-center gap-2 cursor-pointer select-none" @click.stop="widgetStore.toggleWidget('dividends')">
      Dividends
      <button 
        @click.stop="widgetStore.toggleWidget('dividends')"
        class="ml-2 text-slate-400 hover:text-blue-400 focus:outline-none transition-transform minimize-btn"
        title="Minimize Dividends"
      >
        <i :class="widgetStore.getMinimizeIcon('dividends')"></i>
      </button>
    </h2>
    <div class="flex items-center gap-4">
      <!-- No action buttons for dividends -->
    </div>
  </div>

  <!-- Dividends Card -->
  <div class="bg-slate-800 rounded-xl shadow-sm p-6 w-full" :class="{ 'mt-2': widgetStore.showDividendsActionBar }">
    <!-- Collapsed Header (shown when minimized) -->
    <div v-show="widgetStore.isDividendsMinimized" class="flex justify-between items-center">
      <h2 class="text-lg font-bold text-white flex items-center gap-2 cursor-pointer select-none" @click.stop="widgetStore.toggleWidget('dividends')">
        Dividends
        <button 
          @click.stop="widgetStore.toggleWidget('dividends')"
          class="ml-2 text-slate-400 hover:text-blue-400 focus:outline-none transition-transform minimize-btn"
          title="Expand Dividends"
        >
          <i :class="widgetStore.getMinimizeIcon('dividends')"></i>
        </button>
      </h2>
    </div>

    <!-- Content (hidden when minimized) -->
    <div v-show="!widgetStore.isDividendsMinimized" class="widget-content">
      <div class="mb-4 text-gray-400">
        Track your received dividends here.
      </div>
      
      <!-- Received Dividends Section -->
      <div class="mb-6">
        <h3 class="text-md font-semibold text-white mb-1">Received Dividends</h3>
        <div class="overflow-x-auto overflow-y-auto max-h-96">
          <table class="w-full text-sm">
            <thead class="bg-slate-800 sticky top-0 z-10">
              <tr class="border-b border-slate-700">
                <th class="text-left px-3 py-2 text-gray-400">Symbol</th>
                <th class="text-left px-3 py-2 text-gray-400">Amount</th>
                <th class="text-left px-3 py-2 text-gray-400">Record Date</th>
                <th class="text-left px-3 py-2 text-gray-400">Payable Date</th>
                <th class="text-left px-3 py-2 text-gray-400">Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="isLoading">
                <td colspan="5" class="text-center text-gray-400 py-4">
                  <div class="flex justify-center items-center space-x-2">
                    <div class="animate-spin inline-block w-4 h-4 border-[2px] border-current border-t-transparent text-blue-600 rounded-full" role="status" aria-label="loading">
                      <span class="sr-only">Loading dividends...</span>
                    </div>
                    <span>Loading dividends...</span>
                  </div>
                </td>
              </tr>
              <tr v-else-if="dividends.length === 0">
                <td colspan="5" class="text-center text-gray-400 py-4">No received dividends.</td>
              </tr>
              <tr v-for="dividend in dividends" :key="dividend.id" class="hover:bg-slate-700">
                <td class="px-3 py-2 text-sm text-white">{{ dividend.symbol }}</td>
                <td class="px-3 py-2 text-sm text-green-400">{{ formatCurrency(dividend.amount) }}</td>
                <td class="px-3 py-2 text-sm text-gray-300">{{ formatDate(dividend.record_date) }}</td>
                <td class="px-3 py-2 text-sm text-gray-300">{{ formatDate(dividend.payable_date) }}</td>
                <td class="px-3 py-2 text-sm text-gray-300">
                  <div class="flex gap-2">
                    <button
                      @click="editDividend(dividend)"
                      class="text-blue-400 hover:text-blue-300"
                      title="Edit Dividend"
                    >
                      <i class="fas fa-edit"></i>
                    </button>
                    <button
                      @click="deleteDividend(dividend)"
                      class="text-red-400 hover:text-red-300"
                      title="Delete Dividend"
                    >
                      <i class="fas fa-trash"></i>
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>

  <!-- Add/Edit Dividend Modal -->
  <div 
    v-if="showDividendModal"
    class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-60"
    @click="showDividendModal = false"
  >
    <div 
      class="bg-slate-800 rounded-lg shadow-lg w-full max-w-md p-6 mx-4"
      @click.stop
    >
      <h3 class="text-xl font-bold text-white mb-4">{{ editingDividend ? 'Edit Dividend' : 'Add Dividend' }}</h3>
      <form @submit.prevent="saveDividend" class="space-y-4">
        <input type="hidden" v-model="dividendForm.id">
        <div>
          <label class="block text-sm text-gray-300 mb-1" for="dividendSymbol">Symbol</label>
          <input 
            type="text" 
            id="dividendSymbol" 
            v-model="dividendForm.symbol"
            class="w-full p-2 rounded bg-slate-700 text-white" 
            required 
            autocomplete="off" 
            style="text-transform:uppercase; letter-spacing:0.5px;"
          >
        </div>
        <div>
          <label class="block text-sm text-gray-300 mb-1" for="dividendAmount">Amount</label>
          <input 
            type="number" 
            id="dividendAmount" 
            v-model="dividendForm.amount"
            class="w-full p-2 rounded bg-slate-700 text-white" 
            step="any" 
            required
          >
        </div>
        <div>
          <label class="block text-sm text-gray-300 mb-1" for="dividendRecordDate">Record Date</label>
          <input 
            type="date" 
            id="dividendRecordDate" 
            v-model="dividendForm.record_date"
            class="w-full p-2 rounded bg-slate-700 text-white" 
            required
          >
        </div>
        <div>
          <label class="block text-sm text-gray-300 mb-1" for="dividendPayableDate">Payable Date</label>
          <input 
            type="date" 
            id="dividendPayableDate" 
            v-model="dividendForm.payable_date"
            class="w-full p-2 rounded bg-slate-700 text-white" 
            required
          >
        </div>
        <div class="flex justify-end gap-2 mt-4">
          <button 
            type="button" 
            @click="showDividendModal = false"
            class="py-2 px-4 rounded bg-gray-600 text-white hover:bg-gray-500"
          >
            Cancel
          </button>
          <button 
            type="submit" 
            class="py-2 px-4 rounded bg-blue-600 text-white hover:bg-blue-700"
          >
            Save
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useToastStore } from '../../stores/toast'
import { useWidgetStore } from '../../stores/widgets'

const toastStore = useToastStore()
const widgetStore = useWidgetStore()

const showDividendModal = ref(false)
const isLoading = ref(false)
const dividends = ref([])
const editingDividend = ref(null)

const dividendForm = ref({
  id: null,
  symbol: '',
  amount: 0,
  record_date: '',
  payable_date: ''
})

onMounted(async () => {
  await loadDividends()
})

async function loadDividends() {
  isLoading.value = true
  try {
    // TODO: Replace with real API call
    await new Promise(resolve => setTimeout(resolve, 1000))
    dividends.value = [
      {
        id: 1,
        symbol: 'AAPL',
        amount: 0.24,
        record_date: '2024-12-15',
        payable_date: '2024-12-20'
      },
      {
        id: 2,
        symbol: 'MSFT',
        amount: 0.75,
        record_date: '2024-12-10',
        payable_date: '2024-12-15'
      }
    ]
  } catch (error) {
    toastStore.show('Failed to load dividends', 'error')
  } finally {
    isLoading.value = false
  }
}

function formatCurrency(value) {
  if (!value && value !== 0) return '$0.00'
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD'
  }).format(value)
}

function formatDate(date) {
  if (!date) return ''
  return new Date(date).toLocaleDateString()
}

function editDividend(dividend) {
  editingDividend.value = dividend
  dividendForm.value = { ...dividend }
  showDividendModal.value = true
}

async function saveDividend() {
  try {
    // TODO: Replace with real API call
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    if (editingDividend.value) {
      // Update existing dividend
      const index = dividends.value.findIndex(d => d.id === editingDividend.value.id)
      if (index !== -1) {
        dividends.value[index] = { ...dividendForm.value }
      }
    } else {
      // Add new dividend
      const newDividend = {
        ...dividendForm.value,
        id: Date.now()
      }
      dividends.value.unshift(newDividend)
    }
    
    showDividendModal.value = false
    resetForm()
    toastStore.show(`Dividend ${editingDividend.value ? 'updated' : 'added'} successfully`, 'success')
  } catch (error) {
    toastStore.show('Failed to save dividend', 'error')
  }
}

async function deleteDividend(dividend) {
  if (confirm(`Are you sure you want to delete this dividend for ${dividend.symbol}?`)) {
    try {
      // TODO: Replace with real API call
      dividends.value = dividends.value.filter(d => d.id !== dividend.id)
      toastStore.show('Dividend deleted successfully', 'success')
    } catch (error) {
      toastStore.show('Failed to delete dividend', 'error')
    }
  }
}

function resetForm() {
  dividendForm.value = {
    id: null,
    symbol: '',
    amount: 0,
    record_date: '',
    payable_date: ''
  }
  editingDividend.value = null
}
</script> 