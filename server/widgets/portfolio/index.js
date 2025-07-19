const API_PORTFOLIO = '/api/portfolio';

let portfolioCash = 0;
let portfolioBTC = 0;
let portfolioBTCDollar = 0;
let btcPrice = null;
let btcPriceFetched = false;
let btcAvgBuyPrice = 0;

async function fetchPortfolioCash() {
  const resp = await fetch('/api/portfolio/cash');
  const data = await resp.json();
  portfolioCash = data.total_portfolio_cash || 0;
  portfolioBTCDollar = data.total_portfolio_btc || 0;
  btcAvgBuyPrice = data.btc_avg_buy_price || 0;
}

async function setPortfolioCashAndBTC(cashVal, btcDollarVal, btcAvgVal) {
  await fetch('/api/portfolio/cash', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ total_portfolio_cash: cashVal, total_portfolio_btc: btcDollarVal, btc_avg_buy_price: btcAvgVal })
  });
  portfolioCash = cashVal;
  portfolioBTCDollar = btcDollarVal;
  btcAvgBuyPrice = btcAvgVal;
}

async function fetchPositionsAndCash() {
  await fetchPortfolioCash();
  fetchPositions();
}

function fetchPositions() {
  fetch(API_PORTFOLIO + '/')
    .then(r => r.json())
    .then(data => renderPositions(data))
    .catch(() => renderPositions([]));
}

async function renderPositions(positions) {
  const tbody = document.getElementById('positionsTbody');
  if (!tbody) return;
  tbody.innerHTML = '';
  let totalValue = 0;
  positions.forEach(pos => {
    totalValue += pos.quantity * pos.buy_price;
  });
  let btcValueForTotal = portfolioBTCDollar > 0 ? portfolioBTCDollar : 0;
  let cashLeft = portfolioCash - totalValue;
  if (cashLeft < 0) cashLeft = 0;
  let totalPortfolioValue = 0;
  if (totalValue > 0) totalPortfolioValue += totalValue;
  if (btcValueForTotal > 0) totalPortfolioValue += btcValueForTotal;
  if (cashLeft > 0) totalPortfolioValue += cashLeft;
  if (totalPortfolioValue === 0) totalPortfolioValue = 1; // Prevent divide by zero, will show 0.00%

  // --- BTC row at the top ---
  let btcPercent = '-';
  let btcNotes = '-';
  if (portfolioBTCDollar && btcAvgBuyPrice) {
    btcNotes = `₿${(portfolioBTCDollar / btcAvgBuyPrice).toFixed(8)}`;
    btcPercent = portfolioBTCDollar > 0 ? ((portfolioBTCDollar / totalPortfolioValue) * 100).toFixed(2) + '%' : '-';
  } else if (portfolioBTCDollar) {
    btcNotes = '';
    btcPercent = portfolioBTCDollar > 0 ? ((portfolioBTCDollar / totalPortfolioValue) * 100).toFixed(2) + '%' : '-';
  }
  const btcRow = document.createElement('tr');
  btcRow.innerHTML = `
    <td class="px-3 py-2 text-yellow-400 font-bold">BTC</td>
    <td class="px-3 py-2 text-gray-200">$${portfolioBTCDollar.toLocaleString(undefined, {minimumFractionDigits:2, maximumFractionDigits:2})}</td>
    <td class="px-3 py-2 text-gray-200">-</td>
    <td class="px-3 py-2 text-yellow-300">${btcPercent}</td>
    <td class="px-3 py-2 text-gray-200"></td>
    <td class="px-3 py-2 text-gray-200"></td>
    <td class="px-3 py-2 text-gray-400">${btcNotes}</td>
    <td class="px-3 py-2"></td>
  `;
  tbody.appendChild(btcRow);

  // --- Positions ---
  if (!positions.length) {
    tbody.innerHTML += '<tr><td colspan="8" class="text-center text-gray-400 py-4">No positions found.</td></tr>';
  } else {
    positions.forEach(pos => {
      const amount = pos.quantity * pos.buy_price;
      const percent = amount > 0 ? ((amount / totalPortfolioValue) * 100).toFixed(2) : '0.00';
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td class="px-3 py-2 text-white font-semibold">${pos.symbol}</td>
        <td class="px-3 py-2 text-gray-200">$${amount.toFixed(2)}</td>
        <td class="px-3 py-2 text-gray-200">$${pos.buy_price.toFixed(2)}</td>
        <td class="px-3 py-2 text-gray-200">${percent}%</td>
        <td class="px-3 py-2 text-gray-200"></td>
        <td class="px-3 py-2 text-gray-200"></td>
        <td class="px-3 py-2 text-gray-400">${pos.notes || ''}</td>
        <td class="px-3 py-2">
          <button class="portfolio-edit-btn text-blue-400 hover:text-blue-300 mr-2" title="Edit" data-id="${pos.id}"><i class="fa-solid fa-pen"></i></button>
          <button class="portfolio-delete-btn text-red-400 hover:text-red-300" title="Delete" data-id="${pos.id}"><i class="fa-solid fa-trash"></i></button>
        </td>
      `;
      tbody.appendChild(tr);
    });
  }

  // --- CASH row at the bottom ---
  const cashPercent = cashLeft > 0 ? ((cashLeft / totalPortfolioValue) * 100).toFixed(2) : '0.00';
  const cashRow = document.createElement('tr');
  cashRow.innerHTML = `
    <td class="px-3 py-2 text-green-400 font-bold">CASH</td>
    <td class="px-3 py-2 text-gray-200">$${cashLeft.toLocaleString(undefined, {minimumFractionDigits:2, maximumFractionDigits:2})}</td>
    <td class="px-3 py-2 text-gray-200">-</td>
    <td class="px-3 py-2 text-green-300">${cashPercent}%</td>
    <td class="px-3 py-2 text-gray-200"></td>
    <td class="px-3 py-2 text-gray-200"></td>
    <td class="px-3 py-2 text-gray-400">$${cashLeft.toLocaleString(undefined, {minimumFractionDigits:2, maximumFractionDigits:2})}</td>
    <td class="px-3 py-2"></td>
  `;
  tbody.appendChild(cashRow);

  // Add event listeners for edit/delete buttons (use unique class names)
  tbody.querySelectorAll('.portfolio-edit-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const id = btn.getAttribute('data-id');
      const pos = positions.find(p => String(p.id) === String(id));
      if (pos) openEditModal(pos);
    });
  });
  tbody.querySelectorAll('.portfolio-delete-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const id = btn.getAttribute('data-id');
      deletePosition(id);
    });
  });
}

function openEditModal(pos) {
  document.getElementById('modalTitle').textContent = 'Edit Position';
  document.getElementById('positionId').value = pos.id;
  document.getElementById('symbol').value = pos.symbol;
  document.getElementById('amount').value = (pos.quantity * pos.buy_price).toFixed(2);
  document.getElementById('buyPrice').value = pos.buy_price;
  document.getElementById('notes').value = pos.notes || '';
  document.getElementById('positionModal').classList.remove('hidden');
}

function openAddModal() {
  document.getElementById('modalTitle').textContent = 'Add Position';
  document.getElementById('positionId').value = '';
  document.getElementById('symbol').value = '';
  document.getElementById('amount').value = '';
  document.getElementById('buyPrice').value = '';
  document.getElementById('notes').value = '';
  document.getElementById('positionModal').classList.remove('hidden');
}

function showPortfolioConfirmationModal(message, confirmCallback) {
  // Use the global confirmation modal from WidgetUtils
  if (window.WidgetUtils && window.WidgetUtils.showConfirmationModal) {
    window.WidgetUtils.showConfirmationModal(message, confirmCallback);
  } else {
    // Fallback to the original implementation
    const modal = document.getElementById('portfolioConfirmModal');
    const confirmBtn = document.getElementById('confirmPortfolioModalBtn');
    const cancelBtn = document.getElementById('cancelPortfolioConfirmModalBtn');
    const msg = document.getElementById('portfolioConfirmMessage');
    if (modal && confirmBtn && cancelBtn && msg) {
      modal.classList.remove('hidden');
      msg.textContent = message;
      confirmBtn.onclick = null;
      cancelBtn.onclick = null;
      modal.onmousedown = null;
      confirmBtn.onclick = () => {
        modal.classList.add('hidden');
        confirmCallback();
      };
      cancelBtn.onclick = () => {
        modal.classList.add('hidden');
      };
      modal.onmousedown = (e) => {
        if (e.target === modal) {
          modal.classList.add('hidden');
        }
      };
    }
  }
}

function deletePosition(id) {
  showPortfolioConfirmationModal('Are you sure you want to delete this position?', () => {
    fetch(`${API_PORTFOLIO}/${id}`, { method: 'DELETE' })
      .then(() => fetchPositionsAndCash());
  });
}

async function getBTCPrice() {
  if (btcPriceFetched && btcPrice !== null) return btcPrice;
  try {
    const resp = await fetch('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd');
    if (!resp.ok) throw new Error('Failed to fetch BTC price');
    const data = await resp.json();
    btcPrice = data.bitcoin.usd;
    btcPriceFetched = true;
    return btcPrice;
  } catch (e) {
    btcPrice = null;
    btcPriceFetched = true;
    console.warn('Failed to fetch BTC price from CoinGecko:', e);
    return null;
  }
}

export function initPortfolio() {
  console.log('[Portfolio] initPortfolio function called');
  // Modal logic for settings
  const settingsBtn = document.getElementById('settingsBtn');
  const cashModal = document.getElementById('cashModal');
  const cancelCashModalBtn = document.getElementById('cancelCashModalBtn');
  console.log('[Portfolio] settingsBtn:', settingsBtn, '| cashModal:', cashModal, '| cancelCashModalBtn:', cancelCashModalBtn);
  if (settingsBtn && cashModal && cancelCashModalBtn) {
    settingsBtn.addEventListener('click', async () => {
      await fetchPortfolioCash();
      const cashInput = document.getElementById('cash');
      const btcDollarInput = document.getElementById('btcDollar');
      const btcAvgBuyPriceInput = document.getElementById('btcAvgBuyPrice');
      console.log('[Portfolio] Opening cash modal. cashInput:', cashInput, '| btcDollarInput:', btcDollarInput, '| btcAvgBuyPriceInput:', btcAvgBuyPriceInput);
      if (cashInput) cashInput.value = portfolioCash;
      if (btcDollarInput) btcDollarInput.value = portfolioBTCDollar;
      if (btcAvgBuyPriceInput) btcAvgBuyPriceInput.value = btcAvgBuyPrice || '';
      cashModal.classList.remove('hidden');
    });
    cancelCashModalBtn.addEventListener('click', () => {
      cashModal.classList.add('hidden');
    });
    cashModal.addEventListener('mousedown', (e) => {
      if (e.target === cashModal) {
        cashModal.classList.add('hidden');
      }
    });
  }
  // Handle cash form submission
  const cashForm = document.getElementById('cashForm');
  if (cashForm) {
    cashForm.addEventListener('submit', async function(e) {
      e.preventDefault();
      const cashInput = document.getElementById('cash');
      const btcDollarInput = document.getElementById('btcDollar');
      const btcAvgBuyPriceInput = document.getElementById('btcAvgBuyPrice');
      let cashVal = portfolioCash;
      let btcDollarVal = portfolioBTCDollar;
      let btcAvgVal = btcAvgBuyPrice;
      if (cashInput) {
        const val = parseFloat(cashInput.value);
        if (!isNaN(val) && val >= 0) {
          cashVal = val;
        }
      }
      if (btcDollarInput) {
        const val = parseFloat(btcDollarInput.value);
        if (!isNaN(val) && val >= 0) {
          btcDollarVal = val;
        }
      }
      if (btcAvgBuyPriceInput) {
        const val = parseFloat(btcAvgBuyPriceInput.value);
        if (!isNaN(val) && val >= 0) {
          btcAvgVal = val;
        } else {
          btcAvgVal = '';
        }
      }
      await setPortfolioCashAndBTC(cashVal, btcDollarVal, btcAvgVal);
      cashModal.classList.add('hidden');
      fetchPositionsAndCash(); // Refresh table
    });
  }
  // Portfolio CRUD logic
  const addPositionBtn = document.getElementById('addPositionBtn');
  if (addPositionBtn) {
    addPositionBtn.addEventListener('click', openAddModal);
  }
  const cancelModalBtn = document.getElementById('cancelModalBtn');
  if (cancelModalBtn) {
    cancelModalBtn.addEventListener('click', () => {
      document.getElementById('positionModal').classList.add('hidden');
    });
  }
  const positionForm = document.getElementById('positionForm');
  if (positionForm) {
    positionForm.addEventListener('submit', function(e) {
      e.preventDefault();
      const id = document.getElementById('positionId').value;
      const symbol = document.getElementById('symbol').value.trim().toUpperCase();
      const amount = parseFloat(document.getElementById('amount').value);
      const buy_price = parseFloat(document.getElementById('buyPrice').value);
      const notes = document.getElementById('notes').value;
      if (isNaN(amount) || isNaN(buy_price) || buy_price <= 0) return;
      const quantity = amount / buy_price;
      const pos = { id: id ? parseInt(id) : Date.now(), symbol, quantity, buy_price, notes };
      if (id) {
        // Update
        fetch(`${API_PORTFOLIO}/${id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(pos)
        }).then(() => {
          fetchPositionsAndCash();
          document.getElementById('positionModal').classList.add('hidden');
        });
      } else {
        // Add
        fetch(API_PORTFOLIO + '/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(pos)
        }).then(() => {
          fetchPositionsAndCash();
          document.getElementById('positionModal').classList.add('hidden');
        });
      }
    });
  }
  const symbolInput = document.getElementById('symbol');
  const symbolDropdown = document.getElementById('symbolDropdown');
  let symbolSuggestions = [];
  let symbolDropdownOpen = false;
  let symbolDropdownIndex = -1;

  function debounce(fn, delay) {
      let timeout;
      return function(...args) {
          clearTimeout(timeout);
          timeout = setTimeout(() => fn.apply(this, args), delay);
      };
  }

  function closeSymbolDropdown() {
      symbolDropdown.innerHTML = '';
      symbolDropdownOpen = false;
      symbolDropdownIndex = -1;
  }

  function renderSymbolDropdown(suggestions) {
      if (!suggestions.length) {
          closeSymbolDropdown();
          return;
      }
      symbolDropdown.innerHTML = `<div class="absolute z-50 w-full bg-slate-800 border border-slate-600 rounded-b-lg shadow-lg mt-0.5 max-h-56 overflow-y-auto select-none">
          ${suggestions.map((item, i) => `
              <div class="px-4 py-2 cursor-pointer hover:bg-blue-700 ${i === symbolDropdownIndex ? 'bg-blue-700 text-white' : 'text-gray-200'}" data-index="${i}">
                  <span class="font-semibold">${item.symbol}</span>
                  <span class="ml-2 text-xs text-gray-400">${item.name ? item.name : ''}</span>
              </div>
          `).join('')}
      </div>`;
      symbolDropdownOpen = true;
  }

  async function fetchSymbolSuggestionsPortfolio(query) {
      if (!query || query.length < 1) {
          closeSymbolDropdown();
          return;
      }
      try {
          const resp = await fetch(`/api/portfolio/search-symbols?query=${encodeURIComponent(query)}`);
          if (!resp.ok) return;
          const data = await resp.json();
          symbolSuggestions = data;
          renderSymbolDropdown(symbolSuggestions);
      } catch (e) {
          closeSymbolDropdown();
      }
  }
  const debouncedFetchSymbolsPortfolio = debounce((e) => {
      fetchSymbolSuggestionsPortfolio(e.target.value.trim().toUpperCase());
  }, 250);
  if (symbolInput) {
      symbolInput.addEventListener('input', debouncedFetchSymbolsPortfolio);
      symbolInput.addEventListener('keydown', (e) => {
          if (!symbolDropdownOpen || !symbolSuggestions.length) return;
          if (e.key === 'ArrowDown') {
              e.preventDefault();
              symbolDropdownIndex = (symbolDropdownIndex + 1) % symbolSuggestions.length;
              renderSymbolDropdown(symbolSuggestions);
          } else if (e.key === 'ArrowUp') {
              e.preventDefault();
              symbolDropdownIndex = (symbolDropdownIndex - 1 + symbolSuggestions.length) % symbolSuggestions.length;
              renderSymbolDropdown(symbolSuggestions);
          } else if (e.key === 'Enter') {
              if (symbolDropdownIndex >= 0 && symbolDropdownIndex < symbolSuggestions.length) {
                  symbolInput.value = symbolSuggestions[symbolDropdownIndex].symbol;
                  closeSymbolDropdown();
              }
          } else if (e.key === 'Escape') {
              closeSymbolDropdown();
          }
      });
      symbolInput.addEventListener('blur', () => {
          setTimeout(closeSymbolDropdown, 150);
      });
  }

  symbolDropdown.addEventListener('mousedown', (e) => {
      const target = e.target.closest('[data-index]');
      if (target) {
          const idx = parseInt(target.getAttribute('data-index'));
          if (!isNaN(idx) && symbolSuggestions[idx]) {
              symbolInput.value = symbolSuggestions[idx].symbol;
              closeSymbolDropdown();
          }
      }
  });
  const positionModal = document.getElementById('positionModal');
  if (positionModal) {
      positionModal.addEventListener('mousedown', (e) => {
          if (e.target === positionModal) {
              positionModal.classList.add('hidden');
          }
      });
  }
  fetchPositionsAndCash();
}

console.log('[Portfolio] portfolio/index.js script loaded');
document.addEventListener('DOMContentLoaded', function() {
  console.log('[Portfolio] DOMContentLoaded event fired');
  const btn = document.getElementById('portfolioMinimizeBtn');
  const icon = document.getElementById('portfolioMinimizeIcon');
  const actionBar = document.getElementById('portfolioActionBar');
  const content = document.getElementById('portfolioContent');
  console.log('[Portfolio] btn:', btn, '| icon:', icon, '| actionBar:', actionBar, '| content:', content);
  if (btn && actionBar && content) {
    // Set initial max-height for both to open
    actionBar.style.maxHeight = actionBar.scrollHeight + 'px';
    setTimeout(() => { actionBar.style.maxHeight = 'none'; }, 400);
    content.style.maxHeight = content.scrollHeight + 'px';
    setTimeout(() => { content.style.maxHeight = 'none'; }, 400);
    console.log('[Portfolio] Initial actionBar maxHeight:', actionBar.style.maxHeight, '| content maxHeight:', content.style.maxHeight);
    btn.addEventListener('click', function() {
      console.log('[Portfolio] Minimize button clicked. actionBar display:', actionBar.style.display, '| content maxHeight:', content.style.maxHeight);
      // If either is closed, open both
      if (actionBar.style.display === 'none' || content.style.maxHeight === '0px') {
        actionBar.style.display = 'flex';
        actionBar.classList.remove('fade-scale-show');
        actionBar.classList.add('fade-scale-hide');
        // Force reflow to apply the initial state
        void actionBar.offsetWidth;
        actionBar.classList.remove('fade-scale-hide');
        actionBar.classList.add('fade-scale-show');
        // Remove the show class after transition
        actionBar.addEventListener('transitionend', function handler(e) {
          if (e.target === actionBar && (e.propertyName === 'opacity' || e.propertyName === 'transform')) {
            actionBar.classList.remove('fade-scale-show');
            actionBar.removeEventListener('transitionend', handler);
          }
        });
        content.style.maxHeight = content.scrollHeight + 'px';
        console.log('[Portfolio] Opening actionBar and content');
        if (icon) {
          icon.classList.remove('fa-chevron-down');
          icon.classList.add('fa-chevron-up');
        }
        content.addEventListener('transitionend', function handler(e) {
          if (e.target === content) {
            content.style.maxHeight = 'none';
            console.log('[Portfolio] content open animation complete, maxHeight set to none');
            content.removeEventListener('transitionend', handler);
          }
        });
      } else {
        // Both are open, so close both
        actionBar.classList.remove('fade-scale-show');
        actionBar.classList.add('fade-scale-hide');
        actionBar.addEventListener('transitionend', function handler(e) {
          if (e.target === actionBar && (e.propertyName === 'opacity' || e.propertyName === 'transform')) {
            actionBar.style.display = 'none';
            actionBar.classList.remove('fade-scale-hide');
            actionBar.removeEventListener('transitionend', handler);
          }
        });
        content.style.maxHeight = content.scrollHeight + 'px';
        void content.offsetWidth;
        content.style.maxHeight = '0px';
        console.log('[Portfolio] Closing actionBar and content');
        if (icon) {
          icon.classList.remove('fa-chevron-up');
          icon.classList.add('fa-chevron-down');
        }
        content.addEventListener('transitionend', function handler(e) {
          if (e.target === content) {
            console.log('[Portfolio] content close animation complete, maxHeight is', content.style.maxHeight);
            content.removeEventListener('transitionend', handler);
          }
        });
      }
    });
  } else {
    console.log('[Portfolio] Minimize button, actionBar, or content NOT found');
  }
  if (actionBar) actionBar.style.transition = '';
  if (content) content.style.transition = 'max-height 0.4s cubic-bezier(0.4,0,0.2,1)';
}); 