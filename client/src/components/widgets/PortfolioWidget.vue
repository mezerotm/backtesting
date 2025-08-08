<template>
  <!-- Portfolio Action Bar (only shown when expanded) -->
  <div 
    v-show="widgetStore.showPortfolioActionBar"
    class="bg-slate-800 rounded-xl shadow flex justify-between items-center w-full p-6 mb-2 widget-action-bar"
  >
    <h2 class="text-lg font-bold text-white flex items-center gap-2">
      Portfolio
      <button 
        @click="widgetStore.toggleWidget('portfolio')"
        class="ml-2 text-slate-400 hover:text-blue-400 focus:outline-none transition-transform minimize-btn"
        title="Minimize Portfolio"
      >
        <i :class="widgetStore.getMinimizeIcon('portfolio')"></i>
      </button>
    </h2>
    <div class="flex items-center gap-4">
      <button
        @click="showAddPositionModal = true"
        class="primary-btn py-2 px-4 rounded-lg text-white bg-blue-600 hover:bg-blue-700 flex items-center gap-2"
      >
        <i class="fa-solid fa-plus"></i> Add Position
      </button>
      <button
        @click="openSettingsModal"
        class="text-slate-400 hover:text-blue-400 focus:outline-none flex items-center justify-center rounded-full h-10 w-10"
        title="Portfolio Settings"
      >
        <i class="fa-solid fa-gear text-xl"></i>
      </button>
    </div>
  </div>

  <!-- Portfolio Card -->
  <div class="bg-slate-800 rounded-xl shadow-sm p-6 w-full" :class="{ 'mt-2': widgetStore.showPortfolioActionBar }">
    <!-- Collapsed Header (shown when minimized) -->
    <div v-show="widgetStore.isPortfolioMinimized" class="flex justify-between items-center">
      <h2 class="text-lg font-bold text-white flex items-center gap-2">
        Portfolio
        <button 
          @click="widgetStore.toggleWidget('portfolio')"
          class="ml-2 text-slate-400 hover:text-blue-400 focus:outline-none transition-transform minimize-btn"
          title="Expand Portfolio"
        >
          <i :class="widgetStore.getMinimizeIcon('portfolio')"></i>
        </button>
      </h2>
    </div>

    <!-- Content (hidden when minimized) -->
    <div v-show="!widgetStore.isPortfolioMinimized" class="widget-content">
      <!-- Loading State -->
      <div v-if="portfolioStore.isLoading" class="text-center py-8">
        <div class="text-gray-400">Loading portfolio data...</div>
      </div>

      <!-- Error State -->
      <div v-else-if="portfolioStore.error" class="text-center py-8">
        <div class="text-red-400">{{ portfolioStore.error }}</div>
        <button
          @click="refreshData"
          class="mt-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded"
        >
          Retry
        </button>
      </div>

      <!-- Portfolio Table -->
      <div v-else class="overflow-x-auto overflow-y-auto max-h-750px">
        <table class="min-w-full divide-y divide-slate-700">
          <thead>
            <tr>
              <th class="px-3 py-2 text-left text-xs font-medium text-gray-300 uppercase">Symbol</th>
              <th class="px-3 py-2 text-left text-xs font-medium text-gray-300 uppercase cursor-pointer hover:text-blue-400 transition-colors" 
                  @click="sortBy('amount')">
                Amount ($)
                <i v-if="sortColumn === 'amount'" :class="getSortIcon(sortDirection)"></i>
              </th>
              <th class="px-3 py-2 text-left text-xs font-medium text-gray-300 uppercase">Avg Buy Price</th>
              <th class="px-3 py-2 text-left text-xs font-medium text-gray-300 uppercase">Market Value</th>
              <th class="px-3 py-2 text-left text-xs font-medium text-gray-300 uppercase cursor-pointer hover:text-blue-400 transition-colors"
                  @click="sortBy('percent')">
                % of Portfolio
                <i v-if="sortColumn === 'percent'" :class="getSortIcon(sortDirection)"></i>
              </th>
              <th class="px-3 py-2 text-left text-xs font-medium text-gray-300 uppercase">Today's Return</th>
              <th class="px-3 py-2 text-left text-xs font-medium text-gray-300 uppercase cursor-pointer hover:text-blue-400 transition-colors"
                  @click="sortBy('total_return')">
                Total Return
                <i v-if="sortColumn === 'total_return'" :class="getSortIcon(sortDirection)"></i>
              </th>
              <th class="px-3 py-2 text-left text-xs font-medium text-gray-300 uppercase">Beta</th>
              <th class="px-3 py-2 text-left text-xs font-medium text-gray-300 uppercase cursor-pointer hover:text-blue-400 transition-colors"
                  @click="sortBy('delta')">
                Delta
                <i v-if="sortColumn === 'delta'" :class="getSortIcon(sortDirection)"></i>
              </th>
              <th class="px-3 py-2 text-left text-xs font-medium text-gray-300 uppercase">Notes</th>
              <th class="px-3 py-2 text-left text-xs font-medium text-gray-300 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-700">

            
            <tr v-if="sortedPositions.length === 0">
              <td colspan="11" class="text-center text-gray-400 py-4">No positions found.</td>
            </tr>
            <tr v-for="position in sortedPositions" :key="position.symbol" class="border-b border-slate-700 hover:bg-slate-700">
              <td class="px-3 py-2">
                <span :class="getSymbolClass(position)">{{ position.symbol }}</span>
              </td>
              <td class="px-3 py-2 text-gray-200">
                {{ formatCurrency(position.amount) }}
              </td>
              <td class="px-3 py-2 text-gray-200">
                {{ position.avg_buy_price ? formatCurrency(position.avg_buy_price) : '-' }}
              </td>
              <td class="px-3 py-2 text-gray-200">
                {{ formatCurrency(position.market_value) }}
              </td>
              <td class="px-3 py-2 text-gray-200">
                {{ formatPercentage(position.percent_of_portfolio) }}
              </td>
              <td class="px-3 py-2" :class="getReturnClass(position.todays_return)">
                {{ formatPercentage(position.todays_return) }}
              </td>
              <td class="px-3 py-2" :class="getReturnClass(position.total_return)">
                {{ formatPercentage(position.total_return) }}
              </td>
              <td class="px-3 py-2 text-gray-200">
                {{ position.beta ? position.beta.toFixed(2) : '-' }}
              </td>
              <td class="px-3 py-2" :class="getReturnClass(position.delta)">
                {{ formatCurrency(position.delta) }}
              </td>
              <td class="px-3 py-2 text-gray-400">
                {{ position.notes || '-' }}
              </td>
                          <td class="px-3 py-2">
              <!-- Empty for CASH and BTC -->
              <div v-if="position.is_cash || position.is_btc"></div>
              <!-- Robinhood badges for Robinhood positions -->
              <div v-else-if="isRobinhoodPosition(position)" class="flex gap-1">
                <span
                  :class="getRobinhoodBadgeClass(position)"
                  class="rh-badge"
                >
                  {{ position.is_crypto ? '₿' : 'RH' }}
                </span>
              </div>
              <!-- Edit/Delete buttons for manual positions -->
              <div v-else class="flex gap-1">
                <button
                  @click="editPosition(position)"
                  class="text-blue-400 hover:text-blue-300"
                  title="Edit"
                >
                  <i class="fas fa-edit"></i>
                </button>
                <button
                  @click="deletePosition(position)"
                  class="text-red-400 hover:text-red-300"
                  title="Delete"
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

  <!-- Add/Edit Position Modal -->
  <div
    v-if="showAddPositionModal"
    class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
    @click="showAddPositionModal = false"
  >
    <div
      class="bg-slate-800 rounded-lg p-6 w-full max-w-md mx-4"
      @click.stop
    >
      <div class="flex justify-between items-center mb-4">
        <h3 class="text-xl font-bold text-white">{{ editingPosition ? 'Edit Position' : 'Add Position' }}</h3>
        <button
          @click="showAddPositionModal = false"
          class="text-gray-400 hover:text-white"
        >
          <i class="fas fa-times"></i>
        </button>
      </div>

      <form @submit.prevent="savePosition" class="space-y-4">
        <input type="hidden" v-model="positionForm.id">
        <div>
          <label class="block text-sm text-gray-300 mb-1" for="symbol">Symbol</label>
          <input 
            type="text" 
            id="symbol" 
            v-model="positionForm.symbol"
            class="w-full p-2 rounded bg-slate-700 text-white" 
            required 
            autocomplete="off" 
            style="text-transform:uppercase; letter-spacing:0.5px;"
          >
        </div>
        <div>
          <label class="block text-sm text-gray-300 mb-1" for="amount">Amount ($)</label>
          <input 
            type="number" 
            id="amount" 
            v-model="positionForm.amount"
            class="w-full p-2 rounded bg-slate-700 text-white" 
            step="any" 
            required 
            placeholder="Enter dollar amount"
          >
        </div>
        <div>
          <label class="block text-sm text-gray-300 mb-1" for="buyPrice">Avg Buy Price</label>
          <input 
            type="number" 
            id="buyPrice" 
            v-model="positionForm.avg_buy_price"
            class="w-full p-2 rounded bg-slate-700 text-white" 
            step="any" 
            required 
            placeholder="Enter average buy price"
          >
        </div>
        <div>
          <label class="block text-sm text-gray-300 mb-1" for="notes">Notes</label>
          <textarea 
            id="notes" 
            v-model="positionForm.notes"
            class="w-full p-2 rounded bg-slate-700 text-white"
          ></textarea>
        </div>
        <div class="flex justify-end gap-2 mt-4">
          <button 
            type="button" 
            @click="showAddPositionModal = false"
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

  <!-- Settings Modal -->
  <div
    v-if="showSettingsModal"
    class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
    @click="portfolioStore.isSyncing ? null : showSettingsModal = false"
  >
    <div
      class="bg-slate-800 rounded-lg p-6 w-full max-w-md mx-4 relative"
      @click.stop
    >
      <!-- Loading Overlay -->
      <div v-if="portfolioStore.isSyncing" class="absolute inset-0 bg-black bg-opacity-50 flex items-center justify-center z-10 rounded-lg">
        <div class="bg-slate-700 rounded-lg p-6 max-w-md w-full mx-4">
          <div class="text-white text-center">
            <div class="text-lg font-semibold mb-2">Syncing Market Data</div>
            <div class="text-sm opacity-75 mb-4">Please wait, this may take 30-60 seconds</div>
            <div class="flex items-center justify-center">
              <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mr-3"></div>
              <div class="text-sm">Processing data...</div>
            </div>
          </div>
        </div>
      </div>
      <div class="flex justify-between items-center mb-4">
        <h3 class="text-xl font-bold text-white">Portfolio Settings</h3>
        <button
          @click="showSettingsModal = false"
          :disabled="portfolioStore.isSyncing"
          class="text-gray-400 hover:text-white disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <i class="fas fa-times"></i>
        </button>
      </div>

      <form @submit.prevent="saveSettings" class="space-y-4">
        <div class="mb-4">
          <h4 class="text-sm font-bold text-white mb-2">Portfolio</h4>
          <label for="cash" class="block text-sm text-green-400 font-semibold mb-2">Total Portfolio Cash ($):</label>
          <input 
            type="text" 
            id="cash" 
            v-model="settings.total_portfolio_cash"
            class="p-2 rounded bg-slate-700 text-white w-full" 
            step="1" 
            min="0" 
            inputmode="numeric" 
            autocomplete="off"
          >
        </div>
        <div class="mb-4">
          <label for="btcDollar" class="block text-sm text-yellow-300 font-semibold mb-2">Total Portfolio BTC ($):</label>
          <input 
            type="text" 
            id="btcDollar" 
            v-model="settings.total_portfolio_btc"
            class="p-2 rounded bg-slate-700 text-white w-full" 
            step="any" 
            min="0" 
            inputmode="decimal" 
            autocomplete="off"
            placeholder="Enter BTC value in dollars"
          >
        </div>
        <div class="mb-4">
          <label for="btcAvgBuyPrice" class="block text-sm text-yellow-300 font-semibold mb-2">BTC Avg Buy Price ($):</label>
          <input 
            type="text" 
            id="btcAvgBuyPrice" 
            v-model="settings.btc_avg_buy_price"
            class="p-2 rounded bg-slate-700 text-white w-full" 
            step="any" 
            min="0" 
            inputmode="decimal" 
            autocomplete="off"
          >
        </div>
        
        <!-- Robinhood Integration Section -->
        <div class="mb-4">
          <h4 class="text-sm font-bold text-white mb-2">Robinhood Integration</h4>
          <div class="space-y-4">
            <div class="flex items-center">
              <input 
                type="checkbox" 
                id="robinhoodEnabled" 
                v-model="settings.robinhood_enabled"
                class="mr-2"
              >
              <label for="robinhoodEnabled" class="text-sm text-slate-300">Enable Robinhood Integration</label>
            </div>
            <div v-if="settings.robinhood_enabled">
              <div class="mb-4">
                <label for="robinhoodUsername" class="block text-sm text-slate-300 mb-1">Username</label>
                <input 
                  type="email" 
                  id="robinhoodUsername" 
                  v-model="settings.robinhood_username"
                  class="p-2 rounded bg-slate-700 text-white w-full"
                  placeholder="Enter Robinhood email"
                >
              </div>
              <div class="mb-4">
                <label for="robinhoodPassword" class="block text-sm text-slate-300 mb-1">Password</label>
                <input 
                  type="password" 
                  id="robinhoodPassword" 
                  v-model="settings.robinhood_password"
                  class="p-2 rounded bg-slate-700 text-white w-full"
                  placeholder="Enter Robinhood password"
                >
              </div>
              <div class="mb-4">
                <label for="robinhoodMFA" class="block text-sm text-slate-300 mb-1">MFA Code (Optional)</label>
                <input 
                  type="text" 
                  id="robinhoodMFA" 
                  v-model="settings.robinhood_mfa"
                  class="p-2 rounded bg-slate-700 text-white w-full"
                  placeholder="Enter MFA code if enabled"
                >
              </div>
              <div class="mb-4">
                <button 
                  type="button"
                  @click="syncMarketData"
                  :disabled="portfolioStore.isSyncing"
                  class="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white font-medium py-2 px-4 rounded transition-colors flex items-center justify-center gap-2"
                >
                  <div v-if="portfolioStore.isSyncing" class="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  <span v-if="portfolioStore.isSyncing">Syncing...</span>
                  <span v-else>Sync Market Data</span>
                </button>
              </div>
            </div>
          </div>
        </div>
        
        <hr class="my-6 border-t border-slate-600">
        <div class="flex justify-end gap-2">
          <button type="button" @click="showSettingsModal = false" :disabled="portfolioStore.isSyncing" class="py-2 px-4 rounded bg-gray-600 text-white hover:bg-gray-500 disabled:opacity-50 disabled:cursor-not-allowed">Cancel</button>
          <button type="submit" :disabled="portfolioStore.isSyncing" class="py-2 px-4 rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed">Save</button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { usePortfolioStore } from '../../stores/portfolio'
import { useMarketDataStore } from '../../stores/marketData'
import { useToastStore } from '../../stores/toast'
import { useWidgetStore } from '../../stores/widgets'
import { ApiService, API_ENDPOINTS } from '../../services/api'

const portfolioStore = usePortfolioStore()
const marketDataStore = useMarketDataStore()
const toastStore = useToastStore()
const widgetStore = useWidgetStore()

const showSettingsModal = ref(false)
const showAddPositionModal = ref(false)
const sortColumn = ref('amount')
const sortDirection = ref('desc')

const settings = ref({
  total_portfolio_cash: '0',
  total_portfolio_btc: '0',
  btc_avg_buy_price: '0',
  robinhood_username: '',
  robinhood_password: '',
  robinhood_mfa: '',
  robinhood_enabled: true
})

const editingPosition = ref(null)
const positionForm = ref({
  id: null,
  symbol: '',
  amount: 0,
  avg_buy_price: 0,
  notes: ''
})

const sortedPositions = computed(() => {
  const positions = portfolioStore.sortedPositions || []
  
  if (!sortColumn.value) return positions

  // Separate CASH/BTC from other positions
  const cashBtcPositions = positions.filter(pos => pos.is_cash || pos.is_btc)
  const otherPositions = positions.filter(pos => !pos.is_cash && !pos.is_btc)

  // Sort only the other positions
  const sortedOtherPositions = [...otherPositions].sort((a, b) => {
    let aVal = a[sortColumn.value] || 0
    let bVal = b[sortColumn.value] || 0

    if (sortDirection.value === 'asc') {
      return aVal > bVal ? 1 : -1
    } else {
      return aVal < bVal ? 1 : -1
    }
  })

  // Always return CASH/BTC first, then sorted other positions
  return [...cashBtcPositions, ...sortedOtherPositions]
})

onMounted(async () => {
  await portfolioStore.fetchPortfolioData()
})

function sortBy(column) {
  if (sortColumn.value === column) {
    sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortColumn.value = column
    sortDirection.value = 'desc'
  }
}

function getSortIcon(direction) {
  return direction === 'asc' ? 'fas fa-sort-up' : 'fas fa-sort-down'
}

function isRobinhoodPosition(position) {
  // Check if position is from Robinhood based on source or other indicators
  // This could be based on a 'source' field, or we can infer from the data structure
  return position.source === 'robinhood' || position.source === 'robinhood_crypto' || 
         (position.created_at && position.updated_at && !position.notes) // Infer from data patterns
}

function getRobinhoodBadgeClass(position) {
  return position.is_crypto ? 'rh-badge crypto-badge' : 'rh-badge'
}



function getSymbolClass(position) {
  if (position.is_cash) {
    return 'font-bold text-green-400' // Green for CASH
  } else if (position.is_btc) {
    return 'font-bold text-yellow-400' // Yellow for BTC
  }
  return 'font-semibold text-white'
}

function getBadgeClass(badge) {
  const classes = {
    'RH': 'bg-green-600 text-white',
    'NEW': 'bg-blue-600 text-white',
    'SOLD': 'bg-red-600 text-white'
  }
  return classes[badge] || 'bg-gray-600 text-white'
}

function getReturnClass(value) {
  if (!value) return 'text-gray-400'
  return value >= 0 ? 'text-green-400' : 'text-red-400'
}

function formatCurrency(value) {
  if (!value && value !== 0) return '$0.00'
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD'
  }).format(value)
}

function formatPercentage(value) {
  if (!value && value !== 0) return '0.00%'
  return `${value.toFixed(2)}%`
}

function formatLastUpdated() {
  return portfolioStore.lastUpdated || 'Never'
}

async function refreshData() {
  await portfolioStore.fetchPortfolioData()
}

async function pullRobinhoodData() {
  try {
    await portfolioStore.pullRobinhoodData()
    toastStore.show('Robinhood data pulled successfully', 'success')
  } catch (error) {
    toastStore.show('Failed to pull Robinhood data', 'error')
  }
}

async function loadSettings() {
  try {
    // Fetch current portfolio settings from the API
    const settingsData = await ApiService.get(API_ENDPOINTS.PORTFOLIO_SETTINGS)
    
    // Load current portfolio settings into the modal form
    settings.value = {
      total_portfolio_cash: settingsData.total_portfolio_cash?.toString() || '0',
      total_portfolio_btc: settingsData.total_portfolio_btc?.toString() || '0',
      btc_avg_buy_price: settingsData.btc_avg_buy_price?.toString() || '0',
      robinhood_username: settingsData.robinhood_username || '',
      robinhood_password: settingsData.robinhood_password || '',
      robinhood_mfa: settingsData.robinhood_mfa || '',
      robinhood_enabled: settingsData.robinhood_enabled || false
    }
  } catch (error) {
    console.error('Error loading portfolio settings:', error)
    // Fallback to store values for portfolio data
    settings.value = {
      total_portfolio_cash: portfolioStore.portfolioCash?.toString() || '0',
      total_portfolio_btc: portfolioStore.portfolioBTCDollar?.toString() || '0',
      btc_avg_buy_price: portfolioStore.btcAvgBuyPrice?.toString() || '0',
      robinhood_username: '',
      robinhood_password: '',
      robinhood_mfa: '',
      robinhood_enabled: false
    }
  }
}

async function openSettingsModal() {
  await loadSettings()
  showSettingsModal.value = true
}

async function saveSettings() {
  try {
    // Validate and convert numeric fields
    const numericFields = {
      total_portfolio_cash: settings.value.total_portfolio_cash,
      total_portfolio_btc: settings.value.total_portfolio_btc,
      btc_avg_buy_price: settings.value.btc_avg_buy_price
    }

    // Validate numeric fields
    for (const [key, value] of Object.entries(numericFields)) {
      if (value === '' || isNaN(parseFloat(value))) {
        toastStore.show(`Invalid value for ${key}. Please enter a valid number.`, 'error')
        return
      }
      if (parseFloat(value) < 0) {
        toastStore.show(`${key} cannot be negative.`, 'error')
        return
      }
    }

    const settingsToSave = {
      total_portfolio_cash: parseFloat(settings.value.total_portfolio_cash),
      total_portfolio_btc: parseFloat(settings.value.total_portfolio_btc),
      btc_avg_buy_price: parseFloat(settings.value.btc_avg_buy_price),
      robinhood_enabled: settings.value.robinhood_enabled ?? false,
      robinhood_username: settings.value.robinhood_username?.trim() || null,
      robinhood_password: settings.value.robinhood_password?.trim() || null,
      robinhood_mfa: settings.value.robinhood_mfa?.trim() || null
    }

    const result = await portfolioStore.updatePortfolioSettings(settingsToSave)
    if (result.success) {
      showSettingsModal.value = false
      toastStore.show('Settings saved successfully', 'success')
    } else {
      toastStore.show(result.error || 'Failed to save settings', 'error')
    }
  } catch (error) {
    console.error('Error saving settings:', error)
    toastStore.show(error instanceof Error ? error.message : 'Failed to save settings', 'error')
  }
}

async function syncMarketData() {
  try {
    const result = await portfolioStore.syncMarketData()
    if (result.success) {
      toastStore.show('Market data synced successfully', 'success')
    } else {
      toastStore.show(result.error || 'Failed to sync market data', 'error')
    }
  } catch (error) {
    toastStore.show('Failed to sync market data', 'error')
  }
}

function editPosition(position) {
  editingPosition.value = position
  positionForm.value = { ...position }
  showAddPositionModal.value = true
}

async function savePosition() {
  try {
    // TODO: Replace with real API call
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    if (editingPosition.value) {
      // Update existing position
      const index = portfolioStore.positions.findIndex(p => p.id === editingPosition.value.id)
      if (index !== -1) {
        portfolioStore.positions[index] = { ...positionForm.value }
      }
    } else {
      // Add new position
      const newPosition = {
        ...positionForm.value,
        id: Date.now()
      }
      portfolioStore.positions.unshift(newPosition)
    }
    
    showAddPositionModal.value = false
    resetPositionForm()
    toastStore.show(`Position ${editingPosition.value ? 'updated' : 'added'} successfully`, 'success')
  } catch (error) {
    toastStore.show('Failed to save position', 'error')
  }
}

function deletePosition(position) {
  // TODO: Implement delete position confirmation
  console.log('Delete position:', position)
}

function resetPositionForm() {
  positionForm.value = {
    id: null,
    symbol: '',
    amount: 0,
    avg_buy_price: 0,
    notes: ''
  }
  editingPosition.value = null
}
</script> 