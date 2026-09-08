<template>
  <!-- Report Action Bar (only shown when expanded) -->
  <div 
    v-show="widgetStore.showReportsActionBar"
    class="bg-slate-800 rounded-xl shadow flex flex-wrap gap-3 justify-between items-center w-full p-6 mb-2 widget-action-bar"
  >
    <h2 class="text-lg font-bold text-white flex items-center gap-2 cursor-pointer select-none" @click.stop="widgetStore.toggleWidget('reports')">
      Reports
      <button 
        @click.stop="widgetStore.toggleWidget('reports')"
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
        @click="openGenerateReportModal"
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
      <h2 class="text-lg font-bold text-white flex items-center gap-2 cursor-pointer select-none" @click.stop="widgetStore.toggleWidget('reports')">
        Reports
        <button 
          @click.stop="widgetStore.toggleWidget('reports')"
          class="ml-2 text-slate-400 hover:text-blue-400 focus:outline-none transition-transform minimize-btn"
          title="Expand Reports"
        >
          <i :class="widgetStore.getMinimizeIcon('reports')"></i>
        </button>
      </h2>
    </div>

    <!-- Content (hidden when minimized) -->
    <div v-show="!widgetStore.isReportsMinimized" class="widget-content">
      <!-- Error banner: surfaces backend generation/loading failures -->
      <div
        v-if="errorMessage"
        class="flex items-start gap-3 rounded-lg border border-red-500 bg-red-950 bg-opacity-20 p-3 mb-4 w-full"
        role="alert"
      >
        <i class="fa-solid fa-triangle-exclamation text-red-400 mt-1"></i>
        <div class="flex-1 min-w-0">
          <p class="text-sm font-semibold text-red-300">Report action failed</p>
          <p class="text-sm text-red-200 break-words">{{ errorMessage }}</p>
        </div>
        <button
          @click="dismissError"
          class="text-red-300 hover:text-red-200 ml-auto"
          title="Dismiss"
        >
          <i class="fa-solid fa-xmark"></i>
        </button>
      </div>
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
                  <!-- Skeleton row for generating reports -->
                  <template v-if="report._is_generating">
                    <td colspan="7" class="px-3 py-3 text-sm text-gray-300">
                      <div class="flex items-center gap-3">
                        <div class="animate-spin inline-block w-4 h-4 border-[2px] border-current border-t-transparent text-blue-400 rounded-full" role="status"></div>
                        <span class="text-blue-300 font-medium">Generating {{ report.reportType }} for {{ report.symbol }}…</span>
                        <span class="text-yellow-400 text-xs font-mono">{{ formatElapsed(generatingElapsed) }}</span>
                      </div>
                    </td>
                  </template>
                  <template v-else>
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
                  </template>
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
            <option v-for="t in availableReportTypes" :key="t.value" :value="t.value">{{ t.label }}</option>
          </select>
          <p v-for="t in hiddenReportTypes" :key="t.value" class="text-xs text-gray-500 mt-1">
            <i class="fa-solid fa-circle-info mr-1"></i>{{ t.hint }}
          </p>
          <p class="text-xs text-gray-400 mt-1">Only the inputs needed for this report type are shown.</p>
        </div>
        <div v-if="showField('symbol')">
          <label class="block text-sm text-gray-300 mb-1" for="genSymbol">Symbol</label>
          <div class="relative">
            <input 
              type="text" 
              id="genSymbol" 
              v-model="symbolQuery"
              :placeholder="defaultSymbolPlaceholder"
              class="w-full p-2 rounded bg-slate-700 text-white" 
              autocomplete="off" 
              spellcheck="false"
              style="text-transform:uppercase; letter-spacing:0.5px;"
              @input="onSymbolInput"
              @keydown="onSymbolKeydown"
              @blur="onSymbolBlur"
            >
            <div 
              v-if="symbolDropdownOpen && symbolSuggestions.length"
              class="absolute z-50 w-full mt-0.5 max-h-56 overflow-y-auto border border-slate-600 rounded-b-lg shadow-lg bg-slate-800"
            >
              <div 
                v-for="(item, i) in symbolSuggestions"
                :key="item.symbol + i"
                class="px-3 py-2 cursor-pointer select-none text-sm"
                :class="{ 'bg-blue-700 text-white': i === symbolDropdownIndex, 'hover:bg-blue-700': i !== symbolDropdownIndex }"
                @mousedown.prevent="selectSymbol(item)"
              >
                <span class="font-semibold">{{ item.symbol }}</span>
                <span v-if="item.name" class="ml-1 text-xs text-gray-400 truncate">{{ item.name }}</span>
              </div>
            </div>
          </div>
          <p v-if="symbolSearching" class="text-xs text-gray-400 mt-1">
            <i class="fa-solid fa-rotate fa-spin mr-1"></i>Searching approved symbols…
          </p>
          <p v-if="symbolSearchHint" class="text-xs text-yellow-500 mt-1">
            <i class="fa-solid fa-circle-exclamation mr-1"></i>{{ symbolSearchHint }}
          </p>
          <p v-if="symbolSearchError" class="text-xs text-red-400 mt-1">
            <i class="fa-solid fa-triangle-exclamation mr-1"></i>{{ symbolSearchError }}
          </p>
        </div>
        <div v-if="showField('strategy')">
          <label class="block text-sm text-gray-300 mb-1" for="genStrategy">Strategy</label>
          <select 
            id="genStrategy" 
            v-model="newReport.strategy"
            class="w-full p-2 rounded bg-slate-700 text-white"
            required
          >
            <option v-for="s in validStrategies" :key="s.value" :value="s.value">{{ s.label }}</option>
          </select>
          <p class="text-xs text-gray-400 mt-1">Strategy is only needed for backtest / comparison reports.</p>
        </div>
        <div v-if="showField('timeframe')">
          <label class="block text-sm text-gray-300 mb-1" for="genTimeframe">Timeframe</label>
          <select 
            id="genTimeframe" 
            v-model="newReport.timeframe"
            class="w-full p-2 rounded bg-slate-700 text-white"
          >
            <option value="Daily">Daily</option>
            <option value="Weekly">Weekly</option>
            <option value="Monthly">Monthly</option>
          </select>
        </div>
        <div v-if="showField('startDate')">
          <label class="block text-sm text-gray-300 mb-1" for="genStartDate">Start Date</label>
          <input 
            type="date" 
            id="genStartDate" 
            v-model="newReport.startDate"
            class="w-full p-2 rounded bg-slate-700 text-white"
          >
        </div>
        <div v-if="showField('endDate')">
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
            :disabled="isGenerating"
            class="py-2 px-4 rounded bg-green-600 text-white hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {{ isGenerating ? 'Generating...' : 'Generate' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useToastStore } from '../../stores/toast'
import { useWidgetStore } from '../../stores/widgets'
import { ApiService } from '../../services/api'

const toastStore = useToastStore()
const widgetStore = useWidgetStore()

const showGenerateReportModal = ref(false)
const isLoading = ref(false)
const isGenerating = ref(false)
const generatingElapsed = ref(0)
let generatingTimer = null
const errorMessage = ref('')

function setError(message) {
  errorMessage.value = message || 'An unexpected error occurred.'
}

function dismissError() {
  errorMessage.value = ''
}

function formatElapsed(seconds) {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  if (m > 0) return `${m}m ${s}s`
  return `${s}s`
}

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
  strategy: 'BuyAndHoldStrategy',
  timeframe: 'Daily',
  startDate: '',
  endDate: ''
})

// Auto-adjust startDate/endDate when timeframe changes
watch(() => newReport.value.timeframe, (tf) => {
  if (!tf) return
  const now = new Date()
  const start = new Date()
  if (tf === 'Daily') {
    start.setDate(start.getDate() - 7)
  } else if (tf === 'Weekly') {
    start.setMonth(start.getMonth() - 1)
  } else if (tf === 'Monthly') {
    start.setFullYear(start.getFullYear() - 1)
  }
  newReport.value.startDate = toISODate(start)
  newReport.value.endDate = toISODate(now)
})

// Valid (instrumented) strategies — constrained dropdown, not free-text.
// Mirrors the classes exported by strategies/__init__.py
const validStrategies = [
  { value: 'BuyAndHoldStrategy', label: 'Buy & Hold' },
  { value: 'SimpleMovingAverageCrossover', label: 'SMA Crossover' },
  { value: 'ExponentialMovingAverageCrossover', label: 'EMA Crossover' },
  { value: 'MACDRSIStrategy', label: 'MACD-RSI-EMA' },
  { value: 'BollingerRSIStrategy', label: 'Bollinger RSI' },
  { value: 'CombinedStrategy', label: 'Combined' }
]

// Which fields each report type uses, so the form only shows relevant inputs.
const fieldVisibility = {
  market: ['timeframe', 'startDate', 'endDate'],
  finance: ['symbol', 'startDate', 'endDate'],
  backtest: ['symbol', 'strategy', 'startDate', 'endDate'],
  comparison: ['symbol', 'strategy', 'startDate', 'endDate']
}

// Report types the generation form offers, and whether the backend can actually
// generate them. The backend only registers /api/report/generate-market and
// /generate-finance in this build — there is NO generate-backtest /
// generate-comparison endpoint, so those types cannot be produced. Showing a
// type you can't generate is a broken UX, so they are HIDDEN (with a hint)
// until a backend endpoint exists for them. That was the "hidden unless
// conditions met" behavior: the precondition is backend generation support.
const reportTypeCapabilities = {
  market: { label: 'Market Check', available: true },
  finance: { label: 'Finance', available: true },
  backtest: { label: 'Backtest', available: false },
  comparison: { label: 'Comparison', available: false }
}
const REPORT_TYPE_ORDER = ['market', 'finance', 'backtest', 'comparison']
// Order-preserving filtered lists consumed by the template.
const availableReportTypes = REPORT_TYPE_ORDER
  .filter(t => reportTypeCapabilities[t].available)
  .map(t => ({ value: t, label: reportTypeCapabilities[t].label }))
const hiddenReportTypes = REPORT_TYPE_ORDER
  .filter(t => !reportTypeCapabilities[t].available)
  .map(t => ({
    value: t,
    label: reportTypeCapabilities[t].label,
    hint: `${reportTypeCapabilities[t].label} reports aren\u2019t wired to the backend yet, so this type is hidden until a generation endpoint exists.`
  }))

function toISODate(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function showField(field) {
  return fieldVisibility[newReport.value.reportType]?.includes(field) ?? false
}

// Convert a backend report_path (e.g. "public/results/<dir>/index.html") into a
// same-origin URL the dashboard actually serves (/static/results/<dir>/index.html).
// Returns null when no usable path is given so callers can surface graceful feedback.
function deriveServedReportPath(reportPath) {
  if (!reportPath) return null
  const p = String(reportPath).trim()
  // Normalize Windows/absolute artifacts, then map the "public/" mount root to
  // the "/static/" route it's served under. report.py mounts StaticFiles("public")
  // at /static, so "public/results/<dir>/index.html" -> "/static/results/<dir>/index.html".
  let normalized = p.replace(/\\/g, '/')
  if (normalized.startsWith('public/')) {
    normalized = `/static/${normalized.slice('public/'.length)}`
  } else if (!normalized.startsWith('/')) {
    normalized = `/${normalized}`
  }
  // The report should always be an index.html under results; accept it only if it
  // looks like a served report, else return null so we don't claim a bogus URL.
  if (!normalized.endsWith('index.html')) return null
  return normalized
}

// --- Polygon-backed approved-symbol search (generate modal) ---
const symbolQuery = ref('')
const symbolSuggestions = ref([])
const symbolDropdownOpen = ref(false)
const symbolDropdownIndex = ref(-1)
const symbolSearching = ref(false)
const symbolSearchError = ref('')
const symbolSearchHint = ref('')
let symbolSearchTimer = null

function closeSymbolDropdown() {
  symbolDropdownOpen.value = false
  symbolSuggestions.value = []
  symbolDropdownIndex.value = -1
}

async function searchSymbols(query) {
  const q = (query || '').trim()
  symbolSearchError.value = ''
  symbolSearchHint.value = ''
  if (q.length < 1) {
    closeSymbolDropdown()
    return
  }
  symbolSearching.value = true
  try {
    // /api/report/search-symbols → [{ symbol, name }] (Polygon ACTIVE tickers,
    // validated server-side against Polygon.io). Only these are suggested.
    const results = await ApiService.get(`/api/report/search-symbols?query=${encodeURIComponent(q)}`)
    symbolSuggestions.value = Array.isArray(results) ? results : []
    symbolDropdownIndex.value = -1
    if (symbolSuggestions.value.length) {
      symbolDropdownOpen.value = true
    } else {
      symbolDropdownOpen.value = false
      symbolSearchHint.value = `No approved (active) Polygon symbols match "${q}". Please pick one from the list; the request will fail if the ticker isn't valid.`
    }
  } catch (error) {
    closeSymbolDropdown()
    symbolSearchError.value = `Symbol search failed: ${error && error.message ? error.message : 'could not reach Polygon'}. You can still type a symbol manually.`
  } finally {
    symbolSearching.value = false
  }
}

function onSymbolInput() {
  if (symbolSearchTimer) clearTimeout(symbolSearchTimer)
  symbolSuggestions.value = []
  symbolDropdownOpen.value = false
  symbolSearchHint.value = ''
  symbolSearchError.value = ''
  symbolSearchTimer = setTimeout(() => searchSymbols(symbolQuery.value.trim()), 300)
}

function selectSymbol(item) {
  symbolQuery.value = item.symbol
  newReport.value.symbol = item.symbol
  closeSymbolDropdown()
}

function onSymbolKeydown(e) {
  const n = symbolSuggestions.value.length
  if (!symbolDropdownOpen.value || n === 0) {
    if (e.key === 'Escape' && symbolDropdownOpen.value) symbolDropdownOpen.value = false
    return
  }
  if (e.key === 'ArrowDown') {
    e.preventDefault()
    symbolDropdownIndex.value = (symbolDropdownIndex.value + 1) % n
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    symbolDropdownIndex.value = (symbolDropdownIndex.value - 1 + n) % n
  } else if (e.key === 'Enter') {
    if (symbolDropdownIndex.value >= 0 && symbolDropdownIndex.value < n) {
      e.preventDefault()
      selectSymbol(symbolSuggestions.value[symbolDropdownIndex.value])
    }
  } else if (e.key === 'Escape') {
    closeSymbolDropdown()
  }
}

function onSymbolBlur() {
  setTimeout(closeSymbolDropdown, 150)
}

function openGenerateReportModal() {
  const now = new Date()
  const start = new Date()
  start.setFullYear(start.getFullYear() - 1)
  newReport.value = {
    reportType: 'market',
    symbol: filters.value.symbol !== 'all' ? filters.value.symbol : '',
    strategy: 'BuyAndHoldStrategy',
    timeframe: 'Daily',
    startDate: toISODate(start),
    endDate: toISODate(now)
  }
  symbolQuery.value = newReport.value.symbol
  closeSymbolDropdown()
  symbolSearchError.value = ''
  symbolSearchHint.value = ''
  showGenerateReportModal.value = true
}

const defaultSymbolPlaceholder = computed(() => {
  const s = filters.value.symbol !== 'all' ? filters.value.symbol : ''
  return s ? `e.g. ${s}` : 'e.g. NVDA'
})

// Mock data - replace with real API calls
const reports = ref([])
const availableSymbols = ref(['AAPL', 'NVDA', 'TSLA', 'MSFT', 'GOOGL'])
const availableStrategies = ref(['SMA', 'EMA', 'RSI', 'MACD', 'Buy & Hold'])

const filteredReports = computed(() => {
  // Generating entries always show — prepended at the top
  const generating = reports.value.filter(r => r._is_generating)
  const rest = reports.value.filter(report => {
    if (report._is_generating) return false
    const rtKey = report.reportTypeKey || String(report.reportType || '').toLowerCase()
    if (filters.value.reportType !== 'all' && rtKey !== filters.value.reportType) return false
    if (filters.value.symbol !== 'all' && report.symbol !== filters.value.symbol) return false
    if (filters.value.strategy !== 'all' && String(report.strategy) !== filters.value.strategy) return false
    return true
  })
  return [...generating, ...rest]
})

onMounted(async () => {
  await loadReports()
})

function toReportType(meta) {
  const raw = String(meta.type || meta.report_type || meta.reportType || 'report').toLowerCase()
  if (raw.includes('financial') || raw.includes('finance')) return { key: 'finance', label: 'Finance' }
  if (raw.includes('market')) return { key: 'market', label: 'Market Check' }
  if (raw.includes('backtest')) return { key: 'backtest', label: 'Backtest' }
  if (raw.includes('comparison')) return { key: 'comparison', label: 'Comparison' }
  return { key: raw.replace(/[^a-z0-9]/g, ''), label: raw.replace('_', ' ').toUpperCase() }
}

async function loadReports() {
  isLoading.value = true
  try {
    // Real API: /api/report/list returns report metadata (symbol, type/report_type,
    // strategy, timeframe, start_date/end_date, created). Derive the filter
    // dropdowns from the real data instead of a canned list.
    const data = await ApiService.get('/api/report/list')
    const list = Array.isArray(data) ? data : []
    reports.value = list.map(meta => {
      const rt = toReportType(meta)
      return {
        id: meta.id || meta.path || meta.dir,
        symbol: meta.symbol || 'MARKET',
        reportType: rt.label,
        reportTypeKey: rt.key,
        strategy: meta.strategy || '—',
        timeframe: meta.timeframe || '—',
        dateRange: meta.start_date && meta.end_date
          ? `${meta.start_date} to ${meta.end_date}`
          : (meta.dateRange || '—'),
        created: meta.created ? new Date(String(meta.created).replace(' ', 'T')) : new Date(),
        // HTML report location, if the backend provided it. Falls back to the
        // canonical path derived from the report dir.
        path: meta.path || (meta.dir ? `/static/results/${meta.dir}/index.html` : null),
        dir: meta.dir || null
      }
    })
    availableSymbols.value = [...new Set(reports.value.map(r => r.symbol).filter(s => s && s !== 'MARKET'))].sort()
    availableStrategies.value = [...new Set(reports.value.map(r => r.strategy).filter(s => s && s !== '—'))].sort()
  } catch (error) {
    reports.value = []
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
  // Guard: prevent duplicate submissions while one is in flight
  if (isGenerating.value) return
  dismissError()

  const reportType = newReport.value.reportType
  const symbol = (symbolQuery.value || '').trim().toUpperCase()
  newReport.value.symbol = symbol

  // Close modal immediately — user sees the skeleton entry instead
  showGenerateReportModal.value = false

  // Reset form for next use
  const formSnapshot = {
    reportType: newReport.value.reportType,
    symbol: newReport.value.symbol,
    strategy: newReport.value.strategy,
    timeframe: newReport.value.timeframe,
    startDate: newReport.value.startDate,
    endDate: newReport.value.endDate
  }
  newReport.value = {
    reportType: 'market',
    symbol: '',
    strategy: 'BuyAndHoldStrategy',
    timeframe: 'Daily',
    startDate: '',
    endDate: ''
  }
  symbolQuery.value = ''

  isGenerating.value = true
  generatingElapsed.value = 0

  // Push skeleton entry at the top of the reports list
  const skeletonId = '__generating_' + Date.now()
  reports.value.unshift({
    id: skeletonId,
    _is_generating: true,
    symbol: formSnapshot.symbol || '…',
    reportType: formSnapshot.reportType === 'market' ? 'Market Check' : 'Finance',
    reportTypeKey: formSnapshot.reportType,
    strategy: formSnapshot.strategy || '—',
    timeframe: formSnapshot.timeframe || '—',
    dateRange: formSnapshot.startDate && formSnapshot.endDate
      ? `${formSnapshot.startDate} to ${formSnapshot.endDate}`
      : (formSnapshot.reportType === 'market' ? 'Latest snapshot' : '—'),
    created: new Date(),
  })

  // Start elapsed-time ticker
  generatingTimer = setInterval(() => {
    generatingElapsed.value++
  }, 1000)

  try {
    const params = new URLSearchParams()
    params.append('output_dir', 'public/results')
    params.append('force_refresh', 'false')
    if (formSnapshot.symbol) params.append('symbol', formSnapshot.symbol)
    if (formSnapshot.strategy) params.append('strategy', formSnapshot.strategy)
    if (formSnapshot.startDate) params.append('start_date', formSnapshot.startDate)
    if (formSnapshot.endDate) params.append('end_date', formSnapshot.endDate)

    let endpoint
    if (formSnapshot.reportType === 'finance') {
      if (!formSnapshot.symbol) {
        setError('Symbol is required for finance reports.')
        toastStore.show('Symbol is required for finance reports.', 'error')
        return
      }
      endpoint = `/api/report/generate-finance?${params.toString()}`
    } else if (formSnapshot.reportType === 'market') {
      endpoint = `/api/report/generate-market?${params.toString()}`
    } else {
      setError(`Report type "${formSnapshot.reportType}" generation is not available yet.`)
      toastStore.show(`Report type "${formSnapshot.reportType}" not available yet`, 'error')
      return
    }

    // ApiService throws an Error with the backend's {detail} on non-2xx.
    const resp = await ApiService.post(endpoint)
    const servedPath = deriveServedReportPath(resp && resp.report_path)

    // Remove skeleton entry
    reports.value = reports.value.filter(r => !r._is_generating)

    // Reload from server to get real metadata
    await loadReports()

    const label = formSnapshot.reportType === 'market' ? 'Market report' : 'Report'
    if (servedPath) {
      toastStore.show(`${label} generated — ${servedPath}`, 'success')
    } else {
      toastStore.show(`${label} generated successfully`, 'success')
    }
  } catch (error) {
    // Remove skeleton entry
    reports.value = reports.value.filter(r => !r._is_generating)
    const message = error && error.message
      ? error.message
      : 'Failed to generate report. Please try again.'
    setError(message)
    toastStore.show(message, 'error')
  } finally {
    // Remove skeleton if still lingering (early return paths)
    reports.value = reports.value.filter(r => !r._is_generating)
    isGenerating.value = false
    generatingElapsed.value = 0
    if (generatingTimer) {
      clearInterval(generatingTimer)
      generatingTimer = null
    }
  }
}

function viewReport(report) {
  // Keep the existing notification.
  toastStore.show(`Opening ${report.reportType} for ${report.symbol}`, 'info')

  // The backend serves each report's HTML at /static/results/<dir>/index.html.
  // Prefer the explicit path when provided, else build it from the dir.
  const dir = report.dir
  const rawPath = report.path || (dir ? `/static/results/${dir}/index.html` : null)
  if (!rawPath) {
    toastStore.show('Report HTML is not available for this entry', 'error')
    return
  }
  // Ensure an absolute, same-origin URL so it loads on this dashboard host.
  const url = rawPath.startsWith('/') ? rawPath : `/${rawPath}`
  // Open in a new tab — dynamic-chart HTML (bokeh etc.) renders best standalone.
  window.open(url, '_blank', 'noopener')
}

async function deleteReport(report) {
  if (confirm(`Are you sure you want to delete this ${report.reportType} report for ${report.symbol}?`)) {
    try {
      if (report.dir) {
        await ApiService.post(`/api/report/delete/${encodeURIComponent(report.dir)}`)
      }
      await loadReports()
      toastStore.show('Report deleted successfully', 'success')
    } catch (error) {
      const message = error && error.message ? error.message : 'Failed to delete report'
      toastStore.show(message, 'error')
    }
  }
}

async function cleanResults() {
  if (confirm('Are you sure you want to clean all results? This action cannot be undone.')) {
    try {
      await ApiService.post('/api/report/clean')
      await loadReports()
      toastStore.show('Results cleaned successfully', 'success')
    } catch (error) {
      const message = error && error.message ? error.message : 'Failed to clean results'
      toastStore.show(message, 'error')
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