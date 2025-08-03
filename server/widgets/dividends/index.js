export function initDividends() {
  fetchAndRenderDividends();
}

// Expose functions globally for login refresh
window.fetchAndRenderDividends = fetchAndRenderDividends;

async function fetchAndRenderDividends() {
  try {
    const response = await fetch('/api/dividends/received');
    const dividends = await response.json();
    renderDividends(dividends);
  } catch (error) {
    console.error('Error fetching dividends:', error);
  }
}

function renderDividends(dividends) {
  const tbody = document.getElementById('receivedDividendsTbody');
  
  if (!tbody) return;
  
  if (!dividends || dividends.length === 0) {
    tbody.innerHTML = '<tr><td colspan="5" class="text-center text-gray-400 py-4">No received dividends.</td></tr>';
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
      <td class="px-3 py-2 text-gray-200">${formatDate(dividend.record_date)}</td>
      <td class="px-3 py-2 text-gray-200">${formatDate(dividend.payable_date)}</td>
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

document.addEventListener('DOMContentLoaded', function() {
  console.log('[Dividends] DOMContentLoaded');
  const btn = document.getElementById('dividendsMinimizeBtn');
  const icon = document.getElementById('dividendsMinimizeIcon');
  const content = document.getElementById('dividendsContent');
  if (btn && content) {
    console.log('[Dividends] Minimize button and content found');
    // Set initial max-height based on visibility
    if (content.style.maxHeight === '0px' || (icon && icon.classList.contains('fa-chevron-down'))) {
      content.style.maxHeight = '0px';
      if (icon) {
        icon.classList.remove('fa-chevron-up');
        icon.classList.add('fa-chevron-down');
      }
      console.log('[Dividends] Content starts collapsed (by style or icon)');
    } else {
      content.style.maxHeight = content.scrollHeight + 'px';
      setTimeout(() => { content.style.maxHeight = 'none'; }, 400);
      if (icon) {
        icon.classList.remove('fa-chevron-down');
        icon.classList.add('fa-chevron-up');
      }
      console.log('[Dividends] Content starts expanded');
    }
    btn.addEventListener('click', function() {
      const computed = window.getComputedStyle(content);
      console.log('[Dividends] Minimize button clicked. Current style.maxHeight:', content.style.maxHeight, '| computed maxHeight:', computed.maxHeight, '| offsetHeight:', content.offsetHeight, '| scrollHeight:', content.scrollHeight, '| classList:', content.classList.value);
      if (content.style.maxHeight === '0px') {
        // Currently closed, so open
        content.style.maxHeight = content.scrollHeight + 'px';
        console.log('[Dividends] Opening content, set maxHeight to', content.style.maxHeight);
        if (icon) {
          icon.classList.remove('fa-chevron-down');
          icon.classList.add('fa-chevron-up');
        }
        content.addEventListener('transitionend', function handler(e) {
          if (e.target === content) {
            content.style.maxHeight = 'none';
            content.removeEventListener('transitionend', handler);
            console.log('[Dividends] Open animation complete, maxHeight set to none');
          }
        });
      } else {
        // Currently open, so close
        content.style.maxHeight = content.scrollHeight + 'px';
        void content.offsetWidth;
        content.style.maxHeight = '0px';
        console.log('[Dividends] Closing content, set maxHeight to 0px');
        if (icon) {
          icon.classList.remove('fa-chevron-up');
          icon.classList.add('fa-chevron-down');
        }
        content.addEventListener('transitionend', function handler(e) {
          if (e.target === content) {
            console.log('[Dividends] Close animation complete, maxHeight is', content.style.maxHeight);
            content.removeEventListener('transitionend', handler);
          }
        });
      }
    });
  } else {
    console.log('[Dividends] Minimize button or content NOT found');
  }
}); 