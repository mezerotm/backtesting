const API_PORTFOLIO = '/api/portfolio';

let portfolioCash = 0;
let portfolioBTC = 0;
let portfolioBTCDollar = 0;
let btcPrice = null;
let btcPriceFetched = false;
let btcAvgBuyPrice = 0;

async function fetchPortfolioSettings() {
  const resp = await fetch('/api/portfolio/settings', {
    credentials: 'include'  // Required to send authentication cookies
  });
  const data = await resp.json();
  console.log('[Portfolio] Fetched settings:', data);
  portfolioCash = data.total_portfolio_cash || 0;
  portfolioBTCDollar = data.total_portfolio_btc || 0;
  btcAvgBuyPrice = data.btc_avg_buy_price || 0;
  window._portfolioSettings = data; // for debugging
}

async function fetchPortfolioCash() {
  const resp = await fetch('/api/portfolio/cash', {
    credentials: 'include'  // Required to send authentication cookies
  });
  const data = await resp.json();
  portfolioCash = data.total_portfolio_cash || 0;
  portfolioBTCDollar = data.total_portfolio_btc || 0;
  btcAvgBuyPrice = data.btc_avg_buy_price || 0;
}

async function setPortfolioCashAndBTC(cashVal, btcDollarVal, btcAvgVal) {
  await fetch('/api/portfolio/cash', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',  // Required to send authentication cookies
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

async function fetchPositionsAndSettings() {
  await fetchPortfolioSettings();
  fetchPositions();
}

// Expose functions globally for login refresh
window.fetchPositionsAndSettings = fetchPositionsAndSettings;
window.fetchPositionsAndCash = fetchPositionsAndCash;

function fetchPositions() {
  // Add cache-busting parameter to ensure fresh data
  const timestamp = new Date().getTime();
  console.log('[Portfolio] Fetching positions...');
  fetch(API_PORTFOLIO + '/summary?t=' + timestamp, {
    credentials: 'include' // Required to send authentication cookies
  })
    .then(r => {
      console.log('[Portfolio] Response status:', r.status);
      return r.json();
    })
    .then(data => {
      console.log('[Portfolio] Received positions:', data);
      
      // Debug: Log the first position structure
      if (data.positions && data.positions.length > 0) {
        console.log('[Portfolio] First position structure:', data.positions[0]);
        console.log('[Portfolio] First position ID type:', typeof data.positions[0].id, 'Value:', data.positions[0].id);
      }
      
      // Validate the response data
      if (window.DataModels && window.DataModels.validateData) {
        const validation = window.DataModels.validateData('portfolio_summary', data);
        if (!validation.success) {
          console.error('[Portfolio] Data validation failed:', validation.errors);
          // Don't show error to user, just log it and continue with empty data
          console.warn('[Portfolio] Continuing with empty positions due to validation failure');
          renderPositions([]);
          return;
        }
        console.log('[Portfolio] Data validation successful');
      }
      
      // Safe to use validated data
      renderPositions(data.positions || []);
    })
    .catch(error => {
      console.error('[Portfolio] Error fetching positions:', error);
      renderPositions([]);
    });
}

async function renderPositions(positions) {
  console.log('[Portfolio] Rendering positions:', positions);
  const tbody = document.getElementById('positionsTbody');
  if (!tbody) {
    console.error('[Portfolio] positionsTbody element not found');
    return;
  }
  tbody.innerHTML = '';
  let totalValue = 0;
  positions.forEach(pos => {
    const positionValue = pos.market_value !== null && pos.market_value !== undefined ? pos.market_value : (pos.quantity * pos.buy_price);
    totalValue += positionValue || 0;
  });
  let btcValueForTotal = portfolioBTCDollar > 0 ? portfolioBTCDollar : 0;
  let cashLeft = portfolioCash - totalValue;
  if (cashLeft < 0) cashLeft = 0;
  let totalPortfolioValue = 0;
  if (totalValue > 0) totalPortfolioValue += totalValue;
  if (btcValueForTotal > 0) totalPortfolioValue += btcValueForTotal;
  if (cashLeft > 0) totalPortfolioValue += cashLeft;
  if (totalPortfolioValue === 0) totalPortfolioValue = 1; // Prevent divide by zero

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
  btcRow.className = 'border-b border-slate-700 hover:bg-slate-700';
  btcRow.innerHTML = `
    <td class="px-3 py-2 text-yellow-400 font-bold">BTC</td>
    <td class="px-3 py-2 text-gray-200">$${portfolioBTCDollar.toLocaleString(undefined, {minimumFractionDigits:2, maximumFractionDigits:2})}</td>
    <td class="px-3 py-2 text-gray-200">-</td>
    <td class="px-3 py-2 text-gray-200">-</td>
    <td class="px-3 py-2 text-yellow-300">${btcPercent}</td>
    <td class="px-3 py-2 text-gray-200">-</td>
    <td class="px-3 py-2 text-gray-200">-</td>
    <td class="px-3 py-2 text-gray-200">-</td>
    <td class="px-3 py-2 text-gray-200">-</td>
    <td class="px-3 py-2 text-gray-400">${btcNotes}</td>
    <td class="px-3 py-2"></td>
  `;
  tbody.appendChild(btcRow);

  // --- Positions ---
  if (!positions.length) {
    tbody.innerHTML += '<tr><td colspan="11" class="text-center text-gray-400 py-4">No positions found.</td></tr>';
  } else {
    positions.forEach(pos => {
      const amount = pos.quantity * pos.buy_price;
      const amountFormatted = amount !== undefined && amount !== null ? `$${amount.toLocaleString(undefined, {minimumFractionDigits:2, maximumFractionDigits:2})}` : '-';
      // Calculate percentage based on market value if available, otherwise use amount
      const positionValue = pos.market_value !== null && pos.market_value !== undefined ? pos.market_value : (pos.quantity * pos.buy_price);
      const percent = positionValue && totalPortfolioValue > 0 ? ((positionValue / totalPortfolioValue) * 100).toFixed(2) : '0.00';
      const isRobinhoodPosition = pos.source === 'robinhood';
      const actionButtons = isRobinhoodPosition ? 
        '<span class="rh-badge">RH</span>' : 
        `<button class="portfolio-edit-btn text-blue-400 hover:text-blue-300 mr-2" title="Edit" data-id="${pos.id}"><i class="fa-solid fa-pen"></i></button>
        <button class="portfolio-delete-btn text-red-400 hover:text-red-300" title="Delete" data-id="${pos.id}"><i class="fa-solid fa-trash"></i></button>`;
      const notes = pos.notes || '';
      const marketValue = pos.market_value !== undefined && pos.market_value !== null ? `$${pos.market_value.toLocaleString(undefined, {minimumFractionDigits:2, maximumFractionDigits:2})}` : '-';
      const todaysReturn = pos.todays_return !== undefined && pos.todays_return !== null ? `${pos.todays_return.toFixed(2)}%` : '-';
      const totalReturn = pos.total_return !== undefined && pos.total_return !== null ? `${pos.total_return.toFixed(2)}%` : '-';
      const beta = pos.beta !== undefined && pos.beta !== null ? pos.beta.toFixed(2) : '-';
      const delta = pos.delta !== undefined && pos.delta !== null ? pos.delta.toFixed(2) : '-';
      const tr = document.createElement('tr');
      tr.className = 'border-b border-slate-700 hover:bg-slate-700';
      tr.innerHTML = `
        <td class="px-3 py-2 text-white font-semibold">${pos.symbol}</td>
        <td class="px-3 py-2 text-gray-200">${amountFormatted}</td>
        <td class="px-3 py-2 text-gray-200">$${pos.buy_price.toFixed(2)}</td>
        <td class="px-3 py-2 text-gray-200">${marketValue}</td>
        <td class="px-3 py-2 text-gray-200">${percent}%</td>
        <td class="px-3 py-2 text-gray-200">${todaysReturn}</td>
        <td class="px-3 py-2 text-gray-200">${totalReturn}</td>
        <td class="px-3 py-2 text-gray-200">${beta}</td>
        <td class="px-3 py-2 text-gray-200">${delta}</td>
        <td class="px-3 py-2 text-gray-400">${notes}</td>
        <td class="px-3 py-2">${actionButtons}</td>
      `;
      tbody.appendChild(tr);
    });
  }

  // --- CASH row at the bottom ---
  const cashPercent = cashLeft > 0 ? ((cashLeft / totalPortfolioValue) * 100).toFixed(2) : '0.00';
  const cashRow = document.createElement('tr');
  cashRow.className = 'border-b border-slate-700 hover:bg-slate-700';
  cashRow.innerHTML = `
    <td class="px-3 py-2 text-green-400 font-bold">CASH</td>
    <td class="px-3 py-2 text-gray-200">$${cashLeft.toLocaleString(undefined, {minimumFractionDigits:2, maximumFractionDigits:2})}</td>
    <td class="px-3 py-2 text-gray-200">-</td>
    <td class="px-3 py-2 text-gray-200">-</td>
    <td class="px-3 py-2 text-green-300">${cashPercent}%</td>
    <td class="px-3 py-2 text-gray-200">-</td>
    <td class="px-3 py-2 text-gray-200">-</td>
    <td class="px-3 py-2 text-gray-200">-</td>
    <td class="px-3 py-2 text-gray-200">-</td>
    <td class="px-3 py-2 text-gray-400">$${cashLeft.toLocaleString(undefined, {minimumFractionDigits:2, maximumFractionDigits:2})}</td>
    <td class="px-3 py-2"></td>
  `;
  tbody.appendChild(cashRow);

  // Add event listeners for edit/delete buttons (use unique class names)
  tbody.querySelectorAll('.portfolio-edit-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const id = btn.getAttribute('data-id');
      const pos = positions.find(p => String(p.id) === String(id));
      if (pos && pos.source !== 'robinhood') {
        openEditModal(pos);
      } else if (pos && pos.source === 'robinhood') {
        Utils.showNotification('Cannot edit Robinhood positions. They are read-only.', 'warning');
      }
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
    fetch(`${API_PORTFOLIO}/${id}`, { method: 'DELETE', credentials: 'include' })
      .then(() => fetchPositionsAndCash());
  });
}

async function fetchRobinhoodStatus() {
  try {
    const resp = await fetch('/api/robinhood/status', {
      credentials: 'include' // Required to send authentication cookies
    });
    const data = await resp.json();
    
    const statusDiv = document.getElementById('robinhoodStatus');
    const lastPullTime = document.getElementById('lastPullTime');
    const positionsCount = document.getElementById('positionsCount');
    const tradesCount = document.getElementById('tradesCount');
    const dividendsCount = document.getElementById('dividendsCount');
    
    if (statusDiv && data.has_credentials) {
      statusDiv.classList.remove('hidden');
      
      if (lastPullTime) {
        if (data.last_pull) {
          const date = new Date(data.last_pull);
          lastPullTime.textContent = date.toLocaleString();
        } else {
          lastPullTime.textContent = 'Never';
        }
      }
      
      if (positionsCount) positionsCount.textContent = data.positions_count || 0;
      if (tradesCount) tradesCount.textContent = data.trades_count || 0;
      if (dividendsCount) dividendsCount.textContent = data.dividends_count || 0;
    } else if (statusDiv) {
      statusDiv.classList.add('hidden');
    }
  } catch (error) {
    console.error('Error fetching Robinhood status:', error);
  }
}

async function pullRobinhoodData(showSuccess = true) {
  const pullBtn = document.getElementById('pullRobinhoodBtn');
  const cashModal = document.getElementById('cashModal');
  const cancelCashModalBtn = document.getElementById('cancelCashModalBtn');
  const originalText = pullBtn ? pullBtn.textContent : '';
  
  if (pullBtn) {
    pullBtn.disabled = true;
    pullBtn.textContent = 'Pulling...';
    pullBtn.classList.add('opacity-60', 'cursor-not-allowed');
  }
  
  // Disable modal closing while pulling
  if (cancelCashModalBtn) {
    cancelCashModalBtn.disabled = true;
    cancelCashModalBtn.classList.add('opacity-60', 'cursor-not-allowed');
  }
  
  // Add visual feedback that modal is locked
  if (cashModal) {
    cashModal.classList.add('cursor-not-allowed');
    // Add a better overlay with progress bar
    const overlay = document.createElement('div');
    overlay.className = 'absolute inset-0 bg-black bg-opacity-50 flex items-center justify-center z-10';
    overlay.innerHTML = `
      <div class="bg-slate-700 rounded-lg p-6 max-w-md w-full mx-4">
        <div class="text-white text-center">
          <div class="text-lg font-semibold mb-2">Pulling Robinhood Data</div>
          <div class="text-sm opacity-75 mb-4">Please wait, this may take 30-60 seconds</div>
          <div class="flex items-center justify-center">
            <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mr-3"></div>
            <div id="robinhoodProgressText" class="text-sm">Connecting to Robinhood...</div>
          </div>
        </div>
      </div>
    `;
    overlay.id = 'robinhoodPullOverlay';
    const modalContent = cashModal.querySelector('.bg-slate-800');
    if (modalContent) {
      modalContent.style.position = 'relative';
      modalContent.appendChild(overlay);
    }
  }
  
  // Store original click handler and remove it temporarily
  const originalClickHandler = cashModal ? cashModal._originalClickHandler : null;
  if (cashModal && originalClickHandler) {
    cashModal.removeEventListener('mousedown', originalClickHandler);
  }
  
  // Show loading state
  const progressText = document.getElementById('robinhoodProgressText');
  if (progressText) progressText.textContent = 'Connecting to Robinhood...';
  
  try {
    // Update progress text during the process
    setTimeout(() => {
      if (progressText) progressText.textContent = 'Pulling positions and orders...';
    }, 2000);
    
    setTimeout(() => {
      if (progressText) progressText.textContent = 'Processing data and updating database...';
    }, 5000);
    
    const resp = await fetch('/api/robinhood/pull', { method: 'POST', credentials: 'include' });
    const data = await resp.json();
    
    // Show completion
    if (progressText) progressText.textContent = 'Complete!';
    
    if (resp.ok) {
      if (showSuccess) {
        const positions = data.positions || {};
        const orders = data.orders || {};
        const dividends = data.dividends || {};
        
        const totalPositions = (positions.created || 0) + (positions.updated || 0);
        const totalOrders = (orders.created || 0) + (orders.updated || 0);
        const totalDividends = (dividends.created || 0) + (dividends.updated || 0);
        
        let message = `Successfully pulled data: `;
        if (totalPositions > 0) message += `${totalPositions} positions `;
        if (totalOrders > 0) message += `${totalOrders} orders `;
        if (totalDividends > 0) message += `${totalDividends} dividends `;
        
        if (positions.deleted > 0) message += `(${positions.deleted} positions removed) `;
        
        Utils.showNotification(message, 'success');
      }
      await fetchRobinhoodStatus();
      fetchPositionsAndSettings(); // Refresh portfolio data
      // Close the modal after successful pull
      if (cashModal) cashModal.classList.add('hidden');
    } else {
      Utils.showNotification(`Error: ${data.detail}`, 'error');
    }
  } catch (error) {
    console.error('Error pulling Robinhood data:', error);
    Utils.showNotification('Error pulling Robinhood data', 'error');
  } finally {
    // Re-enable modal closing
    if (cancelCashModalBtn) {
      cancelCashModalBtn.disabled = false;
      cancelCashModalBtn.classList.remove('opacity-60', 'cursor-not-allowed');
    }
    
    // Remove visual feedback
    if (cashModal) {
      cashModal.classList.remove('cursor-not-allowed');
      const overlay = document.getElementById('robinhoodPullOverlay');
      if (overlay) {
        overlay.remove();
      }
    }
    
    // Restore original click handler
    if (cashModal && originalClickHandler) {
      cashModal.addEventListener('mousedown', originalClickHandler);
    }
    
    if (pullBtn) {
      pullBtn.disabled = false;
      pullBtn.textContent = originalText;
      pullBtn.classList.remove('opacity-60', 'cursor-not-allowed');
    }
  }
}

async function getBTCPrice() {
  if (btcPriceFetched && btcPrice !== null) return btcPrice;
  try {
    const resp = await fetch('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd', {
      credentials: 'include' // Required to send authentication cookies
    });
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

async function updatePullButtonState() {
  const pullBtn = document.getElementById('pullRobinhoodBtn');
  if (!pullBtn) return;
  
  try {
    console.log('[Portfolio] Updating pull button state...');
    
    // First fetch the settings if not already available
    if (!window._portfolioSettings) {
      console.log('[Portfolio] No settings cached, fetching...');
      await fetchPortfolioSettings();
    }
    
    const settings = window._portfolioSettings || {};
    console.log('[Portfolio] Settings:', settings);
    
    const isEnabled = settings.robinhood_enabled;
    const hasCredentials = settings.robinhood_username && settings.robinhood_password;
    
    console.log('[Portfolio] Robinhood enabled:', isEnabled, 'Has credentials:', hasCredentials);
    
    if (!isEnabled || !hasCredentials) {
      pullBtn.disabled = true;
      pullBtn.classList.add('opacity-50', 'cursor-not-allowed');
      pullBtn.classList.remove('bg-blue-600', 'hover:bg-blue-700');
      pullBtn.classList.add('bg-gray-600');
      pullBtn.textContent = isEnabled ? 'Missing Credentials' : 'Robinhood Disabled';
      console.log('[Portfolio] Button disabled:', pullBtn.textContent);
    } else {
      pullBtn.disabled = false;
      pullBtn.classList.remove('opacity-50', 'cursor-not-allowed', 'bg-gray-600');
      pullBtn.classList.add('bg-blue-600', 'hover:bg-blue-700');
      pullBtn.textContent = 'Pull Robinhood';
      console.log('[Portfolio] Button enabled');
    }
  } catch (error) {
    console.error('Error updating pull button state:', error);
    // Default to disabled state on error
    pullBtn.disabled = true;
    pullBtn.classList.add('opacity-50', 'cursor-not-allowed');
    pullBtn.textContent = 'Error Loading Settings';
  }
}

export function initPortfolio() {
  console.log('[Portfolio] initPortfolio function called');
  
  // Render the portfolio widget HTML into the placeholder
  const portfolioWidget = document.getElementById('portfolio-widget');
  if (portfolioWidget) {
    // Create the portfolio widget HTML structure
    portfolioWidget.innerHTML = `
      <!-- Add Position Toolbar -->
      <div id="portfolioActionBar" class="bg-slate-800 rounded-xl shadow flex justify-end gap-4 w-full p-6 mb-2 collapsed">
          <button id="addPositionBtn" class="primary-btn py-2 px-4 rounded-lg text-white bg-blue-600 hover:bg-blue-700 flex items-center gap-2">
              <i class="fa-solid fa-plus"></i> Add Position
          </button>
          <button id="settingsBtn" class="text-slate-400 hover:text-blue-400 focus:outline-none flex items-center justify-center rounded-full h-10 w-10" title="Portfolio Settings">
              <i class="fa-solid fa-gear text-xl"></i>
          </button>
      </div>
      <!-- Portfolio Card -->
      <div class="bg-slate-800 rounded-xl shadow-sm widget-portfolio p-6 mt-2 w-full">
          <div class="flex justify-between items-center mb-0">
              <h2 class="text-lg font-bold text-white flex items-center gap-2">
                  Portfolio
                  <button id="portfolioMinimizeBtn" class="ml-2 text-slate-400 hover:text-blue-400 focus:outline-none" title="Minimize Portfolio" style="transition: transform 0.2s;"><i id="portfolioMinimizeIcon" class="fa-solid fa-chevron-down"></i></button>
              </h2>
          </div>
          <div id="portfolioContent" class="collapsed">
              <div class="overflow-x-auto overflow-y-auto max-h-750px">
                  <table class="min-w-full divide-y divide-slate-700" id="positionsTable">
                      <thead>
                          <tr>
                              <th class="px-3 py-2 text-left text-xs font-medium text-gray-300 uppercase">Symbol</th>
                              <th class="px-3 py-2 text-left text-xs font-medium text-gray-300 uppercase">Amount ($)</th>
                              <th class="px-3 py-2 text-left text-xs font-medium text-gray-300 uppercase">Avg Buy Price</th>
                              <th class="px-3 py-2 text-left text-xs font-medium text-gray-300 uppercase">Market Value</th>
                              <th class="px-3 py-2 text-left text-xs font-medium text-gray-300 uppercase">% of Portfolio</th>
                              <th class="px-3 py-2 text-left text-xs font-medium text-gray-300 uppercase">Today's Return</th>
                              <th class="px-3 py-2 text-left text-xs font-medium text-gray-300 uppercase">Total Return</th>
                              <th class="px-3 py-2 text-left text-xs font-medium text-gray-300 uppercase">Beta</th>
                              <th class="px-3 py-2 text-left text-xs font-medium text-gray-300 uppercase">Delta</th>
                              <th class="px-3 py-2 text-left text-xs font-medium text-gray-300 uppercase">Notes</th>
                              <th class="px-3 py-2 text-left text-xs font-medium text-gray-300 uppercase">Actions</th>
                          </tr>
                      </thead>
                      <tbody class="divide-y divide-slate-700" id="positionsTbody">
                          <tr><td colspan="11" class="text-center text-gray-400 py-4">Loading...</td></tr>
                      </tbody>
                  </table>
              </div>
          </div>
      </div>
      
      <!-- Portfolio Settings Modal -->
      <div id="cashModal" class="fixed inset-0 bg-black bg-opacity-50 hidden z-50 flex items-center justify-center">
        <div class="bg-slate-800 rounded-lg p-6 w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto">
          <div class="flex justify-between items-center mb-4">
            <h2 class="text-xl font-bold text-white">Portfolio Settings</h2>
            <button id="cancelCashModalBtn" class="text-gray-400 hover:text-white">
              <i class="fas fa-times"></i>
            </button>
          </div>
          
          <form id="portfolioSettingsForm" class="space-y-4">
            <div class="space-y-4">
              <div>
                <label for="cash" class="block text-sm font-medium text-gray-300 mb-1">Cash Balance</label>
                <input type="number" id="cash" name="cash" step="0.01" required 
                       class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-white placeholder-gray-400">
              </div>
              
              <div>
                <label for="btcDollar" class="block text-sm font-medium text-gray-300 mb-1">BTC Dollar Value</label>
                <input type="number" id="btcDollar" name="btcDollar" step="0.01" 
                       class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-white placeholder-gray-400">
              </div>
              
              <div>
                <label for="btcAvgBuyPrice" class="block text-sm font-medium text-gray-300 mb-1">BTC Avg Buy Price</label>
                <input type="number" id="btcAvgBuyPrice" name="btcAvgBuyPrice" step="0.01" 
                       class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-white placeholder-gray-400">
              </div>
            </div>
            
            <div class="border-t border-slate-600 pt-4">
              <h3 class="text-lg font-semibold text-white mb-3">Robinhood Integration</h3>
              <div class="space-y-3">
                <div class="flex items-center">
                  <input type="checkbox" id="robinhoodEnabled" name="robinhoodEnabled" 
                         class="mr-2 rounded border-slate-600 bg-slate-700 text-blue-600 focus:ring-blue-500">
                  <label for="robinhoodEnabled" class="text-sm text-gray-300">Enable Robinhood Integration</label>
                </div>
                
                <div>
                  <label for="robinhoodUsername" class="block text-sm font-medium text-gray-300 mb-1">Robinhood Username</label>
                  <input type="text" id="robinhoodUsername" name="robinhoodUsername" 
                         class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-white placeholder-gray-400">
                </div>
                
                <div>
                  <label for="robinhoodPassword" class="block text-sm font-medium text-gray-300 mb-1">Robinhood Password</label>
                  <input type="password" id="robinhoodPassword" name="robinhoodPassword" 
                         class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-white placeholder-gray-400">
                </div>
                
                <div>
                  <label for="robinhoodMFA" class="block text-sm font-medium text-gray-300 mb-1">Robinhood MFA Code</label>
                  <input type="text" id="robinhoodMFA" name="robinhoodMFA" 
                         class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-white placeholder-gray-400">
                </div>
                
                <div class="pt-2">
                  <button type="button" id="pullRobinhoodBtn" class="w-full py-2 px-4 rounded-lg text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed disabled:bg-gray-600">
                    Pull Robinhood Data
                  </button>
                </div>
              </div>
            </div>
            
            <div class="flex justify-end gap-2">
              <button type="button" id="cancelCashModalBtn2" class="reset-btn py-2 px-4 rounded-lg text-white bg-gray-600 hover:bg-gray-700">
                Cancel
              </button>
              <button type="submit" class="primary-btn py-2 px-4 rounded-lg text-white bg-blue-600 hover:bg-blue-700">
                Save Settings
              </button>
            </div>
          </form>
        </div>
      </div>
      
      <!-- Position Modal (Add/Edit) -->
      <div id="positionModal" class="fixed inset-0 bg-black bg-opacity-50 hidden z-50 flex items-center justify-center">
        <div class="bg-slate-800 rounded-lg p-6 w-full max-w-md mx-4 max-h-[90vh] overflow-visible">
          <div class="flex justify-between items-center mb-6">
            <h2 id="modalTitle" class="text-xl font-bold text-white">Add Position</h2>
            <button id="cancelModalBtn" class="text-gray-400 hover:text-white">
              <i class="fas fa-times"></i>
            </button>
          </div>
          
          <form id="positionForm" class="space-y-4">
            <input type="hidden" id="positionId" name="id">
            
            <div>
              <label for="symbol" class="block text-sm font-medium text-gray-300 mb-2">Symbol</label>
              <div class="relative">
                <input type="text" id="symbol" name="symbol" required placeholder="Search for a symbol..." 
                       class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-white placeholder-gray-400">
                <div id="symbolDropdown" class="absolute w-full z-50"></div>
              </div>
            </div>
            
            <div>
              <label for="amount" class="block text-sm font-medium text-gray-300 mb-2">Amount ($)</label>
              <input type="number" id="amount" name="amount" step="0.01" required 
                     class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-white placeholder-gray-400">
            </div>
            
            <div>
              <label for="buyPrice" class="block text-sm font-medium text-gray-300 mb-2">Buy Price ($)</label>
              <input type="number" id="buyPrice" name="buyPrice" step="0.01" required 
                     class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-white placeholder-gray-400">
            </div>
            
            <div>
              <label for="notes" class="block text-sm font-medium text-gray-300 mb-2">Notes</label>
              <textarea id="notes" name="notes" rows="3" 
                        class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-white placeholder-gray-400 resize-none"></textarea>
            </div>
            
            <div class="flex justify-end gap-3 pt-4">
              <button type="button" id="cancelModalBtn2" class="px-4 py-2 rounded-lg text-white bg-gray-600 hover:bg-gray-700 transition-colors">
                Cancel
              </button>
              <button type="submit" class="px-4 py-2 rounded-lg text-white bg-blue-600 hover:bg-blue-700 transition-colors">
                Save Position
              </button>
            </div>
          </form>
        </div>
      </div>
    `;
  }
  
  // Modal logic for settings
  const settingsBtn = document.getElementById('settingsBtn');
  const cashModal = document.getElementById('cashModal');
  const cancelCashModalBtn = document.getElementById('cancelCashModalBtn');
  console.log('[Portfolio] settingsBtn:', settingsBtn, '| cashModal:', cashModal, '| cancelCashModalBtn:', cancelCashModalBtn);
  if (settingsBtn && cashModal && cancelCashModalBtn) {
    settingsBtn.addEventListener('click', async () => {
      try {
        await fetchPortfolioSettings();
        
        const cashInput = document.getElementById('cash');
        const btcDollarInput = document.getElementById('btcDollar');
        const btcAvgBuyPriceInput = document.getElementById('btcAvgBuyPrice');
        const robinhoodEnabledInput = document.getElementById('robinhoodEnabled');
        const robinhoodUsernameInput = document.getElementById('robinhoodUsername');
        const robinhoodPasswordInput = document.getElementById('robinhoodPassword');
        const robinhoodMFAInput = document.getElementById('robinhoodMFA');
        
        const data = window._portfolioSettings || {};
        
        if (cashInput) cashInput.value = portfolioCash;
        if (btcDollarInput) btcDollarInput.value = portfolioBTCDollar;
        if (btcAvgBuyPriceInput) btcAvgBuyPriceInput.value = btcAvgBuyPrice || '';
        if (robinhoodEnabledInput) robinhoodEnabledInput.checked = !!data.robinhood_enabled;
        if (robinhoodUsernameInput) robinhoodUsernameInput.value = data.robinhood_username || '';
        if (robinhoodPasswordInput) robinhoodPasswordInput.value = data.robinhood_password || '';
        if (robinhoodMFAInput) robinhoodMFAInput.value = data.robinhood_mfa || '';
        
        cashModal.classList.remove('hidden');
      } catch (error) {
        console.error('Error opening settings:', error);
        Utils.showNotification('Error loading settings', 'error');
      }
    });
    cancelCashModalBtn.addEventListener('click', () => {
      cashModal.classList.add('hidden');
    });
    
    // Handle the second cancel button
    const cancelCashModalBtn2 = document.getElementById('cancelCashModalBtn2');
    if (cancelCashModalBtn2) {
      cancelCashModalBtn2.addEventListener('click', () => {
        cashModal.classList.add('hidden');
      });
    }
    
    // Handle the pull Robinhood button in the modal
    const pullRobinhoodBtn = document.getElementById('pullRobinhoodBtn');
    if (pullRobinhoodBtn) {
      pullRobinhoodBtn.addEventListener('click', async () => {
        try {
          await pullRobinhoodData(true);
          // Refresh the portfolio data after pull
          fetchPositionsAndSettings();
        } catch (error) {
          console.error('Error pulling Robinhood data:', error);
          Utils.showNotification('Error pulling Robinhood data', 'error');
        }
      });
    }
    
    // Store the original click handler function
    const originalModalClickHandler = (e) => {
      if (e.target === cashModal) {
        cashModal.classList.add('hidden');
      }
    };
    
    cashModal.addEventListener('mousedown', originalModalClickHandler);
    cashModal._originalClickHandler = originalModalClickHandler;
  }
  // Handle portfolio settings form submission
  const portfolioSettingsForm = document.getElementById('portfolioSettingsForm');
  if (portfolioSettingsForm) {
    portfolioSettingsForm.addEventListener('submit', async function(e) {
      e.preventDefault();
      
      const cashInput = document.getElementById('cash');
      const btcDollarInput = document.getElementById('btcDollar');
      const btcAvgBuyPriceInput = document.getElementById('btcAvgBuyPrice');
      const robinhoodEnabledInput = document.getElementById('robinhoodEnabled');
      const robinhoodUsernameInput = document.getElementById('robinhoodUsername');
      const robinhoodPasswordInput = document.getElementById('robinhoodPassword');
      const robinhoodMFAInput = document.getElementById('robinhoodMFA');
      
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
      
      // Collect Robinhood fields
      const robinhoodEnabled = robinhoodEnabledInput ? robinhoodEnabledInput.checked : false;
      const robinhoodUsername = robinhoodUsernameInput ? robinhoodUsernameInput.value : '';
      const robinhoodPassword = robinhoodPasswordInput ? robinhoodPasswordInput.value : '';
      const robinhoodMFA = robinhoodMFAInput ? robinhoodMFAInput.value : '';
      
      // Send all fields
      const requestData = {
          total_portfolio_cash: cashVal,
          total_portfolio_btc: btcDollarVal,
          btc_avg_buy_price: btcAvgVal,
          robinhood_enabled: robinhoodEnabled,
          robinhood_username: robinhoodUsername,
          robinhood_password: robinhoodPassword,
          robinhood_mfa: robinhoodMFA
      };
      
      console.log('Sending portfolio settings:', requestData);
      
      const response = await fetch('/api/portfolio/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include', // Required to send authentication cookies
        body: JSON.stringify(requestData)
      });
      
      console.log('Portfolio settings response status:', response.status);
      const responseData = await response.json();
      console.log('Portfolio settings response:', responseData);
      
      if (!response.ok) {
        throw new Error(`Failed to save settings: ${responseData.detail || 'Unknown error'}`);
      }
      
      cashModal.classList.add('hidden');
      fetchPositionsAndSettings(); // Refresh table
      updatePullButtonState(); // Update pull button state
    });
  }
  // Portfolio CRUD logic
  const addPositionBtn = document.getElementById('addPositionBtn');
  if (addPositionBtn) {
    addPositionBtn.addEventListener('click', openAddModal);
  }
  const cancelModalBtn = document.getElementById('cancelModalBtn');
  const cancelModalBtn2 = document.getElementById('cancelModalBtn2');
  if (cancelModalBtn) {
    cancelModalBtn.addEventListener('click', () => {
      document.getElementById('positionModal').classList.add('hidden');
    });
  }
  if (cancelModalBtn2) {
    cancelModalBtn2.addEventListener('click', () => {
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
          credentials: 'include', // Required to send authentication cookies
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
          credentials: 'include', // Required to send authentication cookies
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
      if (symbolDropdown) {
          symbolDropdown.innerHTML = '';
      }
      symbolDropdownOpen = false;
      symbolDropdownIndex = -1;
  }

  function renderSymbolDropdown(suggestions) {
      if (!suggestions.length) {
          closeSymbolDropdown();
          return;
      }
      if (symbolDropdown) {
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
  }

  async function fetchSymbolSuggestionsPortfolio(query) {
      if (!query || query.length < 1) {
          closeSymbolDropdown();
          return;
      }
      try {
          const resp = await fetch(`/api/portfolio/search-symbols?query=${encodeURIComponent(query)}`, {
            credentials: 'include' // Required to send authentication cookies
          });
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

  if (symbolDropdown) {
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
  }
  const positionModal = document.getElementById('positionModal');
  if (positionModal) {
      positionModal.addEventListener('mousedown', (e) => {
          if (e.target === positionModal) {
              positionModal.classList.add('hidden');
          }
      });
  }
  
  // Portfolio Settings Modal click handler (cashModal already declared above)
  if (cashModal) {
      cashModal.addEventListener('mousedown', (e) => {
          if (e.target === cashModal) {
              cashModal.classList.add('hidden');
          }
      });
  }
  
  // Initialize Robinhood pull button
  const pullBtn = document.getElementById('pullRobinhoodBtn');
  if (pullBtn) {
    pullBtn.addEventListener('click', () => pullRobinhoodData());
    // Update button state based on Robinhood settings
    updatePullButtonState();
  }
  
  // Auto-pull handled by global timer in main.js
  // setInterval(() => pullRobinhoodData(false), 10 * 60 * 1000);
  
  // Initial data load
  fetchPositionsAndCash();
  
  // Refresh symbol data to get current market prices
  fetch('/api/portfolio/refresh-symbols', { method: 'POST' })
    .then(() => {
      console.log('[Portfolio] Symbol data refreshed');
      fetchPositionsAndCash(); // Reload with fresh market data
    })
    .catch(err => {
      console.error('[Portfolio] Failed to refresh symbol data:', err);
      // Still load positions even if symbol refresh fails
    });
}

console.log('[Portfolio] portfolio/index.js script loaded'); 