export function initDividends() {
  fetchAndRenderDividends();
}

async function fetchAndRenderDividends() {
  const [upcoming, past, summary] = await Promise.all([
    fetch('/api/dividends/upcoming').then(r => r.json()),
    fetch('/api/dividends/past').then(r => r.json()),
    fetch('/api/dividends/summary').then(r => r.json()),
  ]);
  renderDividends(upcoming, past, summary);
}

function renderDividends(upcoming, past, summary) {
  const upcomingTbody = document.getElementById('upcomingDividendsTbody');
  if (upcomingTbody) {
    upcomingTbody.innerHTML = '';
    if (!upcoming || upcoming.length === 0) {
      upcomingTbody.innerHTML = '<tr><td colspan="4" class="text-center text-gray-400 py-4">No upcoming dividends.</td></tr>';
    } else {
      upcoming.forEach(d => {
        const tr = document.createElement('tr');
        tr.innerHTML = `<td class="px-3 py-2">${d.symbol}</td><td class="px-3 py-2">${d.exDate}</td><td class="px-3 py-2">${d.payDate}</td><td class="px-3 py-2">$${d.amount.toFixed(2)}</td>`;
        upcomingTbody.appendChild(tr);
      });
    }
  }
  const pastTbody = document.getElementById('pastDividendsTbody');
  if (pastTbody) {
    pastTbody.innerHTML = '';
    if (!past || past.length === 0) {
      pastTbody.innerHTML = '<tr><td colspan="3" class="text-center text-gray-400 py-4">No past dividends.</td></tr>';
    } else {
      past.forEach(d => {
        const tr = document.createElement('tr');
        tr.innerHTML = `<td class="px-3 py-2">${d.symbol}</td><td class="px-3 py-2">${d.payDate}</td><td class="px-3 py-2">$${d.amount.toFixed(2)}</td>`;
        pastTbody.appendChild(tr);
      });
    }
  }
  const totalSpan = document.getElementById('dividendsTotal');
  if (totalSpan && summary && typeof summary.total === 'number') totalSpan.textContent = `$${summary.total.toFixed(2)}`;
} 