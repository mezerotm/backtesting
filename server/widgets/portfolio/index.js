const API_PORTFOLIO = '/api/portfolio';

let portfolioCash = 0;

async function fetchPortfolioCash() {
  const resp = await fetch('/api/portfolio/cash');
  const data = await resp.json();
  portfolioCash = data.total_portfolio_cash || 0;
}

async function setPortfolioCash(val) {
  await fetch('/api/portfolio/cash', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ total_portfolio_cash: val })
  });
  portfolioCash = val;
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

function renderPositions(positions) {
  const tbody = document.getElementById('positionsTbody');
  if (!tbody) return;
  tbody.innerHTML = '';
  let totalValue = 0;
  positions.forEach(pos => {
    totalValue += pos.quantity * pos.buy_price;
  });
  // Add cash row at the top
  const cashLeft = portfolioCash - totalValue;
  const cashPercent = portfolioCash ? ((cashLeft / portfolioCash) * 100).toFixed(2) : '0.00';
  const cashRow = document.createElement('tr');
  cashRow.innerHTML = `
    <td class="px-3 py-2 text-green-400 font-bold">CASH</td>
    <td class="px-3 py-2 text-gray-200">-</td>
    <td class="px-3 py-2 text-gray-200">-</td>
    <td class="px-3 py-2 text-gray-200">-</td>
    <td class="px-3 py-2 text-green-300">${cashPercent}%</td>
    <td class="px-3 py-2 text-gray-200">-</td>
    <td class="px-3 py-2 text-gray-200">-</td>
    <td class="px-3 py-2 text-gray-400">$${cashLeft.toLocaleString(undefined, {minimumFractionDigits:2, maximumFractionDigits:2})}</td>
    <td class="px-3 py-2"></td>
  `;
  tbody.appendChild(cashRow);
  if (!positions.length) {
    tbody.innerHTML += '<tr><td colspan="9" class="text-center text-gray-400 py-4">No positions found.</td></tr>';
    return;
  }
  positions.forEach(pos => {
    const percent = portfolioCash ? ((pos.quantity * pos.buy_price) / portfolioCash * 100).toFixed(2) : '0.00';
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td class="px-3 py-2 text-white font-semibold">${pos.symbol}</td>
      <td class="px-3 py-2 text-gray-200">${pos.quantity}</td>
      <td class="px-3 py-2 text-gray-200">$${pos.buy_price.toFixed(2)}</td>
      <td class="px-3 py-2 text-gray-200">${pos.buy_date}</td>
      <td class="px-3 py-2 text-gray-200">${percent}%</td>
      <td class="px-3 py-2 text-gray-200">${pos.beta !== undefined ? pos.beta : ''}</td>
      <td class="px-3 py-2 text-gray-200">${pos.delta !== undefined ? pos.delta : ''}</td>
      <td class="px-3 py-2 text-gray-400">${pos.notes || ''}</td>
      <td class="px-3 py-2">
        <button class="edit-btn text-blue-400 hover:text-blue-300 mr-2" title="Edit" data-id="${pos.id}"><i class="fa-solid fa-pen"></i></button>
        <button class="delete-btn text-red-400 hover:text-red-300" title="Delete" data-id="${pos.id}"><i class="fa-solid fa-trash"></i></button>
      </td>
    `;
    tbody.appendChild(tr);
  });
  // Attach event listeners for edit/delete
  tbody.querySelectorAll('.edit-btn').forEach(btn => {
    btn.addEventListener('click', e => {
      const id = btn.getAttribute('data-id');
      const pos = positions.find(p => String(p.id) === String(id));
      if (pos) openEditModal(pos);
    });
  });
  tbody.querySelectorAll('.delete-btn').forEach(btn => {
    btn.addEventListener('click', e => {
      const id = btn.getAttribute('data-id');
      deletePosition(id);
    });
  });
}

function openEditModal(pos) {
  document.getElementById('modalTitle').textContent = 'Edit Position';
  document.getElementById('positionId').value = pos.id;
  document.getElementById('symbol').value = pos.symbol;
  document.getElementById('quantity').value = pos.quantity;
  document.getElementById('buyPrice').value = pos.buy_price;
  document.getElementById('buyDate').value = pos.buy_date;
  document.getElementById('beta').value = pos.beta !== undefined ? pos.beta : '';
  document.getElementById('delta').value = pos.delta !== undefined ? pos.delta : '';
  document.getElementById('notes').value = pos.notes || '';
  document.getElementById('positionModal').classList.remove('hidden');
}

function openAddModal() {
  document.getElementById('modalTitle').textContent = 'Add Position';
  document.getElementById('positionId').value = '';
  document.getElementById('symbol').value = '';
  document.getElementById('quantity').value = 1;
  document.getElementById('buyPrice').value = '';
  document.getElementById('buyDate').value = '';
  document.getElementById('beta').value = '';
  document.getElementById('delta').value = '';
  document.getElementById('notes').value = '';
  document.getElementById('positionModal').classList.remove('hidden');
}

function deletePosition(id) {
  if (!confirm('Delete this position?')) return;
  fetch(`${API_PORTFOLIO}/${id}`, { method: 'DELETE' })
    .then(() => fetchPositionsAndCash());
}

export function initPortfolio() {
  // Modal logic for settings
  const settingsBtn = document.getElementById('settingsBtn');
  const cashModal = document.getElementById('cashModal');
  const cancelCashModalBtn = document.getElementById('cancelCashModalBtn');
  if (settingsBtn && cashModal && cancelCashModalBtn) {
    settingsBtn.addEventListener('click', async () => {
      // Set input value to current cash
      await fetchPortfolioCash();
      const cashInput = document.getElementById('cash');
      if (cashInput) cashInput.value = portfolioCash;
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
      if (cashInput) {
        const val = parseFloat(cashInput.value);
        if (!isNaN(val) && val >= 0) {
          await setPortfolioCash(val);
        }
      }
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
      const quantity = parseFloat(document.getElementById('quantity').value);
      const buy_price = parseFloat(document.getElementById('buyPrice').value);
      const buy_date = document.getElementById('buyDate').value;
      const beta = parseFloat(document.getElementById('beta').value);
      const delta = parseFloat(document.getElementById('delta').value);
      const notes = document.getElementById('notes').value;
      const pos = { id: id ? parseInt(id) : Date.now(), symbol, quantity, buy_price, buy_date, notes };
      if (!isNaN(beta)) pos.beta = beta;
      if (!isNaN(delta)) pos.delta = delta;
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