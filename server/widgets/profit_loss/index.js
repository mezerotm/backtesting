export function initProfitLoss() {
  fetchAndRenderProfitLoss();
  setupTimeButtons();
  initChart();
}

let plChart = null;
let currentPeriod = 'YTD';

async function fetchAndRenderProfitLoss() {
  const [summary, details] = await Promise.all([
    fetch('/api/profit_loss/summary').then(r => r.json()),
    fetch('/api/profit_loss/details').then(r => r.json()),
  ]);
  renderProfitLoss(summary, details);
  updateChart();
}

function renderProfitLoss(summary, details) {
  // Update summary with color coding
  const totalSpan = document.getElementById('plTotal');
  if (totalSpan && summary && typeof summary.total === 'number') {
    totalSpan.textContent = `$${summary.total.toFixed(2)}`;
    totalSpan.className = summary.total >= 0 ? 'text-2xl font-bold text-green-400' : 'text-2xl font-bold text-red-400';
  }
  
  const unrealizedSpan = document.getElementById('plUnrealized');
  if (unrealizedSpan && summary && typeof summary.unrealized === 'number') {
    unrealizedSpan.textContent = `$${summary.unrealized.toFixed(2)}`;
    unrealizedSpan.className = summary.unrealized >= 0 ? 'text-2xl font-bold text-green-400' : 'text-2xl font-bold text-red-400';
  }
  
  const realizedSpan = document.getElementById('plRealized');
  if (realizedSpan && summary && typeof summary.realized === 'number') {
    realizedSpan.textContent = `$${summary.realized.toFixed(2)}`;
    realizedSpan.className = summary.realized >= 0 ? 'text-2xl font-bold text-blue-400' : 'text-2xl font-bold text-red-400';
  }

  const detailsTbody = document.getElementById('plDetailsTbody');
  if (detailsTbody) {
    detailsTbody.innerHTML = '';
    if (!details || details.length === 0) {
      detailsTbody.innerHTML = '<tr><td colspan="3" class="text-center text-gray-400 py-4">No P/L data.</td></tr>';
    } else {
      details.forEach(d => {
        const tr = document.createElement('tr');
        const amountClass = d.amount >= 0 ? 'text-green-400' : 'text-red-400';
        tr.innerHTML = `<td class="px-3 py-2">${d.symbol}</td><td class="px-3 py-2">${d.type}</td><td class="px-3 py-2 ${amountClass}">$${d.amount.toFixed(2)}</td>`;
        detailsTbody.appendChild(tr);
      });
    }
  }
}

function setupTimeButtons() {
  const timeButtons = document.querySelectorAll('.time-btn');
  timeButtons.forEach(btn => {
    btn.addEventListener('click', function() {
      // Remove active class from all buttons
      timeButtons.forEach(b => b.classList.remove('active'));
      // Add active class to clicked button
      this.classList.add('active');
      // Update current period
      currentPeriod = this.dataset.period;
      // Update chart
      updateChart();
    });
  });
}

function initChart() {
  const ctx = document.getElementById('plChart');
  if (!ctx) return;

  plChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: [],
      datasets: [{
        label: 'Total P/L',
        data: [],
        borderColor: '#10b981',
        backgroundColor: 'rgba(16, 185, 129, 0.1)',
        borderWidth: 2,
        fill: true,
        tension: 0.4,
        pointRadius: 0,
        pointHoverRadius: 4,
        pointHoverBackgroundColor: '#10b981'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: false
        },
        tooltip: {
          mode: 'index',
          intersect: false,
          backgroundColor: '#1e293b',
          titleColor: '#e5e7eb',
          bodyColor: '#e5e7eb',
          borderColor: '#374151',
          borderWidth: 1,
          callbacks: {
            label: function(context) {
              const value = context.parsed.y;
              const color = value >= 0 ? '#4ade80' : '#f87171';
              return `P/L: $${value.toFixed(2)}`;
            }
          }
        }
      },
      scales: {
        x: {
          display: true,
          grid: {
            color: '#374151',
            drawBorder: false
          },
          ticks: {
            color: '#9ca3af',
            font: {
              size: 10
            }
          }
        },
        y: {
          display: true,
          grid: {
            color: '#374151',
            drawBorder: false
          },
          ticks: {
            color: '#9ca3af',
            font: {
              size: 10
            },
            callback: function(value) {
              return '$' + value.toFixed(0);
            }
          }
        }
      },
      interaction: {
        mode: 'nearest',
        axis: 'x',
        intersect: false
      }
    }
  });
}

function updateChart() {
  if (!plChart) return;

  // Generate sample data based on current period
  const data = generateChartData(currentPeriod);
  
  plChart.data.labels = data.labels;
  plChart.data.datasets[0].data = data.values;
  
  // Update colors based on data
  const lastValue = data.values[data.values.length - 1];
  const color = lastValue >= 0 ? '#10b981' : '#f87171';
  plChart.data.datasets[0].borderColor = color;
  plChart.data.datasets[0].backgroundColor = color.replace(')', ', 0.1)').replace('rgb', 'rgba');
  
  plChart.update('none');
}

function generateChartData(period) {
  const now = new Date();
  let labels = [];
  let values = [];
  
  switch (period) {
    case '1W':
      // Last 7 days
      for (let i = 6; i >= 0; i--) {
        const date = new Date(now);
        date.setDate(date.getDate() - i);
        labels.push(date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }));
        values.push(Math.random() * 2000 - 1000); // Random P/L between -1000 and 1000
      }
      break;
    case '1M':
      // Last 30 days, weekly data points
      for (let i = 4; i >= 0; i--) {
        const date = new Date(now);
        date.setDate(date.getDate() - (i * 7));
        labels.push(date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }));
        values.push(Math.random() * 3000 - 1500);
      }
      break;
    case '3M':
      // Last 3 months, bi-weekly data points
      for (let i = 6; i >= 0; i--) {
        const date = new Date(now);
        date.setDate(date.getDate() - (i * 14));
        labels.push(date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }));
        values.push(Math.random() * 4000 - 2000);
      }
      break;
    case 'YTD':
      // Year to date, monthly data points
      const startOfYear = new Date(now.getFullYear(), 0, 1);
      const months = Math.floor((now - startOfYear) / (1000 * 60 * 60 * 24 * 30));
      for (let i = months; i >= 0; i--) {
        const date = new Date(now.getFullYear(), now.getMonth() - i, 1);
        labels.push(date.toLocaleDateString('en-US', { month: 'short' }));
        values.push(Math.random() * 5000 - 2500);
      }
      break;
    case 'MAX':
      // Last 12 months
      for (let i = 11; i >= 0; i--) {
        const date = new Date(now);
        date.setMonth(date.getMonth() - i);
        labels.push(date.toLocaleDateString('en-US', { month: 'short' }));
        values.push(Math.random() * 6000 - 3000);
      }
      break;
  }
  
  // Create a cumulative effect
  let cumulative = 0;
  values = values.map(v => {
    cumulative += v;
    return cumulative;
  });
  
  return { labels, values };
}

document.addEventListener('DOMContentLoaded', function() {
  console.log('[ProfitLoss] DOMContentLoaded');
  const btn = document.getElementById('profitLossMinimizeBtn');
  const icon = document.getElementById('profitLossMinimizeIcon');
  const content = document.getElementById('profitLossContent');
  if (btn && content) {
    console.log('[ProfitLoss] Minimize button and content found');
    // Set initial max-height based on visibility
    if (content.style.maxHeight === '0px' || (icon && icon.classList.contains('fa-chevron-down'))) {
      content.style.maxHeight = '0px';
      if (icon) {
        icon.classList.remove('fa-chevron-up');
        icon.classList.add('fa-chevron-down');
      }
      console.log('[ProfitLoss] Content starts collapsed (by style or icon)');
    } else {
      content.style.maxHeight = content.scrollHeight + 'px';
      setTimeout(() => { content.style.maxHeight = 'none'; }, 400);
      if (icon) {
        icon.classList.remove('fa-chevron-down');
        icon.classList.add('fa-chevron-up');
      }
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