// Main JavaScript for Backtesting Dashboard

// Global state management
const AppState = {
    isLoading: false,
    currentView: 'dashboard',
    data: {},
    
    setLoading(loading) {
        this.isLoading = loading;
        this.updateUI();
    },
    
    setData(key, value) {
        this.data[key] = value;
    },
    
    getData(key) {
        return this.data[key];
    },
    
    updateUI() {
        const loadingElements = document.querySelectorAll('.loading');
        loadingElements.forEach(el => {
            el.style.display = this.isLoading ? 'flex' : 'none';
        });
    }
};

// Utility functions
const Utils = {
    // Format currency
    formatCurrency(amount, currency = 'USD') {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: currency
        }).format(amount);
    },
    
    // Format percentage
    formatPercentage(value, decimals = 2) {
        return `${(value * 100).toFixed(decimals)}%`;
    },
    
    // Format date
    formatDate(date) {
        return new Intl.DateTimeFormat('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        }).format(new Date(date));
    },
    
    // Show notification
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        
        // Add styles
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 1rem 1.5rem;
            border-radius: 6px;
            color: white;
            font-weight: 500;
            z-index: 1000;
            animation: slideIn 0.3s ease;
        `;
        
        // Set background color based on type
        const colors = {
            info: '#667eea',
            success: '#28a745',
            warning: '#ffc107',
            error: '#dc3545'
        };
        notification.style.backgroundColor = colors[type] || colors.info;
        
        document.body.appendChild(notification);
        
        // Remove after 3 seconds
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }, 3000);
    },
    
    // API request helper
    async apiRequest(endpoint, options = {}) {
        const defaultOptions = {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
        };
        
        const finalOptions = { ...defaultOptions, ...options };
        
        try {
            AppState.setLoading(true);
            const response = await fetch(endpoint, finalOptions);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            return data;
        } catch (error) {
            console.error('API request failed:', error);
            Utils.showNotification(`Request failed: ${error.message}`, 'error');
            throw error;
        } finally {
            AppState.setLoading(false);
        }
    },
    
    // Debounce function
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
};

// Chart utilities
const ChartUtils = {
    // Create a simple line chart
    createLineChart(containerId, data, options = {}) {
        const container = document.getElementById(containerId);
        if (!container) return null;
        
        const canvas = document.createElement('canvas');
        container.innerHTML = '';
        container.appendChild(canvas);
        
        const ctx = canvas.getContext('2d');
        
        // Set canvas size
        canvas.width = container.offsetWidth;
        canvas.height = container.offsetHeight || 300;
        
        const { labels, datasets } = data;
        const { width, height } = canvas;
        
        // Clear canvas
        ctx.clearRect(0, 0, width, height);
        
        // Find min/max values
        const allValues = datasets.flatMap(dataset => dataset.data);
        const minValue = Math.min(...allValues);
        const maxValue = Math.max(...allValues);
        const range = maxValue - minValue;
        
        // Draw grid
        ctx.strokeStyle = '#e9ecef';
        ctx.lineWidth = 1;
        
        // Horizontal grid lines
        const gridLines = 5;
        for (let i = 0; i <= gridLines; i++) {
            const y = (height - 40) * (i / gridLines) + 20;
            ctx.beginPath();
            ctx.moveTo(40, y);
            ctx.lineTo(width - 20, y);
            ctx.stroke();
        }
        
        // Draw lines
        datasets.forEach((dataset, datasetIndex) => {
            ctx.strokeStyle = dataset.color || '#667eea';
            ctx.lineWidth = 2;
            ctx.beginPath();
            
            dataset.data.forEach((value, index) => {
                const x = (width - 60) * (index / (labels.length - 1)) + 40;
                const y = height - 20 - ((value - minValue) / range) * (height - 40);
                
                if (index === 0) {
                    ctx.moveTo(x, y);
                } else {
                    ctx.lineTo(x, y);
                }
            });
            
            ctx.stroke();
        });
        
        return canvas;
    }
};

// Navigation
const Navigation = {
    navigateTo(view) {
        AppState.currentView = view;
        this.updateActiveNav();
        this.loadView(view);
    },
    
    updateActiveNav() {
        const navLinks = document.querySelectorAll('.nav-link');
        navLinks.forEach(link => {
            link.classList.remove('active');
            if (link.dataset.view === AppState.currentView) {
                link.classList.add('active');
            }
        });
    },
    
    async loadView(view) {
        try {
            AppState.setLoading(true);
            
            // Load view-specific content
            switch (view) {
                case 'dashboard':
                    await this.loadDashboard();
                    break;
                case 'portfolio':
                    await this.loadPortfolio();
                    break;
                case 'trades':
                    await this.loadTrades();
                    break;
                case 'report':
                    await this.loadReport();
                    break;
                default:
                    console.warn(`Unknown view: ${view}`);
            }
        } catch (error) {
            console.error(`Failed to load view ${view}:`, error);
            Utils.showNotification(`Failed to load ${view}`, 'error');
        } finally {
            AppState.setLoading(false);
        }
    },
    
    async loadDashboard() {
        // Dashboard is loaded by default, no additional action needed
        console.log('Dashboard loaded');
    },
    
    async loadPortfolio() {
        const data = await Utils.apiRequest('/api/portfolio');
        // Portfolio widget will handle its own rendering
        console.log('Portfolio data loaded:', data);
    },
    
    async loadTrades() {
        const data = await Utils.apiRequest('/api/trades');
        // Trades widget will handle its own rendering
        console.log('Trades data loaded:', data);
    },
    
    async loadReport() {
        const data = await Utils.apiRequest('/api/report');
        // Report widget will handle its own rendering
        console.log('Report data loaded:', data);
    }
};

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('Backtesting Dashboard initialized');
    
    // Add CSS animations
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideIn {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        
        @keyframes slideOut {
            from { transform: translateX(0); opacity: 1; }
            to { transform: translateX(100%); opacity: 0; }
        }
        
        .nav-link.active {
            background-color: rgba(255, 255, 255, 0.2);
            border-radius: 6px;
        }
    `;
    document.head.appendChild(style);
    
    // Set up navigation event listeners
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const view = link.dataset.view;
            if (view) {
                Navigation.navigateTo(view);
            }
        });
    });
    
    // Initialize with dashboard view
    Navigation.navigateTo('dashboard');
});

// Global widget utilities
const WidgetUtils = {
    // Minimize/maximize widget functionality
    setupMinimizeButtons() {
        document.querySelectorAll('[id$="MinimizeBtn"]').forEach(btn => {
            btn.addEventListener('click', function() {
                const widgetId = this.id.replace('MinimizeBtn', '');
                const contentId = widgetId + 'Content';
                const actionBarId = widgetId + 'ActionBar';
                const iconId = widgetId + 'MinimizeIcon';
                const content = document.getElementById(contentId);
                const actionBar = document.getElementById(actionBarId);
                const icon = document.getElementById(iconId);
                
                if (content && icon) {
                    const isCollapsed = content.classList.contains('collapsed');
                    
                    if (isCollapsed) {
                        // Expand the widget
                        content.classList.remove('collapsed');
                        // Only hide action bar for widgets that aren't reports
                        if (actionBar && !widgetId.includes('report')) {
                            actionBar.classList.remove('collapsed');
                        }
                        icon.className = 'fa-solid fa-chevron-up';
                    } else {
                        // Collapse the widget
                        content.classList.add('collapsed');
                        // Only hide action bar for widgets that aren't reports
                        if (actionBar && !widgetId.includes('report')) {
                            actionBar.classList.add('collapsed');
                        }
                        icon.className = 'fa-solid fa-chevron-down';
                    }
                }
            });
        });
    },
    
    // Setup modal functionality
    setupModals() {
        // Close modals when clicking outside
        document.querySelectorAll('[id$="Modal"]').forEach(modal => {
            modal.addEventListener('click', function(e) {
                if (e.target === this) {
                    this.classList.add('hidden');
                }
            });
        });
        
        // Setup cancel buttons
        document.querySelectorAll('[id$="cancelModalBtn"], [id$="CancelModalBtn"]').forEach(btn => {
            btn.addEventListener('click', function() {
                const modalId = this.id.replace('cancelModalBtn', 'Modal').replace('CancelModalBtn', 'Modal');
                const modal = document.getElementById(modalId);
                if (modal) {
                    modal.classList.add('hidden');
                }
            });
        });
    },
    
    // Symbol dropdown functionality
    setupSymbolDropdowns() {
        const symbolInputs = document.querySelectorAll('input[id*="symbol"], input[id*="Symbol"]');
        
        symbolInputs.forEach(input => {
            const dropdownId = input.id.replace('symbol', 'symbolDropdown').replace('Symbol', 'SymbolDropdown');
            const dropdown = document.getElementById(dropdownId);
            
            if (dropdown) {
                // Close dropdown when clicking outside
                document.addEventListener('click', function(e) {
                    if (!input.contains(e.target) && !dropdown.contains(e.target)) {
                        dropdown.innerHTML = '';
                    }
                });
                
                // Handle input changes
                input.addEventListener('input', Utils.debounce(async function() {
                    const query = this.value.trim();
                    if (query.length >= 2) {
                        try {
                            const suggestions = await Utils.apiRequest(`/api/symbols/search?q=${encodeURIComponent(query)}`);
                            renderSymbolDropdown(suggestions, dropdown, input);
                        } catch (error) {
                            console.error('Failed to fetch symbol suggestions:', error);
                        }
                    } else {
                        dropdown.innerHTML = '';
                    }
                }, 300));
            }
        });
    },
    
    // Render symbol dropdown
    renderSymbolDropdown(suggestions, dropdown, input) {
        dropdown.innerHTML = '';
        
        if (suggestions && suggestions.length > 0) {
            const dropdownDiv = document.createElement('div');
            suggestions.forEach(suggestion => {
                const item = document.createElement('div');
                item.className = 'cursor-pointer hover:bg-blue-700 px-4 py-2';
                item.textContent = suggestion.symbol || suggestion;
                item.addEventListener('click', () => {
                    input.value = suggestion.symbol || suggestion;
                    dropdown.innerHTML = '';
                });
                dropdownDiv.appendChild(item);
            });
            dropdown.appendChild(dropdownDiv);
        }
    },
    
    // Confirmation modal functionality
    showConfirmationModal(message, confirmCallback, cancelCallback) {
        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-60';
        modal.innerHTML = `
            <div class="modal-content bg-slate-800 rounded-lg shadow-lg w-full max-w-md p-6">
                <p class="text-white mb-6">${message}</p>
                <div class="flex justify-end gap-2">
                    <button type="button" class="cancel-btn py-2 px-4 rounded bg-gray-600 text-white hover:bg-gray-500">Cancel</button>
                    <button type="button" class="confirm-btn py-2 px-4 rounded bg-red-600 text-white hover:bg-red-700">Confirm</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        const confirmBtn = modal.querySelector('.confirm-btn');
        const cancelBtn = modal.querySelector('.cancel-btn');
        
        confirmBtn.addEventListener('click', () => {
            document.body.removeChild(modal);
            if (confirmCallback) confirmCallback();
        });
        
        cancelBtn.addEventListener('click', () => {
            document.body.removeChild(modal);
            if (cancelCallback) cancelCallback();
        });
        
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                document.body.removeChild(modal);
                if (cancelCallback) cancelCallback();
            }
        });
    }
};

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('Backtesting Dashboard initialized');
    
    // Add CSS animations
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideIn {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        
        @keyframes slideOut {
            from { transform: translateX(0); opacity: 1; }
            to { transform: translateX(100%); opacity: 0; }
        }
        
        .nav-link.active {
            background-color: rgba(255, 255, 255, 0.2);
            border-radius: 6px;
        }
    `;
    document.head.appendChild(style);
    
    // Setup global widget functionality
    WidgetUtils.setupMinimizeButtons();
    WidgetUtils.setupModals();
    WidgetUtils.setupSymbolDropdowns();
    
    // Set up navigation event listeners
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const view = link.dataset.view;
            if (view) {
                Navigation.navigateTo(view);
            }
        });
    });
    
    // Initialize with dashboard view
    Navigation.navigateTo('dashboard');
});

// Export for use in other modules
window.AppState = AppState;
window.Utils = Utils;
window.ChartUtils = ChartUtils;
window.Navigation = Navigation;
window.WidgetUtils = WidgetUtils; 