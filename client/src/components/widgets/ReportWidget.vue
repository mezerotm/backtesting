<template>
  <!-- Report Action Bar (only shown when expanded) -->
  <div 
    v-show="widgetStore.showReportsActionBar"
    class="bg-slate-800 rounded-xl shadow flex justify-between items-center w-full p-6 mb-2 widget-action-bar"
  >
    <h2 class="text-lg font-bold text-white flex items-center gap-2">
      Reports
      <button 
        @click="widgetStore.toggleWidget('reports')"
        class="ml-2 text-slate-400 hover:text-blue-400 focus:outline-none transition-transform minimize-btn"
        title="Minimize Reports"
      >
        <i :class="widgetStore.getMinimizeIcon('reports')"></i>
      </button>
    </h2>
    <div class="flex items-center gap-4">
      <button 
        @click="cleanResults"
        class="py-2 px-4 rounded-lg text-white bg-red-600 hover:bg-red-700 flex items-center gap-2"
      >
        <i class="fa-solid fa-trash"></i> Clean Results
      </button>
      <button 
        @click="showGenerateReportModal = true"
        class="primary-btn py-2 px-4 rounded-lg text-white bg-blue-600 hover:bg-blue-700 flex items-center gap-2"
      >
        <i class="fa-solid fa-plus"></i> Generate Report
      </button>
    </div>
  </div>

  <!-- Reports Card -->
  <div class="bg-slate-800 rounded-xl shadow-sm p-6 w-full" :class="{ 'mt-2': widgetStore.showReportsActionBar }">
    <!-- Collapsed Header (shown when minimized) -->
    <div v-show="widgetStore.isReportsMinimized" class="flex justify-between items-center">
      <h2 class="text-lg font-bold text-white flex items-center gap-2">
        Reports
        <button 
          @click="widgetStore.toggleWidget('reports')"
          class="ml-2 text-slate-400 hover:text-blue-400 focus:outline-none transition-transform minimize-btn"
          title="Expand Reports"
        >
          <i :class="widgetStore.getMinimizeIcon('reports')"></i>
        </button>
      </h2>
    </div>

    <!-- Content (hidden when minimized) -->
    <div v-show="!widgetStore.isReportsMinimized" class="widget-content">
      <div class="flex flex-col lg:flex-row gap-4 w-full items-start">
        <!-- Filters Section -->
        <div class="bg-slate-800 border border-slate-700 rounded-xl shadow flex flex-col gap-3 p-6 w-full lg:max-w-sm lg:flex-none h-[750px]">
          <div class="flex items-center gap-2 mb-4">
            <i class="fa-solid fa-filter text-blue-400"></i>
            <h3 class="text-lg font-semibold text-white">Filters</h3>
          </div>
          <div class="flex flex-col gap-4">
            <div>
              <label for="reportType" class="block text-sm font-medium mb-2 text-gray-300">Report Type</label>
              <select 
                id="reportType" 
                v-model="filters.reportType"
                class="p-3 block w-full border border-gray-600 bg-slate-900 text-white rounded-lg text-sm focus:border-blue-500 focus:ring-blue-500 appearance-none"
              >
                <option value="all">All Reports</option>
                <option value="comparison">Comparison Reports</option>
                <option value="backtest">Backtest Reports</option>
                <option value="market">Market Check</option>
                <option value="finance">Finance Report</option>
              </select>
            </div>
            <div>
              <label for="symbol" class="block text-sm font-medium mb-2 text-gray-300">Symbol</label>
              <select 
                id="symbol" 
                v-model="filters.symbol"
                class="p-3 block w-full border border-gray-600 bg-slate-900 text-white rounded-lg text-sm focus:border-blue-500 focus:ring-blue-500 appearance-none"
              >
                <option value="all">All Symbols</option>
                <option v-for="symbol in availableSymbols" :key="symbol" :value="symbol">{{ symbol }}</option>
              </select>
            </div>
            <div>
              <label for="strategy" class="block text-sm font-medium mb-2 text-gray-300">Strategy</label>
              <select 
                id="strategy" 
                v-model="filters.strategy"
                class="p-3 block w-full border border-gray-600 bg-slate-900 text-white rounded-lg text-sm focus:border-blue-500 focus:ring-blue-500 appearance-none"
              >
                <option value="all">All Strategies</option>
                <option v-for="strategy in availableStrategies" :key="strategy" :value="strategy">{{ strategy }}</option>
              </select>
            </div>
            <div>
              <label for="startDate" class="block text-xs text-gray-300 mb-1">Start Date</label>
              <input 
                type="date" 
                id="startDate" 
                v-model="filters.startDate"
                class="py-2 px-3 block w-full border border-gray-600 bg-slate-900 text-white rounded-lg text-sm focus:border-blue-500 focus:ring-blue-500"
              >
            </div>
            <div>
              <label for="endDate" class="block text-xs text-gray-300 mb-1">End Date</label>
              <input 
                type="date" 
                id="endDate" 
                v-model="filters.endDate"
                class="py-2 px-3 block w-full border border-gray-600 bg-slate-900 text-white rounded-lg text-sm focus:border-blue-500 focus:ring-blue-500"
              >
            </div>
            <div class="flex flex-col gap-2 mt-2">
              <button 
                @click="resetFilters"
                class="reset-btn py-2 px-4 rounded-lg border border-gray-600 bg-slate-800 text-white hover:bg-slate-600 flex items-center justify-center gap-2"
              >
                <i class="fa-solid fa-rotate"></i> Reset
              </button>
              <button 
                @click="applyFilters"
                class="primary-btn py-2 px-4 rounded-lg bg-blue-600 text-white hover:bg-blue-700 flex items-center justify-center gap-2"
              >
                <i class="fa-solid fa-filter"></i> Apply Filters
              </button>
            </div>
          </div>
        </div>

        <!-- Reports Table Section -->
        <div class="bg-slate-800 border border-slate-700 rounded-xl shadow flex flex-col flex-1 min-w-0 p-6 w-full h-[750px]">
          <div class="flex justify-between items-center mb-4">
            <div class="flex items-center gap-2">
              <i class="fa-solid fa-table text-blue-400"></i>
              <h2 class="text-lg font-bold text-white">Available Reports</h2>
            </div>
            <div class="text-sm text-gray-500">
              Last updated: <span>{{ formatLastUpdated() }}</span>
            </div>
          </div>
          <div class="overflow-x-auto overflow-y-auto h-full">
            <table class="min-w-0 w-full table-auto divide-y divide-slate-700">
              <thead class="bg-slate-800 sticky top-0 z-10">
                <tr>
                  <th scope="col" class="px-3 py-3 text-start text-xs font-medium text-gray-300 uppercase truncate">Actions</th>
                  <th scope="col" class="px-3 py-3 text-start text-xs font-medium text-gray-300 uppercase truncate">Symbol</th>
                  <th scope="col" class="px-3 py-3 text-start text-xs font-medium text-gray-300 uppercase truncate">Report Type</th>
                  <th scope="col" class="px-3 py-3 text-start text-xs font-medium text-gray-300 uppercase truncate">Strategy</th>
                  <th scope="col" class="px-3 py-3 text-start text-xs font-medium text-gray-300 uppercase truncate">Timeframe</th>
                  <th scope="col" class="px-3 py-3 text-start text-xs font-medium text-gray-300 uppercase truncate">Date Range</th>
                  <th scope="col" class="px-3 py-3 text-start text-xs font-medium text-gray-300 uppercase truncate">
                    Created
                    <i class="fa-solid fa-arrow-up-short-wide ml-1 text-blue-400" title="Sorted by newest first"></i>
                  </th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-700">
                <tr v-if="isLoading">
                  <td colspan="7" class="px-3 py-3 text-center text-gray-400 truncate">
                    <div class="flex justify-center items-center space-x-2">
                      <div class="animate-spin inline-block w-4 h-4 border-[2px] border-current border-t-transparent text-blue-600 rounded-full" role="status" aria-label="loading">
                        <span class="sr-only">Loading reports...</span>
                      </div>
                      <span>Loading reports...</span>
                    </div>
                  </td>
                </tr>
                <tr v-else-if="filteredReports.length === 0">
                  <td colspan="7" class="px-3 py-3 text-center text-gray-400 truncate">
                    No reports found.
                  </td>
                </tr>
                <tr v-for="report in filteredReports" :key="report.id" class="hover:bg-slate-700">
                  <td class="px-3 py-3 text-sm text-gray-300">
                    <div class="flex gap-2">
                      <button 
                        @click="viewReport(report)"
                        class="text-blue-400 hover:text-blue-300"
                        title="View Report"
                      >
                        <i class="fas fa-eye"></i>
                      </button>
                      <button 
                        @click="deleteReport(report)"
                        class="text-red-400 hover:text-red-300"
                        title="Delete Report"
                      >
                        <i class="fas fa-trash"></i>
                      </button>
                    </div>
                  </td>
                  <td class="px-3 py-3 text-sm text-white truncate">{{ report.symbol }}</td>
                  <td class="px-3 py-3 text-sm text-gray-300 truncate">{{ report.reportType }}</td>
                  <td class="px-3 py-3 text-sm text-gray-300 truncate">{{ report.strategy }}</td>
                  <td class="px-3 py-3 text-sm text-gray-300 truncate">{{ report.timeframe }}</td>
                  <td class="px-3 py-3 text-sm text-gray-300 truncate">{{ report.dateRange }}</td>
                  <td class="px-3 py-3 text-sm text-gray-300 truncate">{{ formatDate(report.created) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Modal for Report Generation -->
  <div 
    v-if="showGenerateReportModal"
    class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-60"
    @click="showGenerateReportModal = false"
  >
    <div 
      class="bg-slate-800 rounded-lg shadow-lg w-full max-w-md p-6 mx-4"
      @click.stop
    >
      <h3 class="text-xl font-bold text-white mb-4">Generate Report</h3>
      <form @submit.prevent="generateReport" class="space-y-4">
        <div>
          <label class="block text-sm text-gray-300 mb-1" for="genReportType">Report Type</label>
          <select 
            id="genReportType" 
            v-model="newReport.reportType"
            class="w-full p-2 rounded bg-slate-700 text-white" 
            required
          >
            <option value="market">Market Check</option>
            <option value="finance">Finance</option>
            <option value="backtest" disabled>Backtest</option>
            <option value="comparison" disabled>Comparison</option>
          </select>
        </div>
        <div>
          <label class="block text-sm text-gray-300 mb-1" for="genSymbol">Symbol</label>
          <input 
            type="text" 
            id="genSymbol" 
            v-model="newReport.symbol"
            class="w-full p-2 rounded bg-slate-700 text-white" 
            autocomplete="off" 
            style="text-transform:uppercase; letter-spacing:0.5px;"
          >
        </div>
        <div>
          <label class="block text-sm text-gray-300 mb-1" for="genStrategy">Strategy</label>
          <input 
            type="text" 
            id="genStrategy" 
            v-model="newReport.strategy"
            class="w-full p-2 rounded bg-slate-700 text-white"
          >
        </div>
        <div>
          <label class="block text-sm text-gray-300 mb-1" for="genTimeframe">Timeframe</label>
          <input 
            type="text" 
            id="genTimeframe" 
            v-model="newReport.timeframe"
            class="w-full p-2 rounded bg-slate-700 text-white"
          >
        </div>
        <div>
          <label class="block text-sm text-gray-300 mb-1" for="genStartDate">Start Date</label>
          <input 
            type="date" 
            id="genStartDate" 
            v-model="newReport.startDate"
            class="w-full p-2 rounded bg-slate-700 text-white"
          >
        </div>
        <div>
          <label class="block text-sm text-gray-300 mb-1" for="genEndDate">End Date</label>
          <input 
            type="date" 
            id="genEndDate" 
            v-model="newReport.endDate"
            class="w-full p-2 rounded bg-slate-700 text-white"
          >
        </div>
        <div class="flex justify-end gap-2 mt-4">
          <button 
            type="button" 
            @click="showGenerateReportModal = false"
            class="py-2 px-4 rounded bg-gray-600 text-white hover:bg-gray-500"
          >
            Cancel
          </button>
          <button 
            type="submit" 
            class="py-2 px-4 rounded bg-green-600 text-white hover:bg-green-700"
          >
            Generate
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useToastStore } from '../../stores/toast'
import { useWidgetStore } from '../../stores/widgets'

const toastStore = useToastStore()
const widgetStore = useWidgetStore()

const showGenerateReportModal = ref(false)
const isLoading = ref(false)

const filters = ref({
  reportType: 'all',
  symbol: 'all',
  strategy: 'all',
  startDate: '',
  endDate: ''
})

const newReport = ref({
  reportType: 'market',
  symbol: '',
  strategy: '',
  timeframe: '',
  startDate: '',
  endDate: ''
})

// Mock data - replace with real API calls
const reports = ref([])
const availableSymbols = ref(['AAPL', 'NVDA', 'TSLA', 'MSFT', 'GOOGL'])
const availableStrategies = ref(['SMA', 'EMA', 'RSI', 'MACD', 'Buy & Hold'])

const filteredReports = computed(() => {
  return reports.value.filter(report => {
    if (filters.value.reportType !== 'all' && report.reportType !== filters.value.reportType) return false
    if (filters.value.symbol !== 'all' && report.symbol !== filters.value.symbol) return false
    if (filters.value.strategy !== 'all' && report.strategy !== filters.value.strategy) return false
    return true
  })
})

onMounted(async () => {
  await loadReports()
})

async function loadReports() {
  isLoading.value = true
  try {
    // TODO: Replace with real API call
    await new Promise(resolve => setTimeout(resolve, 1000))
    reports.value = [
      {
        id: 1,
        symbol: 'NVDA',
        reportType: 'Market Check',
        strategy: 'SMA',
        timeframe: 'Daily',
        dateRange: '2024-01-01 to 2024-12-31',
        created: new Date('2024-12-15')
      },
      {
        id: 2,
        symbol: 'AAPL',
        reportType: 'Finance',
        strategy: 'Buy & Hold',
        timeframe: 'Weekly',
        dateRange: '2024-06-01 to 2024-12-31',
        created: new Date('2024-12-10')
      }
    ]
  } catch (error) {
    toastStore.show('Failed to load reports', 'error')
  } finally {
    isLoading.value = false
  }
}

function resetFilters() {
  filters.value = {
    reportType: 'all',
    symbol: 'all',
    strategy: 'all',
    startDate: '',
    endDate: ''
  }
}

function applyFilters() {
  // Filters are applied automatically via computed property
  toastStore.show('Filters applied', 'success')
}

async function generateReport() {
  try {
    // TODO: Replace with real API call
    await new Promise(resolve => setTimeout(resolve, 2000))
    
    const report = {
      id: Date.now(),
      symbol: newReport.value.symbol.toUpperCase(),
      reportType: newReport.value.reportType,
      strategy: newReport.value.strategy,
      timeframe: newReport.value.timeframe,
      dateRange: `${newReport.value.startDate} to ${newReport.value.endDate}`,
      created: new Date()
    }
    
    reports.value.unshift(report)
    showGenerateReportModal.value = false
    
    // Reset form
    newReport.value = {
      reportType: 'market',
      symbol: '',
      strategy: '',
      timeframe: '',
      startDate: '',
      endDate: ''
    }
    
    toastStore.show('Report generated successfully', 'success')
  } catch (error) {
    toastStore.show('Failed to generate report', 'error')
  }
}

function viewReport(report) {
  // TODO: Implement report viewing
  console.log('View report:', report)
  toastStore.show(`Opening ${report.reportType} for ${report.symbol}`, 'info')
}

async function deleteReport(report) {
  if (confirm(`Are you sure you want to delete this ${report.reportType} report for ${report.symbol}?`)) {
    try {
      // TODO: Replace with real API call
      reports.value = reports.value.filter(r => r.id !== report.id)
      toastStore.show('Report deleted successfully', 'success')
    } catch (error) {
      toastStore.show('Failed to delete report', 'error')
    }
  }
}

async function cleanResults() {
  if (confirm('Are you sure you want to clean all results? This action cannot be undone.')) {
    try {
      // TODO: Replace with real API call
      reports.value = []
      toastStore.show('Results cleaned successfully', 'success')
    } catch (error) {
      toastStore.show('Failed to clean results', 'error')
    }
  }
}

function formatDate(date) {
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  }).format(date)
}

function formatLastUpdated() {
  return new Date().toLocaleString()
}
</script> 