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