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

document.addEventListener('DOMContentLoaded', function() {
  console.log('[Dividends] DOMContentLoaded');
  const btn = document.getElementById('dividendsMinimizeBtn');
  const icon = document.getElementById('dividendsMinimizeIcon');
  const content = document.getElementById('dividendsContent');
  if (btn && content) {
    console.log('[Dividends] Minimize button and content found');
    // Set initial max-height based on visibility
    if (content.classList.contains('collapsed')) {
      content.style.maxHeight = '0px';
      console.log('[Dividends] Content starts collapsed');
    } else {
      content.style.maxHeight = content.scrollHeight + 'px';
      setTimeout(() => { content.style.maxHeight = 'none'; }, 400);
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