<template>
  <!-- Orders Action Bar (only shown when expanded) -->
  <div 
    v-show="widgetStore.showOrdersActionBar"
    class="bg-slate-800 rounded-xl shadow flex flex-wrap gap-3 justify-between items-center w-full p-6 mb-2 widget-action-bar"
  >
    <h2 class="text-lg font-bold text-white flex items-center gap-2 cursor-pointer select-none" @click.stop="widgetStore.toggleWidget('orders')">
      Orders
      <button 
        @click.stop="widgetStore.toggleWidget('orders')"
        class="ml-2 text-slate-400 hover:text-blue-400 focus:outline-none transition-transform minimize-btn"
        title="Minimize Orders"
      >
        <i :class="widgetStore.getMinimizeIcon('orders')"></i>
      </button>
    </h2>
    <div class="flex items-center gap-4">
      <button 
        @click="showAddOrderModal = true"
        class="primary-btn py-2 px-4 rounded-lg text-white bg-blue-600 hover:bg-blue-700 flex items-center gap-2"
      >
        <i class="fa-solid fa-plus"></i> Add Order
      </button>
    </div>
  </div>

  <!-- Orders Card -->
  <div class="bg-slate-800 rounded-xl shadow-sm p-6 w-full" :class="{ 'mt-2': widgetStore.showOrdersActionBar }">
    <!-- Collapsed Header (shown when minimized) -->
    <div v-show="widgetStore.isOrdersMinimized" class="flex justify-between items-center">
      <h2 class="text-lg font-bold text-white flex items-center gap-2 cursor-pointer select-none" @click.stop="widgetStore.toggleWidget('orders')">
        Orders
        <button 
          @click.stop="widgetStore.toggleWidget('orders')"
          class="ml-2 text-slate-400 hover:text-blue-400 focus:outline-none transition-transform minimize-btn"
          title="Expand Orders"
        >
          <i :class="widgetStore.getMinimizeIcon('orders')"></i>
        </button>
      </h2>
    </div>

    <!-- Content (hidden when minimized) -->
    <div v-show="!widgetStore.isOrdersMinimized" class="widget-content">
      <div class="overflow-x-auto overflow-y-auto max-h-96">
        <table class="min-w-full divide-y divide-slate-700 text-sm">
          <thead class="bg-slate-800 sticky top-0 z-10">
            <tr>
              <th class="px-3 py-2 text-left text-xs font-medium text-gray-300 uppercase">ID</th>
              <th class="px-3 py-2 text-left text-xs font-medium text-gray-300 uppercase">Symbol</th>
              <th class="px-3 py-2 text-left text-xs font-medium text-gray-300 uppercase">Type</th>
              <th class="px-3 py-2 text-left text-xs font-medium text-gray-300 uppercase">Quantity</th>
              <th class="px-3 py-2 text-left text-xs font-medium text-gray-300 uppercase">Buy Price</th>
              <th class="px-3 py-2 text-left text-xs font-medium text-gray-300 uppercase">Sell Price</th>
              <th class="px-3 py-2 text-left text-xs font-medium text-gray-300 uppercase">Date</th>
              <th class="px-3 py-2 text-left text-xs font-medium text-gray-300 uppercase">P/L</th>
              <th class="px-3 py-2 text-left text-xs font-medium text-gray-300 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="isLoading">
              <td colspan="9" class="text-center text-gray-400 py-4">
                <div class="flex justify-center items-center space-x-2">
                  <div class="animate-spin inline-block w-4 h-4 border-[2px] border-current border-t-transparent text-blue-600 rounded-full" role="status" aria-label="loading">
                    <span class="sr-only">Loading orders...</span>
                  </div>
                  <span>Loading orders...</span>
                </div>
              </td>
            </tr>
            <tr v-else-if="orders.length === 0">
              <td colspan="9" class="text-center text-gray-400 py-4">No orders found.</td>
            </tr>
            <tr v-for="order in orders" :key="order.id" class="hover:bg-slate-700">
              <td class="px-3 py-2 text-sm text-gray-300">{{ order.id }}</td>
              <td class="px-3 py-2 text-sm text-white">{{ order.symbol }}</td>
              <td class="px-3 py-2 text-sm text-gray-300">
                <span :class="getOrderTypeClass(order.type)">{{ order.type }}</span>
              </td>
              <td class="px-3 py-2 text-sm text-gray-300">{{ order.quantity }}</td>
              <td class="px-3 py-2 text-sm text-gray-300">{{ formatCurrency(order.buy_price) }}</td>
              <td class="px-3 py-2 text-sm text-gray-300">{{ formatCurrency(order.sell_price) }}</td>
              <td class="px-3 py-2 text-sm text-gray-300">{{ formatDate(order.date) }}</td>
              <td class="px-3 py-2 text-sm" :class="getPLClass(order.profit_loss)">
                {{ formatCurrency(order.profit_loss) }}
              </td>
              <td class="px-3 py-2 text-sm text-gray-300">
                <div class="flex gap-2">
                  <button
                    @click="editOrder(order)"
                    class="text-blue-400 hover:text-blue-300"
                    title="Edit Order"
                  >
                    <i class="fas fa-edit"></i>
                  </button>
                  <button
                    @click="deleteOrder(order)"
                    class="text-red-400 hover:text-red-300"
                    title="Delete Order"
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

  <!-- Add/Edit Order Modal -->
  <div 
    v-if="showAddOrderModal"
    class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-60"
    @click="showAddOrderModal = false"
  >
    <div 
      class="bg-slate-800 rounded-lg shadow-lg w-full max-w-md p-6 mx-4"
      @click.stop
    >
      <h3 class="text-xl font-bold text-white mb-4">{{ editingOrder ? 'Edit Order' : 'Add Order' }}</h3>
      <form @submit.prevent="saveOrder" class="space-y-4">
        <input type="hidden" v-model="orderForm.id">
        <div>
          <label class="block text-sm text-gray-300 mb-1" for="orderSymbol">Symbol</label>
          <input 
            type="text" 
            id="orderSymbol" 
            v-model="orderForm.symbol"
            class="w-full p-2 rounded bg-slate-700 text-white" 
            required 
            autocomplete="off" 
            style="text-transform:uppercase; letter-spacing:0.5px;"
          >
        </div>
        <div>
          <label class="block text-sm text-gray-300 mb-1" for="orderType">Type</label>
          <select 
            id="orderType" 
            v-model="orderForm.type"
            class="w-full p-2 rounded bg-slate-700 text-white" 
            required
          >
            <option value="buy">Buy</option>
            <option value="sell">Sell</option>
            <option value="dividend">Dividend</option>
          </select>
        </div>
        <div>
          <label class="block text-sm text-gray-300 mb-1" for="orderQuantity">Quantity</label>
          <input 
            type="number" 
            id="orderQuantity" 
            v-model="orderForm.quantity"
            class="w-full p-2 rounded bg-slate-700 text-white" 
            step="any" 
            required
          >
        </div>
        <div>
          <label class="block text-sm text-gray-300 mb-1" for="orderBuyPrice">Buy Price</label>
          <input 
            type="number" 
            id="orderBuyPrice" 
            v-model="orderForm.buy_price"
            class="w-full p-2 rounded bg-slate-700 text-white" 
            step="any"
          >
        </div>
        <div>
          <label class="block text-sm text-gray-300 mb-1" for="orderSellPrice">Sell Price</label>
          <input 
            type="number" 
            id="orderSellPrice" 
            v-model="orderForm.sell_price"
            class="w-full p-2 rounded bg-slate-700 text-white" 
            step="any"
          >
        </div>
        <div>
          <label class="block text-sm text-gray-300 mb-1" for="orderDate">Date</label>
          <input 
            type="date" 
            id="orderDate" 
            v-model="orderForm.date"
            class="w-full p-2 rounded bg-slate-700 text-white" 
            required
          >
        </div>
        <div>
          <label class="block text-sm text-gray-300 mb-1" for="orderPL">P/L</label>
          <input 
            type="number" 
            id="orderPL" 
            v-model="orderForm.profit_loss"
            class="w-full p-2 rounded bg-slate-700 text-white" 
            step="any"
          >
        </div>
        <div class="flex justify-end gap-2 mt-4">
          <button 
            type="button" 
            @click="showAddOrderModal = false"
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

const showAddOrderModal = ref(false)
const isLoading = ref(false)
const orders = ref([])
const editingOrder = ref(null)

const orderForm = ref({
  id: null,
  symbol: '',
  type: 'buy',
  quantity: 0,
  buy_price: 0,
  sell_price: 0,
  date: '',
  profit_loss: 0
})

onMounted(async () => {
  await loadOrders()
})

async function loadOrders() {
  isLoading.value = true
  try {
    // TODO: Replace with real API call
    await new Promise(resolve => setTimeout(resolve, 1000))
    orders.value = [
      {
        id: 1,
        symbol: 'AAPL',
        type: 'buy',
        quantity: 10,
        buy_price: 150.00,
        sell_price: 0,
        date: '2024-12-15',
        profit_loss: 0
      },
      {
        id: 2,
        symbol: 'NVDA',
        type: 'sell',
        quantity: 5,
        buy_price: 200.00,
        sell_price: 250.00,
        date: '2024-12-10',
        profit_loss: 250.00
      }
    ]
  } catch (error) {
    toastStore.show('Failed to load orders', 'error')
  } finally {
    isLoading.value = false
  }
}

function getOrderTypeClass(type) {
  const classes = {
    'buy': 'text-green-400',
    'sell': 'text-red-400',
    'dividend': 'text-blue-400'
  }
  return classes[type] || 'text-gray-300'
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

function formatDate(date) {
  if (!date) return ''
  return new Date(date).toLocaleDateString()
}

function editOrder(order) {
  editingOrder.value = order
  orderForm.value = { ...order }
  showAddOrderModal.value = true
}

async function saveOrder() {
  try {
    // TODO: Replace with real API call
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    if (editingOrder.value) {
      // Update existing order
      const index = orders.value.findIndex(o => o.id === editingOrder.value.id)
      if (index !== -1) {
        orders.value[index] = { ...orderForm.value }
      }
    } else {
      // Add new order
      const newOrder = {
        ...orderForm.value,
        id: Date.now()
      }
      orders.value.unshift(newOrder)
    }
    
    showAddOrderModal.value = false
    resetForm()
    toastStore.show(`Order ${editingOrder.value ? 'updated' : 'added'} successfully`, 'success')
  } catch (error) {
    toastStore.show('Failed to save order', 'error')
  }
}

async function deleteOrder(order) {
  if (confirm(`Are you sure you want to delete this ${order.type} order for ${order.symbol}?`)) {
    try {
      // TODO: Replace with real API call
      orders.value = orders.value.filter(o => o.id !== order.id)
      toastStore.show('Order deleted successfully', 'success')
    } catch (error) {
      toastStore.show('Failed to delete order', 'error')
    }
  }
}

function resetForm() {
  orderForm.value = {
    id: null,
    symbol: '',
    type: 'buy',
    quantity: 0,
    buy_price: 0,
    sell_price: 0,
    date: '',
    profit_loss: 0
  }
  editingOrder.value = null
}
</script> 