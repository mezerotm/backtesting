export function initOrders() {
  console.log('[Orders] Initializing orders widget...');
  // Render the orders widget HTML into the placeholder
  const ordersWidget = document.getElementById('orders-widget');
  if (ordersWidget) {
    console.log('[Orders] Found orders-widget element, rendering HTML...');
    // Create the orders widget HTML structure
    ordersWidget.innerHTML = `
      <!-- Orders Action Bar -->
      <div id="ordersActionBar" class="bg-slate-800 rounded-xl shadow flex justify-end gap-4 w-full p-6 mb-2 collapsed">
          <button id="addOrderBtn" class="primary-btn py-2 px-4 rounded-lg text-white bg-blue-600 hover:bg-blue-700 flex items-center gap-2">
              <i class="fa-solid fa-plus"></i> Add Order
          </button>
      </div>
      <!-- Orders Card -->
      <div class="bg-slate-800 rounded-xl shadow-sm widget-orders p-6 w-full">
        <div class="flex justify-between items-center mb-0">
          <h2 class="text-lg font-bold text-white flex items-center gap-2">
            Orders
            <button id="ordersMinimizeBtn" class="ml-2 text-slate-400 hover:text-blue-400 focus:outline-none" title="Minimize Orders" style="transition: transform 0.2s;"><i id="ordersMinimizeIcon" class="fa-solid fa-chevron-down"></i></button>
          </h2>
        </div>
        <div id="ordersContent" class="collapsed">
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
              <tbody id="ordersTbody">
                <tr><td colspan="9" class="text-center text-gray-400 py-4">Loading...</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
      
      <!-- Order Modal -->
      <div id="orderModal" class="fixed inset-0 bg-black bg-opacity-50 hidden z-50 flex items-center justify-center">
        <div class="bg-slate-800 rounded-lg p-6 w-full max-w-2xl mx-4">
          <div class="flex justify-between items-center mb-4">
            <h2 id="orderModalTitle" class="text-xl font-bold text-white">Add Order</h2>
            <button id="cancelOrderModalBtn" class="text-gray-400 hover:text-white">
              <i class="fas fa-times"></i>
            </button>
          </div>
          
          <form id="orderForm" class="space-y-4">
            <input type="hidden" id="orderId" name="id">
            
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label for="orderSymbol" class="block text-sm font-medium text-gray-300 mb-1">Symbol</label>
                <input type="text" id="orderSymbol" name="symbol" required 
                       class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-white placeholder-gray-400">
              </div>
              
              <div>
                <label for="orderType" class="block text-sm font-medium text-gray-300 mb-1">Type</label>
                <select id="orderType" name="type" required 
                        class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-white">
                  <option value="buy">Buy</option>
                  <option value="sell">Sell</option>
                </select>
              </div>
              
              <div>
                <label for="orderQuantity" class="block text-sm font-medium text-gray-300 mb-1">Quantity</label>
                <input type="number" id="orderQuantity" name="quantity" step="0.01" required 
                       class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-white placeholder-gray-400">
              </div>
              
              <div>
                <label for="orderBuyPrice" class="block text-sm font-medium text-gray-300 mb-1">Buy Price</label>
                <input type="number" id="orderBuyPrice" name="buy_price" step="0.01" 
                       class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-white placeholder-gray-400">
              </div>
              
              <div>
                <label for="orderSellPrice" class="block text-sm font-medium text-gray-300 mb-1">Sell Price</label>
                <input type="number" id="orderSellPrice" name="sell_price" step="0.01" 
                       class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-white placeholder-gray-400">
              </div>
              
              <div>
                <label for="orderDate" class="block text-sm font-medium text-gray-300 mb-1">Date</label>
                <input type="date" id="orderDate" name="date" 
                       class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-white">
              </div>
              
              <div>
                <label for="orderPL" class="block text-sm font-medium text-gray-300 mb-1">P/L</label>
                <input type="number" id="orderPL" name="pl" step="0.01" 
                       class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-white placeholder-gray-400">
              </div>
            </div>
            
            <div class="flex justify-end gap-2">
              <button type="button" id="cancelOrderModalBtn2" class="reset-btn py-2 px-4 rounded-lg text-white bg-gray-600 hover:bg-gray-700">
                Cancel
              </button>
              <button type="submit" class="primary-btn py-2 px-4 rounded-lg text-white bg-blue-600 hover:bg-blue-700">
                Save Order
              </button>
            </div>
          </form>
        </div>
      </div>
    `;
  }
  
  console.log('[Orders] Orders widget HTML rendered, fetching data...');
  fetchAndRenderOrders();
  setupOrderModal();
  console.log('[Orders] Orders widget initialization complete');
}

async function fetchAndRenderOrders() {
  try {
    console.log('[Orders] Fetching orders...');
    const response = await fetch('/api/orders/').then(r => r.json());
    console.log('[Orders] Received response:', response);
    
    // Validate the response data
    if (window.DataModels && window.DataModels.validateData) {
      const validation = window.DataModels.validateData('orders_response', response);
      if (!validation.success) {
        console.error('[Orders] Data validation failed:', validation.errors);
        // Don't show error to user, just log it and continue with empty data
        console.warn('[Orders] Continuing with empty orders due to validation failure');
        renderOrders([]);
        return;
      }
      console.log('[Orders] Data validation successful');
    }
    
    const orders = response.orders || [];
    console.log('[Orders] Extracted orders array:', orders);
    console.log('[Orders] Orders array length:', orders.length);
    console.log('[Orders] Orders data structure:', JSON.stringify(orders, null, 2));
    renderOrders(orders);
  } catch (error) {
    console.error('[Orders] Error fetching orders:', error);
    renderOrders([]);
  }
}

function renderOrders(orders) {
  console.log('[Orders] Rendering orders:', orders);
  if (!Array.isArray(orders)) {
    console.error("Orders is not an array", orders);
    orders = [];
  }
  const tbody = document.getElementById('ordersTbody');
  if (!tbody) {
    console.error('[Orders] ordersTbody element not found');
    return;
  }
  tbody.innerHTML = '';
  if (!orders || orders.length === 0) {
    console.log('[Orders] No orders to display');
    tbody.innerHTML = '<tr><td colspan="9" class="text-center text-gray-400 py-4">No orders found.</td></tr>';
    return;
  }
  orders.forEach(order => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td class="px-3 py-2">${order.id}</td>
      <td class="px-3 py-2">${order.symbol}</td>
      <td class="px-3 py-2">${order.type}</td>
      <td class="px-3 py-2">${order.quantity}</td>
      <td class="px-3 py-2">${order.type === 'buy' ? order.price : ''}</td>
      <td class="px-3 py-2">${order.type === 'sell' ? order.price : ''}</td>
      <td class="px-3 py-2">${order.date ? new Date(order.date).toLocaleDateString() : ''}</td>
      <td class="px-3 py-2">${order.pl ? `$${order.pl.toFixed(2)}` : ''}</td>
      <td class="px-3 py-2">
        ${order.source === 'robinhood' ? 
          '<span class="rh-badge">RH</span>' : 
          `<button class="edit-btn text-blue-400 hover:text-blue-300 mr-2" onclick="editOrder(${order.id})">
            <i class="fa-solid fa-pencil"></i>
          </button>
          <button class="delete-btn text-red-400 hover:text-red-300" onclick="deleteOrder(${order.id})">
            <i class="fa-solid fa-trash"></i>
          </button>`
        }
      </td>
    `;
    tbody.appendChild(tr);
  });
  tbody.querySelectorAll('.edit-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const id = btn.getAttribute('data-id');
      const order = orders.find(o => String(o.id) === String(id));
      if (order) openEditOrder(order);
    });
  });
  tbody.querySelectorAll('.delete-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      const id = btn.getAttribute('data-id');
      if (confirm('Delete this order?')) {
        await fetch(`/api/orders/${id}`, { method: 'DELETE' });
        fetchAndRenderOrders();
      }
    });
  });
}

function setupOrderModal() {
  const addBtn = document.getElementById('addOrderBtn');
  const modal = document.getElementById('orderModal');
  const form = document.getElementById('orderForm');
  const cancelBtn = document.getElementById('cancelOrderModalBtn');
  const modalTitle = document.getElementById('orderModalTitle');

  if (addBtn) {
    addBtn.addEventListener('click', () => {
      openOrderModal();
    });
  }

  if (cancelBtn) {
    cancelBtn.addEventListener('click', () => {
      closeOrderModal();
    });
  }

  if (form) {
    form.addEventListener('submit', async function(e) {
      e.preventDefault();
      const id = document.getElementById('orderId').value;
      const symbol = document.getElementById('orderSymbol').value.trim().toUpperCase();
      const type = document.getElementById('orderType').value;
      const quantity = parseFloat(document.getElementById('orderQuantity').value);
      const buy_price = parseFloat(document.getElementById('orderBuyPrice').value);
      const sell_price = parseFloat(document.getElementById('orderSellPrice').value);
      const date = document.getElementById('orderDate').value;
      const pl = parseFloat(document.getElementById('orderPL').value);
      const order = { symbol, type, quantity, buy_price, sell_price, date, pl };
      if (id) {
        await fetch(`/api/orders/${id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(order)
        });
      } else {
        await fetch('/api/orders', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(order)
        });
      }
      form.reset();
      document.getElementById('orderId').value = '';
      closeOrderModal();
      fetchAndRenderOrders();
    });
  }

  if (modal) {
    modal.addEventListener('mousedown', (e) => {
      if (e.target === modal) {
        closeOrderModal();
      }
    });
  }

  function openOrderModal(edit = false) {
    if (modal) modal.classList.remove('hidden');
    if (modalTitle) modalTitle.textContent = edit ? 'Edit Order' : 'Add Order';
  }

  function closeOrderModal() {
    if (modal) modal.classList.add('hidden');
    if (form) form.reset();
    document.getElementById('orderId').value = '';
  }

  window.openEditOrder = function(order) {
    openOrderModal(true);
    document.getElementById('orderId').value = order.id;
    document.getElementById('orderSymbol').value = order.symbol;
    document.getElementById('orderType').value = order.type;
    document.getElementById('orderQuantity').value = order.quantity;
    document.getElementById('orderBuyPrice').value = order.buy_price ?? '';
    document.getElementById('orderSellPrice').value = order.sell_price ?? '';
    document.getElementById('orderDate').value = order.date ?? '';
    document.getElementById('orderPL').value = order.pl ?? '';
  };
}

// Expose functions globally for login refresh
window.fetchAndRenderOrders = fetchAndRenderOrders;

// Remove the following block:
// document.addEventListener('DOMContentLoaded', function() {
//   const btn = document.getElementById('ordersMinimizeBtn');
//   const icon = document.getElementById('ordersMinimizeIcon');
//   const actionBar = document.getElementById('ordersActionBar');
//   const content = document.getElementById('ordersContent');
//   if (btn && actionBar && content) {
//     // Initial state: hide action bar if content is collapsed/hidden
//     if (
//       content.style.maxHeight === '0px' ||
//       content.classList.contains('collapsed') ||
//       content.offsetHeight === 0
//     ) {
//       actionBar.style.display = 'none';
//     } else {
//       actionBar.style.display = 'flex';
//     }
//     // Set initial max-height for both to open or closed
//     if (content.style.maxHeight === '0px' || (icon && icon.classList.contains('fa-chevron-down'))) {
//       content.style.maxHeight = '0px';
//       actionBar.style.display = 'none';
//       actionBar.classList.remove('fade-scale-show', 'fade-scale-hide');
//       if (icon) {
//         icon.classList.remove('fa-chevron-up');
//         icon.classList.add('fa-chevron-down');
//       }
//     } else {
//       actionBar.style.maxHeight = actionBar.scrollHeight + 'px';
//       setTimeout(() => { actionBar.style.maxHeight = 'none'; }, 400);
//       actionBar.style.display = 'flex';
//       actionBar.classList.remove('fade-scale-hide');
//       actionBar.classList.add('fade-scale-show');
//       content.style.maxHeight = content.scrollHeight + 'px';
//       setTimeout(() => { content.style.maxHeight = 'none'; }, 400);
//       if (icon) {
//         icon.classList.remove('fa-chevron-down');
//         icon.classList.add('fa-chevron-up');
//       }
//     }
//     btn.addEventListener('click', function() {
//       // If either is closed, open both
//       if (actionBar.style.display === 'none' || content.style.maxHeight === '0px') {
//         actionBar.style.display = 'flex';
//         actionBar.classList.remove('fade-scale-show');
//         actionBar.classList.add('fade-scale-hide');
//         void actionBar.offsetWidth;
//         actionBar.classList.remove('fade-scale-hide');
//         actionBar.classList.add('fade-scale-show');
//         actionBar.addEventListener('transitionend', function handler(e) {
//           if (e.target === actionBar && (e.propertyName === 'opacity' || e.propertyName === 'transform')) {
//             actionBar.classList.remove('fade-scale-show');
//             actionBar.removeEventListener('transitionend', handler);
//           }
//         });
//         content.style.maxHeight = content.scrollHeight + 'px';
//         if (icon) {
//           icon.classList.remove('fa-chevron-down');
//           icon.classList.add('fa-chevron-up');
//         }
//         content.addEventListener('transitionend', function handler(e) {
//           if (e.target === content) {
//             content.style.maxHeight = 'none';
//             content.removeEventListener('transitionend', handler);
//           }
//         });
//       } else {
//         // Both are open, so close both
//         actionBar.classList.remove('fade-scale-show');
//         actionBar.classList.add('fade-scale-hide');
//         actionBar.addEventListener('transitionend', function handler(e) {
//           if (e.target === actionBar && (e.propertyName === 'opacity' || e.propertyName === 'transform')) {
//             actionBar.style.display = 'none';
//             actionBar.classList.remove('fade-scale-hide');
//             actionBar.removeEventListener('transitionend', handler);
//           }
//         });
//         content.style.maxHeight = content.scrollHeight + 'px';
//         void content.offsetWidth;
//         content.style.maxHeight = '0px';
//         if (icon) {
//           icon.classList.remove('fa-chevron-up');
//           icon.classList.add('fa-chevron-down');
//         }
//         content.addEventListener('transitionend', function handler(e) {
//           if (e.target === content) {
//             content.removeEventListener('transitionend', handler);
//           }
//         });
//       }
//     });
//   }
//   if (actionBar) actionBar.style.transition = '';
//   if (content) content.style.transition = 'max-height 0.4s cubic-bezier(0.4,0,0.2,1)';
//   // In the DOMContentLoaded handler, ensure that when ordersContent is hidden (maxHeight 0px), ordersActionBar is also hidden (display: none). When ordersContent is shown, ordersActionBar is shown (display: flex).
//   if (content) {
//     content.addEventListener('transitionend', function(e) {
//       if (e.target === content) {
//         if (content.style.maxHeight === '0px') {
//           actionBar.style.display = 'none';
//         } else {
//           actionBar.style.display = 'flex';
//         }
//       }
//     });
//   }
// });

// The global WidgetUtils.setupMinimizeButtons() in main.js will now handle minimize/maximize for this widget. 