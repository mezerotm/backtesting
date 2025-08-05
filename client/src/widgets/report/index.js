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
            console.log('[fetchReportsData] Total reports received:', data.length);
            const finishedReports = data.filter(report => !report.status || report.status === 'finished');
            console.log('[fetchReportsData] Finished reports after filtering:', finishedReports.length);
            console.log('[fetchReportsData] Report statuses:', data.map(r => ({ dir: r.dir, status: r.status })));
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
    // Use the global confirmation modal from WidgetUtils
    if (window.WidgetUtils && window.WidgetUtils.showConfirmationModal) {
        window.WidgetUtils.showConfirmationModal(message, confirmCallback);
    } else {
        // Fallback to the original implementation
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
    // Render the report widget HTML into the placeholder
    const reportWidget = document.getElementById('report-widget');
    if (reportWidget) {
        // Create the report widget HTML structure
        reportWidget.innerHTML = `
            <!-- Report Action Bar -->
            <div id="reportActionBar" class="bg-slate-800 rounded-xl shadow flex justify-end gap-4 w-full p-6 mb-2 collapsed">
                <button id="cleanResultsBtn" class="reset-btn py-2 px-4 rounded-lg text-white bg-gray-600 hover:bg-gray-700 flex items-center gap-2">
                    <i class="fa-solid fa-broom"></i> Clean Results
                </button>
                <button id="openModalBtn" class="primary-btn py-2 px-4 rounded-lg text-white bg-blue-600 hover:bg-blue-700 flex items-center gap-2">
                    <i class="fa-solid fa-plus"></i> Generate Report
                </button>
            </div>
            
            <!-- Report Card -->
            <div class="bg-slate-800 rounded-xl shadow-sm widget-report p-6 w-full">
                <div class="flex justify-between items-center mb-0">
                    <h2 class="text-lg font-bold text-white flex items-center gap-2">
                        Reports
                        <button id="reportMinimizeBtn" class="ml-2 text-slate-400 hover:text-blue-400 focus:outline-none" title="Minimize Reports" style="transition: transform 0.2s;"><i id="reportMinimizeIcon" class="fa-solid fa-chevron-down"></i></button>
                    </h2>
                </div>
                <div id="reportContent" class="collapsed">
                    <!-- Reports Area: Two Columns -->
                    <div class="grid grid-cols-1 lg:grid-cols-4 gap-6">
                        <!-- Left Column: Filters -->
                        <div class="lg:col-span-1">
                            <div class="bg-slate-700 rounded-lg shadow-sm p-4">
                                <h3 class="text-md font-bold text-white mb-4 flex items-center gap-2">
                                    <i class="fa-solid fa-filter"></i>
                                    Filters
                                </h3>
                                <div class="space-y-4">
                                    <!-- Report Type Filter -->
                                    <div>
                                        <label class="block text-sm font-medium text-gray-300 mb-2">Report Type</label>
                                        <select id="filterReportType" class="w-full px-3 py-2 bg-slate-600 border border-slate-500 rounded-md text-white">
                                            <option value="">All Reports</option>
                                            <option value="backtest">Backtest</option>
                                            <option value="comparison">Comparison</option>
                                            <option value="chart">Chart</option>
                                        </select>
                                    </div>
                                    
                                    <!-- Symbol Filter -->
                                    <div>
                                        <label class="block text-sm font-medium text-gray-300 mb-2">Symbol</label>
                                        <select id="filterSymbol" class="w-full px-3 py-2 bg-slate-600 border border-slate-500 rounded-md text-white">
                                            <option value="">All Symbols</option>
                                        </select>
                                    </div>
                                    
                                    <!-- Strategy Filter -->
                                    <div>
                                        <label class="block text-sm font-medium text-gray-300 mb-2">Strategy</label>
                                        <select id="filterStrategy" class="w-full px-3 py-2 bg-slate-600 border border-slate-500 rounded-md text-white">
                                            <option value="">All Strategies</option>
                                        </select>
                                    </div>
                                    
                                    <!-- Date Range -->
                                    <div>
                                        <label class="block text-sm font-medium text-gray-300 mb-2">Start Date</label>
                                        <input type="date" id="filterStartDate" class="w-full px-3 py-2 bg-slate-600 border border-slate-500 rounded-md text-white">
                                    </div>
                                    
                                    <div>
                                        <label class="block text-sm font-medium text-gray-300 mb-2">End Date</label>
                                        <input type="date" id="filterEndDate" class="w-full px-3 py-2 bg-slate-600 border border-slate-500 rounded-md text-white">
                                    </div>
                                    
                                    <!-- Filter Buttons -->
                                    <div class="flex gap-2">
                                        <button id="resetFiltersBtn" class="flex-1 reset-btn py-2 px-4 rounded-lg text-white bg-gray-600 hover:bg-gray-700">
                                            Reset
                                        </button>
                                        <button id="applyFiltersBtn" class="flex-1 primary-btn py-2 px-4 rounded-lg text-white bg-blue-600 hover:bg-blue-700">
                                            Apply Filters
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Right Column: Reports Table -->
                        <div class="lg:col-span-3">
                            <div class="bg-slate-700 rounded-lg shadow-sm p-4">
                                <div class="flex justify-between items-center mb-4">
                                    <h3 class="text-md font-bold text-white flex items-center gap-2">
                                        <i class="fa-solid fa-file-lines"></i>
                                        Available Reports
                                    </h3>
                                </div>
                                
                                <div class="overflow-x-auto">
                                    <table id="reportsTable" class="min-w-full divide-y divide-slate-600">
                                        <thead class="bg-slate-700">
                                            <tr>
                                                <th class="px-3 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Actions</th>
                                                <th class="px-3 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Symbol</th>
                                                <th class="px-3 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Report Type</th>
                                                <th class="px-3 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Strategy</th>
                                                <th class="px-3 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Timeframe</th>
                                                <th class="px-3 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Created</th>
                                            </tr>
                                        </thead>
                                        <tbody class="bg-slate-700 divide-y divide-slate-600">
                                    <tr>
                                        <td colspan="6" class="px-6 py-4 text-center text-gray-400">
                                            <div class="flex items-center justify-center">
                                                <div class="spinner"></div>
                                                <span class="ml-2">Loading reports...</span>
                                            </div>
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                        
                        <div class="mt-4 text-sm text-gray-400">
                            Last updated: <span id="lastUpdated">-</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
            
            <!-- Generate Report Modal -->
            <div id="reportModal" class="fixed inset-0 bg-black bg-opacity-50 hidden z-50 flex items-center justify-center">
                <div class="bg-slate-800 rounded-lg p-6 w-full max-w-md mx-4 max-h-[90vh] overflow-visible">
                    <div class="flex justify-between items-center mb-6">
                        <h2 class="text-xl font-bold text-white">Generate Report</h2>
                        <button id="cancelReportModalBtn" class="text-gray-400 hover:text-white">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                    
                    <form id="reportForm" class="space-y-6">
                        <!-- Report Type Selection (Always Visible) -->
                        <div>
                            <label for="genReportType" class="block text-sm font-medium text-gray-300 mb-2">Report Type</label>
                            <select id="genReportType" name="type" required class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-white">
                                <option value="market">Market Report</option>
                                <option value="finance">Financial Report</option>
                            </select>
                        </div>
                        
                        <!-- Conditional Fields Container -->
                        <div id="conditionalFields" class="space-y-4">
                            <!-- Symbol Field (Only for Finance Reports) -->
                            <div id="symbolField" class="hidden">
                                <label for="genSymbol" class="block text-sm font-medium text-gray-300 mb-2">Symbol</label>
                                <div class="relative">
                                    <input type="text" id="genSymbol" name="symbol" placeholder="Search for a symbol..." 
                                           class="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-md text-white placeholder-gray-400">
                                    <div id="genSymbolDropdown" class="absolute w-full z-50"></div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="flex justify-end gap-3 pt-4">
                            <button type="button" id="cancelReportModalBtn2" class="px-4 py-2 rounded-lg text-white bg-gray-600 hover:bg-gray-700 transition-colors">
                                Cancel
                            </button>
                            <button type="submit" class="px-4 py-2 rounded-lg text-white bg-blue-600 hover:bg-blue-700 transition-colors">
                                Generate Report
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        `;
    }
    
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
    // Modern conditional form fields for report type
    const genReportType = document.getElementById('genReportType');
    const symbolField = document.getElementById('symbolField');
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
        if (genSymbolDropdown) {
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
    }

    async function fetchGenSymbolSuggestions(query) {
        if (!query || query.length < 1) {
            closeGenSymbolDropdown();
            return;
        }
        try {
            const resp = await fetch(`/api/portfolio/search-symbols?query=${encodeURIComponent(query)}`);
            if (!resp.ok) return;
            const data = await resp.json();
            genSymbolSuggestions = data.symbols || data;
            renderGenSymbolDropdown(genSymbolSuggestions);
        } catch (e) {
            console.error('Error fetching symbol suggestions:', e);
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
    
    if (genSymbolDropdown) {
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
    }

    function updateReportFormFields() {
        const type = genReportType.value;
        
        // Hide all conditional fields by default
        if (symbolField) {
            symbolField.classList.add('hidden');
            genSymbolInput.required = false;
        }
        
        // Show relevant fields based on report type
        switch (type) {
            case 'market':
                // Market reports don't need any additional fields
                break;
            case 'finance':
                // Finance reports need symbol
                if (symbolField) {
                    symbolField.classList.remove('hidden');
                    genSymbolInput.required = true;
                }
                break;
            default:
                // No report type selected
                break;
        }
    }
    
    if (genReportType) {
        genReportType.addEventListener('change', updateReportFormFields);
        updateReportFormFields(); // Initial call
    }
    // Add event listener for Generate Report form
    const reportForm = document.getElementById('reportForm');
    if (reportForm) {
        reportForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            console.log('[Generate Report] Form submitted');
            
            // Show loading state
            const submitBtn = reportForm.querySelector('button[type="submit"]');
            const originalText = submitBtn.textContent;
            submitBtn.textContent = 'Generating...';
            submitBtn.disabled = true;
            
            const formData = new FormData(reportForm);
            const reportType = formData.get('type') || 'market';
            const symbol = formData.get('symbol') || '';
            
            const params = new URLSearchParams();
            params.append('output_dir', 'public/results');
            params.append('force_refresh', 'false');
            
            // Add symbol if provided
            if (symbol.trim()) {
                params.append('symbol', symbol.trim().toUpperCase());
            }
            
            let apiEndpoint = '';
            let successMessage = '';
            
            // Determine API endpoint based on report type
            switch (reportType) {
                case 'market':
                    apiEndpoint = '/api/report/generate-market';
                    successMessage = 'Market report generated';
                    break;
                case 'finance':
                    if (!symbol.trim()) {
                        showToast('Symbol is required for financial reports', 'error');
                        submitBtn.textContent = originalText;
                        submitBtn.disabled = false;
                        return;
                    }
                    apiEndpoint = '/api/report/generate-finance';
                    successMessage = 'Financial report generated';
                    break;
                default:
                    showToast('Invalid report type: ' + reportType, 'error');
                    submitBtn.textContent = originalText;
                    submitBtn.disabled = false;
                    return;
            }
            
            try {
                const resp = await fetch(apiEndpoint + '?' + params.toString(), {
                    method: 'POST',
                });
                if (!resp.ok) throw new Error('Failed to generate report: ' + resp.status);
                const data = await resp.json();
                console.log('[Generate Report] Success:', data);
                showToast(successMessage + ': ' + (data.report_path || 'unknown'), 'success');
                
                // Close the modal
                const reportModal = document.getElementById('reportModal');
                if (reportModal) {
                    reportModal.classList.add('hidden');
                }
                
                // Refresh the reports table to show the new report
                fetchReportsData();
            } catch (err) {
                console.error('[Generate Report] Error:', err);
                showToast('Error generating report: ' + err.message, 'error');
            } finally {
                // Restore button state
                submitBtn.textContent = originalText;
                submitBtn.disabled = false;
            }
        });
    } else {
        console.warn('[initReport] reportForm not found');
    }
    // Auto-refresh reports every 5 seconds - TEMPORARILY DISABLED to fix infinite loop
    // setInterval(fetchReportsData, 5000);
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

document.addEventListener('DOMContentLoaded', function() {
  const btn = document.getElementById('reportMinimizeBtn');
  const icon = document.getElementById('reportMinimizeIcon');
  const content = document.getElementById('reportContent');
  const actionButtons = document.getElementById('reportActionButtons');
  if (btn && content && actionButtons) {
    // Always start open by default
    content.style.maxHeight = 'none';
    actionButtons.style.display = 'flex';
    actionButtons.classList.remove('fade-scale-hide');
    actionButtons.classList.add('fade-scale-show');
    if (icon) {
      icon.classList.remove('fa-chevron-down');
      icon.classList.add('fa-chevron-up');
    }
    // Set initial max-height for open/closed
    if (content.style.maxHeight === '0px' || (icon && icon.classList.contains('fa-chevron-down'))) {
      content.style.maxHeight = '0px';
      actionButtons.style.display = 'none';
      actionButtons.classList.remove('fade-scale-show', 'fade-scale-hide');
      if (icon) {
        icon.classList.remove('fa-chevron-up');
        icon.classList.add('fa-chevron-down');
      }
    } else {
      actionButtons.style.maxHeight = actionButtons.scrollHeight + 'px';
      setTimeout(() => { actionButtons.style.maxHeight = 'none'; }, 400);
      actionButtons.style.display = 'flex';
      actionButtons.classList.remove('fade-scale-hide');
      actionButtons.classList.add('fade-scale-show');
      content.style.maxHeight = content.scrollHeight + 'px';
      setTimeout(() => { content.style.maxHeight = 'none'; }, 400);
      if (icon) {
        icon.classList.remove('fa-chevron-down');
        icon.classList.add('fa-chevron-up');
      }
    }
    btn.addEventListener('click', function() {
      if (actionButtons.style.display === 'none' || content.style.maxHeight === '0px') {
        actionButtons.style.display = 'flex';
        actionButtons.classList.remove('fade-scale-show');
        actionButtons.classList.add('fade-scale-hide');
        void actionButtons.offsetWidth;
        actionButtons.classList.remove('fade-scale-hide');
        actionButtons.classList.add('fade-scale-show');
        actionButtons.addEventListener('transitionend', function handler(e) {
          if (e.target === actionButtons && (e.propertyName === 'opacity' || e.propertyName === 'transform')) {
            actionButtons.classList.remove('fade-scale-show');
            actionButtons.removeEventListener('transitionend', handler);
          }
        });
        content.style.maxHeight = content.scrollHeight + 'px';
        if (icon) {
          icon.classList.remove('fa-chevron-down');
          icon.classList.add('fa-chevron-up');
        }
        content.addEventListener('transitionend', function handler(e) {
          if (e.target === content) {
            content.style.maxHeight = 'none';
            content.removeEventListener('transitionend', handler);
          }
        });
      } else {
        actionButtons.classList.remove('fade-scale-show');
        actionButtons.classList.add('fade-scale-hide');
        actionButtons.addEventListener('transitionend', function handler(e) {
          if (e.target === actionButtons && (e.propertyName === 'opacity' || e.propertyName === 'transform')) {
            actionButtons.style.display = 'none';
            actionButtons.classList.remove('fade-scale-hide');
            actionButtons.removeEventListener('transitionend', handler);
          }
        });
        content.style.maxHeight = content.scrollHeight + 'px';
        void content.offsetWidth;
        content.style.maxHeight = '0px';
        if (icon) {
          icon.classList.remove('fa-chevron-up');
          icon.classList.add('fa-chevron-down');
        }
      }
    });
  }
  if (actionButtons) actionButtons.style.transition = '';
  if (content) content.style.transition = 'max-height 0.4s cubic-bezier(0.4,0,0.2,1)';
});