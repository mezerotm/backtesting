export function initProfitLoss() {
  fetchAndRenderProfitLoss();
  setupTimeButtons();
  initChart();
}

let plChart = null;
let currentPeriod = 'YTD';

async function fetchAndRenderProfitLoss(period = 'YTD') {
  console.log(`[ProfitLoss] Fetching data for period: ${period}`);
  try {
    const [summary, details, chartData] = await Promise.all([
      fetch(`/api/profit-loss/summary?period=${period}`).then(r => r.json()),
      fetch('/api/profit-loss/details').then(r => r.json()),
      fetch(`/api/profit-loss/chart?period=${period}`).then(r => r.json()),
    ]);
    console.log('[ProfitLoss] API responses:', { summary, details: details.length, chartData });
    renderProfitLoss(summary, details);
    updateChart(chartData);
  } catch (error) {
    console.error('[ProfitLoss] Error fetching data:', error);
  }
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
      // Fetch and update data for the new period
      fetchAndRenderProfitLoss(currentPeriod);
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

function updateChart(chartData) {
  if (!plChart || !chartData) return;

  plChart.data.labels = chartData.labels || [];
  plChart.data.datasets[0].data = chartData.values || [];
  
  // Update colors based on data
  const lastValue = chartData.values && chartData.values.length > 0 ? chartData.values[chartData.values.length - 1] : 0;
  const color = lastValue >= 0 ? '#10b981' : '#f87171';
  plChart.data.datasets[0].borderColor = color;
  plChart.data.datasets[0].backgroundColor = color.replace(')', ', 0.1)').replace('rgb', 'rgba');
  
  plChart.update('none');
}

// Collapse logic is handled by the global WidgetUtils.setupMinimizeButtons() in main.js 