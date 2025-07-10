// --- Report Widget Logic (migrated from dashboard.html) ---
const API_REPORT = '/api/report';

export function fetchReportsData() {
    fetch(API_REPORT + '/list')
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok: ' + response.status);
            }
            return response.json();
        })
        .then(data => {
            if (!data) {
                console.error('Invalid reports data format:', data);
                return;
            }
            const finishedReports = data.filter(report => !report.status || report.status === 'finished');
            displayReports(finishedReports);
            const lastUpdated = document.getElementById('lastUpdated');
            if (lastUpdated) lastUpdated.textContent = new Date().toLocaleString();
        })
        .catch(error => {
            console.error('Error fetching reports data:', error);
            const tableBody = document.querySelector('#reportsTable tbody');
            if (tableBody) {
                tableBody.innerHTML = `
                    <tr>
                        <td colspan="7" class="px-6 py-4 text-center text-red-500 font-medium">
                            <i class="fa-solid fa-circle-exclamation mr-2"></i>
                            Failed to load reports. Error: ${error.message}
                        </td>
                    </tr>
                `;
            }
        });
}

export function displayReports(reports) {
    reports.sort((a, b) => new Date(b.created) - new Date(a.created));
    const tableBody = document.querySelector('#reportsTable tbody');
    if (!tableBody) {
        console.error('Table body not found');
        return;
    }
    tableBody.innerHTML = '';
    if (reports.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="7" class="py-4 text-center">
                    <div class="flex justify-center text-gray-300">
                        <i class="fa-solid fa-folder-open text-xl mr-2"></i>
                        <span>No reports available</span>
                    </div>
                </td>
            </tr>
        `;
        return;
    }
    // Filter logic can be re-enabled here if needed
    reports.forEach((report, index) => {
        const row = document.createElement('tr');
        row.className = `${index % 2 === 0 ? 'bg-slate-800' : 'bg-slate-900'} hover:bg-slate-700`;
        let typeBadgeClass = '';
        if (report.type === 'backtest') {
            typeBadgeClass = 'bg-green-800 text-green-200';
        } else if (report.type === 'comparison') {
            typeBadgeClass = 'bg-rose-900 text-rose-200';
        } else if (report.type === 'chart') {
            typeBadgeClass = 'bg-blue-900 text-blue-200';
        } else {
            typeBadgeClass = 'bg-gray-700 text-gray-200';
        }
        const startDate = report.start_date ? formatDate(report.start_date, false, true) : '';
        const endDate = report.end_date ? formatDate(report.end_date, false, true) : '';
        row.innerHTML = `
            <td class="px-3 py-3 align-middle whitespace-nowrap">
                <div class="flex items-center gap-2">
                    <a href="${report.path}" class="text-blue-500 hover:text-blue-400" title="View Report">
                        <i class="fa-solid fa-file-lines"></i>
                    </a>
                    <button onclick="deleteReport('${report.dir}')" class="text-red-500 hover:text-red-400" title="Delete Report">
                        <i class="fa-solid fa-trash"></i>
                    </button>
                </div>
            </td>
            <td class="px-3 py-3 align-middle whitespace-nowrap font-medium text-white">
                ${report.symbol || 'Unknown'}
            </td>
            <td class="px-3 py-3 align-middle whitespace-nowrap">
                <span class="inline-flex items-center gap-x-1.5 py-1 px-2.5 text-xs font-medium rounded-full ${typeBadgeClass}">
                    ${report.type || 'Unknown'}
                </span>
            </td>
            <td class="px-3 py-3 align-middle whitespace-nowrap text-gray-200">
                ${report.strategy === 'Unknown' ? '-' : report.strategy || '-'}
            </td>
            <td class="px-3 py-3 align-middle whitespace-nowrap text-gray-300">
                ${report.timeframe || '-'}
            </td>
            <td class="px-3 py-3 align-middle whitespace-nowrap text-sm text-gray-300">
                ${report.date_range || report.start_date && report.end_date ? 
                    `${formatDate(report.start_date, false, true)} to ${formatDate(report.end_date, false, true)}` : 
                    '-'}
            </td>
            <td class="px-3 py-3 align-middle whitespace-nowrap text-gray-300">
                ${report.created ? formatDate(report.created, true, true) : '-'}
            </td>
        `;
        tableBody.appendChild(row);
    });
}

export function formatDate(dateString, includeTime = false, compact = false) {
    try {
        const date = new Date(dateString);
        if (compact) {
            const month = date.toLocaleString('en-US', { month: 'short' });
            const day = date.getDate();
            const year = date.getFullYear();
            let formatted = `${month} ${day}, ${year}`;
            if (includeTime) {
                const hours = date.getHours();
                const minutes = date.getMinutes().toString().padStart(2, '0');
                formatted = `${month} ${day}, ${year} ${hours}:${minutes}`;
            }
            return formatted;
        } else {
            const options = { year: 'numeric', month: 'short', day: 'numeric', hour12: false };
            if (includeTime) {
                options.hour = '2-digit';
                options.minute = '2-digit';
            }
            return date.toLocaleDateString('en-US', options);
        }
    } catch (e) {
        console.error('Date parsing error:', e, 'for date:', dateString);
        return dateString;
    }
}

export function deleteReport(reportDir) {
    showConfirmationModal(
        `Are you sure you want to delete this report?`,
        () => {
            fetch(`/delete-report/${reportDir}`, { 
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                showToast('Report deleted successfully', 'success');
                fetchReportsData();
            })
            .catch(error => {
                showToast('Error deleting report: ' + error.message, 'error');
                console.error('Delete error:', error);
            });
        }
    );
}

export function showConfirmationModal(message, confirmCallback) {
    const modal = document.getElementById('reportConfirmModal');
    const confirmBtn = document.getElementById('confirmReportModalBtn');
    const cancelBtn = document.getElementById('cancelReportConfirmModalBtn');

    if (modal && confirmBtn && cancelBtn) {
        modal.classList.remove('hidden');
        modal.querySelector('.modal-content p').textContent = message;

        // Remove previous listeners to avoid stacking
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
        // Optional: close modal on outside click
        modal.onmousedown = (e) => {
            if (e.target === modal) {
                modal.classList.add('hidden');
            }
        };
    } else {
        console.error('[showConfirmationModal] Modal or buttons not found:', {modal, confirmBtn, cancelBtn});
    }
}

export function showToast(message, type = 'success') {
    const toastContainer = document.getElementById('toastContainer');
    if (!toastContainer) {
        console.error('Toast container not found');
        return;
    }

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;

    toastContainer.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('hidden');
    }, 3000); // Hide after 3 seconds

    toast.addEventListener('transitionend', () => {
        if (toast.classList.contains('hidden')) {
            toast.remove();
        }
    });
}

export function resetFilters() {
    // This function was not provided in the edit_specification,
    // so it will be left as a placeholder.
    console.log('Resetting filters...');
}

export function initReport() {
    fetchReportsData();
    // Set up event listeners for Clean Results and Generate Report buttons (toolbar or widget)
    // Clean Results
    const cleanBtn = document.getElementById('cleanResultsBtn');
    if (cleanBtn) {
        console.log('[initReport] Found cleanResultsBtn, attaching event listener');
        cleanBtn.addEventListener('click', () => {
            console.log('[cleanResultsBtn] Clicked');
            cleanResults();
        });
    } else {
        console.warn('[initReport] cleanResultsBtn not found');
    }
    // Generate Report Modal logic
    const openModalBtn = document.getElementById('openModalBtn');
    const reportModal = document.getElementById('reportModal');
    const cancelReportModalBtn = document.getElementById('cancelReportModalBtn');
    if (openModalBtn && reportModal) {
        openModalBtn.addEventListener('click', () => {
            reportModal.classList.remove('hidden');
        });
    }
    if (cancelReportModalBtn && reportModal) {
        cancelReportModalBtn.addEventListener('click', () => {
            reportModal.classList.add('hidden');
        });
    }
    // Optional: close modal on outside click
    if (reportModal) {
        reportModal.addEventListener('mousedown', (e) => {
            if (e.target === reportModal) {
                reportModal.classList.add('hidden');
            }
        });
    }
    // Dynamic form fields for report type
    const genReportType = document.getElementById('genReportType');
    const strategyField = document.getElementById('genStrategy').closest('div');
    const timeframeField = document.getElementById('genTimeframe').closest('div');
    const startDateField = document.getElementById('genStartDate').closest('div');
    const endDateField = document.getElementById('genEndDate').closest('div');
    const symbolField = document.getElementById('genSymbol').closest('div');
    const genSymbolInput = document.getElementById('genSymbol');
    const genSymbolDropdown = document.getElementById('genSymbolDropdown');
    let genSymbolSuggestions = [];
    let genSymbolDropdownOpen = false;
    let genSymbolDropdownIndex = -1;

    function closeGenSymbolDropdown() {
        genSymbolDropdown.innerHTML = '';
        genSymbolDropdownOpen = false;
        genSymbolDropdownIndex = -1;
    }

    function renderGenSymbolDropdown(suggestions) {
        if (!suggestions.length) {
            closeGenSymbolDropdown();
            return;
        }
        genSymbolDropdown.innerHTML = `<div class="absolute z-50 w-full bg-slate-800 border border-slate-600 rounded-b-lg shadow-lg mt-0.5 max-h-56 overflow-y-auto select-none">
            ${suggestions.map((item, i) => `
                <div class="px-4 py-2 cursor-pointer hover:bg-blue-700 ${i === genSymbolDropdownIndex ? 'bg-blue-700 text-white' : 'text-gray-200'}" data-index="${i}">
                    <span class="font-semibold">${item.symbol}</span>
                    <span class="ml-2 text-xs text-gray-400">${item.name ? item.name : ''}</span>
                </div>
            `).join('')}
        </div>`;
        genSymbolDropdownOpen = true;
    }

    async function fetchGenSymbolSuggestions(query) {
        if (!query || query.length < 1) {
            closeGenSymbolDropdown();
            return;
        }
        try {
            const resp = await fetch(`/api/report/search-symbols?query=${encodeURIComponent(query)}`);
            if (!resp.ok) return;
            const data = await resp.json();
            genSymbolSuggestions = data;
            renderGenSymbolDropdown(genSymbolSuggestions);
        } catch (e) {
            closeGenSymbolDropdown();
        }
    }

    // Debounce helper
    function debounce(fn, delay) {
        let timeout;
        return function(...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => fn.apply(this, args), delay);
        };
    }

    const debouncedFetchGenSymbols = debounce((e) => {
        fetchGenSymbolSuggestions(e.target.value.trim().toUpperCase());
    }, 250);

    if (genSymbolInput) {
        genSymbolInput.addEventListener('input', debouncedFetchGenSymbols);
        genSymbolInput.addEventListener('keydown', (e) => {
            if (!genSymbolDropdownOpen || !genSymbolSuggestions.length) return;
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                genSymbolDropdownIndex = (genSymbolDropdownIndex + 1) % genSymbolSuggestions.length;
                renderGenSymbolDropdown(genSymbolSuggestions);
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                genSymbolDropdownIndex = (genSymbolDropdownIndex - 1 + genSymbolSuggestions.length) % genSymbolSuggestions.length;
                renderGenSymbolDropdown(genSymbolSuggestions);
            } else if (e.key === 'Enter') {
                if (genSymbolDropdownIndex >= 0 && genSymbolDropdownIndex < genSymbolSuggestions.length) {
                    genSymbolInput.value = genSymbolSuggestions[genSymbolDropdownIndex].symbol;
                    closeGenSymbolDropdown();
                }
            } else if (e.key === 'Escape') {
                closeGenSymbolDropdown();
            }
        });
        genSymbolInput.addEventListener('blur', () => {
            setTimeout(closeGenSymbolDropdown, 150);
        });
    }
    genSymbolDropdown.addEventListener('mousedown', (e) => {
        const target = e.target.closest('[data-index]');
        if (target) {
            const idx = parseInt(target.getAttribute('data-index'));
            if (!isNaN(idx) && genSymbolSuggestions[idx]) {
                genSymbolInput.value = genSymbolSuggestions[idx].symbol;
                closeGenSymbolDropdown();
            }
        }
    });
    function updateReportFormFields() {
        const type = genReportType.value;
        // Always show report type at the top
        if (type === 'finance') {
            if (symbolField) symbolField.style.display = '';
        } else {
            if (symbolField) symbolField.style.display = 'none';
        }
        if (type === 'market' || type === 'finance') {
            if (strategyField) strategyField.style.display = 'none';
            if (timeframeField) timeframeField.style.display = 'none';
            if (startDateField) startDateField.style.display = 'none';
            if (endDateField) endDateField.style.display = 'none';
        } else {
            if (strategyField) strategyField.style.display = '';
            if (timeframeField) timeframeField.style.display = '';
            if (startDateField) startDateField.style.display = '';
            if (endDateField) endDateField.style.display = '';
        }
    }
    if (genReportType) {
        genReportType.addEventListener('change', updateReportFormFields);
        updateReportFormFields(); // Initial call
    }
    // Add event listener for Generate Report form
    const generateReportForm = document.getElementById('generateReportForm');
    if (generateReportForm) {
        generateReportForm.addEventListener('submit', function(e) {
            e.preventDefault();
            console.log('[Generate Report] Form submitted');
            const formData = new FormData(generateReportForm);
            for (const [key, value] of formData.entries()) {
                console.log(`[Generate Report] ${key}:`, value);
            }
            // TODO: Implement actual report generation logic here
        });
    } else {
        console.warn('[initReport] generateReportForm not found');
    }
    // Auto-refresh reports every 5 seconds
    setInterval(fetchReportsData, 5000);
}

export function cleanResults() {
    console.log('[cleanResults] Called');
    // Show confirmation modal before cleaning all results
    showConfirmationModal(
        `[DEBUG] Are you sure you want to delete all results? This cannot be undone.`,
        () => {
            console.log('[cleanResults] Confirmation callback executed');
            // Confirmed - proceed with cleaning
            console.log('[cleanResults] Confirmed, sending POST to /api/report/clean');
            fetch('/api/report/clean', { method: 'POST' })
                .then(response => {
                    console.log('[cleanResults] Response received', response);
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    return response.json();
                })
                .then(data => {
                    console.log('[cleanResults] Success data:', data);
                    showToast('All results cleaned successfully', 'success');
                    if (typeof fetchReportsData === 'function') fetchReportsData();
                })
                .catch(error => {
                    console.error('[cleanResults] Error:', error);
                    showToast('Error cleaning results: ' + error.message, 'error');
                });
        }
    );
    console.log('[cleanResults] Confirmation modal should be shown');
}