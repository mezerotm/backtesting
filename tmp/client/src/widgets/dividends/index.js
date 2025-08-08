export function initDividends() {
  // Render the dividends widget HTML into the placeholder
  const dividendsWidget = document.getElementById('dividends-widget');
  if (dividendsWidget) {
    // Create the dividends widget HTML structure
    dividendsWidget.innerHTML = `
      <!-- Dividends Card -->
      <div class="bg-slate-800 rounded-xl shadow-sm widget-dividends p-6 w-full">
        <div class="flex justify-between items-center mb-0">
          <h2 class="text-lg font-bold text-white flex items-center gap-2">
            Dividends
            <button id="dividendsMinimizeBtn" class="ml-2 text-slate-400 hover:text-blue-400 focus:outline-none" title="Minimize Dividends" style="transition: transform 0.2s;"><i id="dividendsMinimizeIcon" class="fa-solid fa-chevron-down"></i></button>
          </h2>
        </div>
        <div id="dividendsContent" class="collapsed">
          <div class="overflow-x-auto overflow-y-auto max-h-96">
            <table class="min-w-full divide-y divide-slate-700 text-sm">
              <thead class="bg-slate-800 sticky top-0 z-10">
                <tr>
                  <th class="px-3 py-2 text-left text-xs font-medium text-gray-300 uppercase">Symbol</th>
                  <th class="px-3 py-2 text-left text-xs font-medium text-gray-300 uppercase">Amount</th>
                  <th class="px-3 py-2 text-left text-xs font-medium text-gray-300 uppercase">Date</th>
                  <th class="px-3 py-2 text-left text-xs font-medium text-gray-300 uppercase">Record Date</th>
                  <th class="px-3 py-2 text-left text-xs font-medium text-gray-300 uppercase">Payable Date</th>
                  <th class="px-3 py-2 text-left text-xs font-medium text-gray-300 uppercase">State</th>
                  <th class="px-3 py-2 text-left text-xs font-medium text-gray-300 uppercase">Source</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-700" id="dividendsTbody">
                <tr><td colspan="7" class="text-center text-gray-400 py-4">Loading...</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    `;
  }
  
  fetchAndRenderDividends();
}

// Expose functions globally for login refresh
window.fetchAndRenderDividends = fetchAndRenderDividends;

async function fetchAndRenderDividends() {
  try {
    console.log('[Dividends] Fetching dividends...');
    const response = await fetch('/api/dividends/received');
    const dividends = await response.json();
    console.log('[Dividends] Received response:', dividends);
    
    // Validate the response data
    if (window.DataModels && window.DataModels.validateData) {
      const validation = window.DataModels.validateData('dividends_response', dividends);
      if (!validation.success) {
        console.error('[Dividends] Data validation failed:', validation.errors);
        // Don't show error to user, just log it and continue with empty data
        console.warn('[Dividends] Continuing with empty dividends due to validation failure');
        renderDividends([]);
        return;
      }
      console.log('[Dividends] Data validation successful');
    }
    
    renderDividends(dividends);
  } catch (error) {
    console.error('Error fetching dividends:', error);
    renderDividends([]);
  }
}

function renderDividends(dividends) {
  const tbody = document.getElementById('dividendsTbody');
  
  if (!tbody) return;
  
  if (!dividends || dividends.length === 0) {
    tbody.innerHTML = '<tr><td colspan="7" class="text-center text-gray-400 py-4">No received dividends.</td></tr>';
    return;
  }
  
  tbody.innerHTML = '';
  
  // Sort by payable date (most recent first)
  dividends.sort((a, b) => new Date(b.payable_date) - new Date(a.payable_date));
  
  dividends.forEach(dividend => {
    const tr = document.createElement('tr');
    tr.className = 'border-b border-slate-700 hover:bg-slate-700';
    
    const amount = parseFloat(dividend.amount || 0);
    const amountClass = amount >= 0 ? 'text-green-400' : 'text-red-400';
    
    // Create actions cell with Robinhood badge if source is robinhood
    const actionsCell = dividend.source === 'robinhood' 
      ? '<span class="rh-badge">RH</span>'
      : '<span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-700 text-gray-300 border border-gray-600 cursor-not-allowed">Manual</span>';
    
    tr.innerHTML = `
      <td class="px-3 py-2 text-white font-semibold">${dividend.symbol || 'N/A'}</td>
      <td class="px-3 py-2 ${amountClass}">$${amount.toFixed(2)}</td>
      <td class="px-3 py-2 text-gray-200">${formatDate(dividend.date)}</td>
      <td class="px-3 py-2 text-gray-200">${formatDate(dividend.record_date)}</td>
      <td class="px-3 py-2 text-gray-200">${formatDate(dividend.payable_date)}</td>
      <td class="px-3 py-2 text-gray-200">${dividend.state || 'N/A'}</td>
      <td class="px-3 py-2">${actionsCell}</td>
    `;
    
    tbody.appendChild(tr);
  });
}

function formatDate(dateString) {
  if (!dateString) return 'N/A';
  try {
    return new Date(dateString).toLocaleDateString();
  } catch {
    return dateString;
  }
}

console.log('[Dividends] dividends/index.js script loaded'); 