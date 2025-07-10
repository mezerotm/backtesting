export function initProfitLoss() {
  fetchAndRenderProfitLoss();
}

async function fetchAndRenderProfitLoss() {
  const [summary, details] = await Promise.all([
    fetch('/api/profit_loss/summary').then(r => r.json()),
    fetch('/api/profit_loss/details').then(r => r.json()),
  ]);
  renderProfitLoss(summary, details);
}

function renderProfitLoss(summary, details) {
  const totalSpan = document.getElementById('plTotal');
  if (totalSpan && summary && typeof summary.total === 'number') totalSpan.textContent = `$${summary.total.toFixed(2)}`;
  const unrealizedSpan = document.getElementById('plUnrealized');
  if (unrealizedSpan && summary && typeof summary.unrealized === 'number') unrealizedSpan.textContent = `$${summary.unrealized.toFixed(2)}`;
  const realizedSpan = document.getElementById('plRealized');
  if (realizedSpan && summary && typeof summary.realized === 'number') realizedSpan.textContent = `$${summary.realized.toFixed(2)}`;

  const detailsTbody = document.getElementById('plDetailsTbody');
  if (detailsTbody) {
    detailsTbody.innerHTML = '';
    if (!details || details.length === 0) {
      detailsTbody.innerHTML = '<tr><td colspan="3" class="text-center text-gray-400 py-4">No P/L data.</td></tr>';
    } else {
      details.forEach(d => {
        const tr = document.createElement('tr');
        tr.innerHTML = `<td class="px-3 py-2">${d.symbol}</td><td class="px-3 py-2">${d.type}</td><td class="px-3 py-2">$${d.amount.toFixed(2)}</td>`;
        detailsTbody.appendChild(tr);
      });
    }
  }
}

document.addEventListener('DOMContentLoaded', function() {
  console.log('[ProfitLoss] DOMContentLoaded');
  const btn = document.getElementById('profitLossMinimizeBtn');
  const icon = document.getElementById('profitLossMinimizeIcon');
  const content = document.getElementById('profitLossContent');
  if (btn && content) {
    console.log('[ProfitLoss] Minimize button and content found');
    // Set initial max-height based on visibility
    if (content.classList.contains('collapsed')) {
      content.style.maxHeight = '0px';
      console.log('[ProfitLoss] Content starts collapsed');
    } else {
      content.style.maxHeight = content.scrollHeight + 'px';
      setTimeout(() => { content.style.maxHeight = 'none'; }, 400);
      console.log('[ProfitLoss] Content starts expanded');
    }
    btn.addEventListener('click', function() {
      console.log('[ProfitLoss] Minimize button clicked. Current maxHeight:', content.style.maxHeight);
      if (content.style.maxHeight === '0px') {
        // Currently closed, so open
        content.style.maxHeight = content.scrollHeight + 'px';
        console.log('[ProfitLoss] Opening content');
        if (icon) {
          icon.classList.remove('fa-chevron-down');
          icon.classList.add('fa-chevron-up');
        }
        content.addEventListener('transitionend', function handler(e) {
          if (e.target === content) {
            content.style.maxHeight = 'none';
            content.removeEventListener('transitionend', handler);
            console.log('[ProfitLoss] Open animation complete, maxHeight set to none');
          }
        });
      } else {
        // Currently open, so close
        content.style.maxHeight = content.scrollHeight + 'px';
        void content.offsetWidth;
        content.style.maxHeight = '0px';
        console.log('[ProfitLoss] Closing content');
        if (icon) {
          icon.classList.remove('fa-chevron-up');
          icon.classList.add('fa-chevron-down');
        }
      }
    });
  } else {
    console.log('[ProfitLoss] Minimize button or content NOT found');
  }
}); 