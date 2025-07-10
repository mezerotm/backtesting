export function initTrades() {
  fetchAndRenderTrades();
  setupTradeForm();
}

async function fetchAndRenderTrades() {
  const trades = await fetch('/api/trades').then(r => r.json());
  renderTrades(trades);
}

function renderTrades(trades) {
  const tbody = document.getElementById('tradesTbody');
  if (!tbody) return;
  tbody.innerHTML = '';
  if (!trades || trades.length === 0) {
    tbody.innerHTML = '<tr><td colspan="9" class="text-center text-gray-400 py-4">No trades found.</td></tr>';
    return;
  }
  trades.forEach(trade => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td class="px-3 py-2">${trade.id}</td>
      <td class="px-3 py-2">${trade.symbol}</td>
      <td class="px-3 py-2">${trade.type}</td>
      <td class="px-3 py-2">${trade.quantity}</td>
      <td class="px-3 py-2">${trade.buy_price ?? ''}</td>
      <td class="px-3 py-2">${trade.sell_price ?? ''}</td>
      <td class="px-3 py-2">${trade.date ?? ''}</td>
      <td class="px-3 py-2">${trade.pl ?? ''}</td>
      <td class="px-3 py-2">
        <button class="edit-btn text-blue-400 hover:text-blue-300 mr-2" data-id="${trade.id}"><i class="fa-solid fa-pen"></i></button>
        <button class="delete-btn text-red-400 hover:text-red-300" data-id="${trade.id}"><i class="fa-solid fa-trash"></i></button>
      </td>
    `;
    tbody.appendChild(tr);
  });
  tbody.querySelectorAll('.edit-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const id = btn.getAttribute('data-id');
      const trade = trades.find(t => String(t.id) === String(id));
      if (trade) openEditTrade(trade);
    });
  });
  tbody.querySelectorAll('.delete-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      const id = btn.getAttribute('data-id');
      if (confirm('Delete this trade?')) {
        await fetch(`/api/trades/${id}`, { method: 'DELETE' });
        fetchAndRenderTrades();
      }
    });
  });
}

function setupTradeForm() {
  const form = document.getElementById('tradeForm');
  const cancelBtn = document.getElementById('cancelTradeBtn');
  if (!form) return;
  form.addEventListener('submit', async function(e) {
    e.preventDefault();
    const id = document.getElementById('tradeId').value;
    const symbol = document.getElementById('tradeSymbol').value.trim().toUpperCase();
    const type = document.getElementById('tradeType').value;
    const quantity = parseFloat(document.getElementById('tradeQuantity').value);
    const buy_price = parseFloat(document.getElementById('tradeBuyPrice').value);
    const sell_price = parseFloat(document.getElementById('tradeSellPrice').value);
    const date = document.getElementById('tradeDate').value;
    const pl = parseFloat(document.getElementById('tradePL').value);
    const trade = { symbol, type, quantity, buy_price, sell_price, date, pl };
    if (id) {
      await fetch(`/api/trades/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(trade)
      });
    } else {
      await fetch('/api/trades', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(trade)
      });
    }
    form.reset();
    document.getElementById('tradeId').value = '';
    fetchAndRenderTrades();
  });
  cancelBtn.addEventListener('click', () => {
    form.reset();
    document.getElementById('tradeId').value = '';
  });
}

function openEditTrade(trade) {
  document.getElementById('tradeId').value = trade.id;
  document.getElementById('tradeSymbol').value = trade.symbol;
  document.getElementById('tradeType').value = trade.type;
  document.getElementById('tradeQuantity').value = trade.quantity;
  document.getElementById('tradeBuyPrice').value = trade.buy_price ?? '';
  document.getElementById('tradeSellPrice').value = trade.sell_price ?? '';
  document.getElementById('tradeDate').value = trade.date ?? '';
  document.getElementById('tradePL').value = trade.pl ?? '';
}

document.addEventListener('DOMContentLoaded', function() {
  console.log('[Trades] DOMContentLoaded');
  const btn = document.getElementById('tradesMinimizeBtn');
  const icon = document.getElementById('tradesMinimizeIcon');
  const content = document.getElementById('tradesContent');
  if (btn && content) {
    console.log('[Trades] Minimize button and content found');
    // Set initial max-height based on visibility
    if (content.style.maxHeight === '0px' || (icon && icon.classList.contains('fa-chevron-down'))) {
      content.style.maxHeight = '0px';
      if (icon) {
        icon.classList.remove('fa-chevron-up');
        icon.classList.add('fa-chevron-down');
      }
      console.log('[Trades] Content starts collapsed (by style or icon)');
    } else {
      content.style.maxHeight = content.scrollHeight + 'px';
      setTimeout(() => { content.style.maxHeight = 'none'; }, 400);
      if (icon) {
        icon.classList.remove('fa-chevron-down');
        icon.classList.add('fa-chevron-up');
      }
      console.log('[Trades] Content starts expanded');
    }
    btn.addEventListener('click', function() {
      console.log('[Trades] Minimize button clicked. Current maxHeight:', content.style.maxHeight);
      if (content.style.maxHeight === '0px') {
        // Currently closed, so open
        content.style.maxHeight = content.scrollHeight + 'px';
        console.log('[Trades] Opening content');
        if (icon) {
          icon.classList.remove('fa-chevron-down');
          icon.classList.add('fa-chevron-up');
        }
        content.addEventListener('transitionend', function handler(e) {
          if (e.target === content) {
            content.style.maxHeight = 'none';
            content.removeEventListener('transitionend', handler);
            console.log('[Trades] Open animation complete, maxHeight set to none');
          }
        });
      } else {
        // Currently open, so close
        content.style.maxHeight = content.scrollHeight + 'px';
        void content.offsetWidth;
        content.style.maxHeight = '0px';
        console.log('[Trades] Closing content');
        if (icon) {
          icon.classList.remove('fa-chevron-up');
          icon.classList.add('fa-chevron-down');
        }
      }
    });
  } else {
    console.log('[Trades] Minimize button or content NOT found');
  }
}); 