export function initOrders() {
  fetchAndRenderOrders();
  setupOrderModal();
}

async function fetchAndRenderOrders() {
  const orders = await fetch('/api/orders').then(r => r.json());
  renderOrders(orders);
}

function renderOrders(orders) {
  if (!Array.isArray(orders)) {
    console.error("Orders is not an array", orders);
    orders = [];
  }
  const tbody = document.getElementById('ordersTbody');
  if (!tbody) return;
  tbody.innerHTML = '';
  if (!orders || orders.length === 0) {
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