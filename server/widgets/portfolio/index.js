const API_PORTFOLIO = '/api/portfolio';

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
  const portfolioCash = getPortfolioCash();
  let totalValue = 0;
  positions.forEach(pos => {
    totalValue += pos.quantity * pos.buy_price;
  });
  if (!positions.length) {
    tbody.innerHTML = '<tr><td colspan="9" class="text-center text-gray-400 py-4">No positions found.</td></tr>';
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

function getPortfolioCash() {
  const val = localStorage.getItem('portfolio-cash');
  return val ? parseFloat(val) : 10000;
}

function setPortfolioCash(val) {
  localStorage.setItem('portfolio-cash', val);
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
    .then(() => fetchPositions());
}

export function initPortfolio() {
  // Modal logic for settings
  const settingsBtn = document.getElementById('settingsBtn');
  const cashModal = document.getElementById('cashModal');
  const cancelCashModalBtn = document.getElementById('cancelCashModalBtn');
  if (settingsBtn && cashModal && cancelCashModalBtn) {
    settingsBtn.addEventListener('click', () => {
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
          fetchPositions();
          document.getElementById('positionModal').classList.add('hidden');
        });
      } else {
        // Add
        fetch(API_PORTFOLIO + '/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(pos)
        }).then(() => {
          fetchPositions();
          document.getElementById('positionModal').classList.add('hidden');
        });
      }
    });
  }
  fetchPositions();
} 