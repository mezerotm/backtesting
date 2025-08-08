// Main JavaScript for Backtesting Dashboard

// Import styles
import './styles/main.css';

// Import Preline UI components
import 'preline/dist/preline.js';

// Import frontend data models for validation
import { 
    validateData, 
    validateAndTransform, 
    withValidatedData, 
    validateApiResponse, 
    formatValidationErrors, 
    handleValidationError,
    SCHEMA_REGISTRY 
} from './data_models.js';

// Global state management
const AppState = {
    isLoading: false,
    currentView: 'landing', // Start with landing page
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
    
    // API request helper with validation
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
            
            // Validate response data if validation is available
            if (typeof validateApiResponse === 'function') {
                const validation = validateApiResponse(endpoint, data);
                if (!validation.success) {
                    console.warn(`API response validation failed for ${endpoint}:`, validation.errors);
                    handleValidationError(validation.errors, `API Response (${endpoint})`);
                }
            }
            
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
    },
    
    // Landing page navigation
    goToDashboard() {
        window.location.href = '/dashboard.html';
    },
    
    goToLanding() {
        window.location.href = '/landing.html';
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
        console.log('[WidgetUtils] Setting up minimize buttons...');
        const buttons = document.querySelectorAll('[id$="MinimizeBtn"]');
        console.log(`[WidgetUtils] Found ${buttons.length} minimize buttons:`, Array.from(buttons).map(btn => btn.id));
        
        buttons.forEach(btn => {
            console.log(`[WidgetUtils] Setting up minimize button: ${btn.id}`);
            btn.addEventListener('click', function() {
                const widgetId = this.id.replace('MinimizeBtn', '');
                const contentId = widgetId + 'Content';
                const actionBarId = widgetId + 'ActionBar';
                const iconId = widgetId + 'MinimizeIcon';
                const content = document.getElementById(contentId);
                const actionBar = document.getElementById(actionBarId);
                const icon = document.getElementById(iconId);
                console.log(`[WidgetUtils] ${widgetId} widget elements - contentId: ${contentId}, iconId: ${iconId}, content: ${!!content}, icon: ${!!icon}`);
                
                if (content && icon) {
                    const isCollapsed = content.classList.contains('collapsed');
                    console.log(`[WidgetUtils] ${widgetId} widget - isCollapsed: ${isCollapsed}, content: ${content.id}, icon: ${icon.id}`);
                    
                    if (isCollapsed) {
                        // Expand the widget
                        content.classList.remove('collapsed');
                        // Show action bar for all widgets
                        if (actionBar) {
                            actionBar.classList.remove('collapsed');
                        }
                        icon.className = 'fa-solid fa-chevron-up';
                        console.log(`[WidgetUtils] ${widgetId} widget expanded, icon set to chevron-up`);
                    } else {
                        // Collapse the widget
                        content.classList.add('collapsed');
                        // Hide action bar for all widgets
                        if (actionBar) {
                            actionBar.classList.add('collapsed');
                        }
                        icon.className = 'fa-solid fa-chevron-down';
                        console.log(`[WidgetUtils] ${widgetId} widget collapsed, icon set to chevron-down`);
                    }
                } else {
                    console.log(`[WidgetUtils] Missing elements for ${widgetId} widget - content: ${!!content}, icon: ${!!icon}`);
                }
            });
        });
        console.log('[WidgetUtils] Minimize buttons setup complete');
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
                    const query = (this.value || '').trim();
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
document.addEventListener('DOMContentLoaded', async function() {
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
    
    // Setup global widget functionality (modals and symbol dropdowns)
    WidgetUtils.setupModals();
    WidgetUtils.setupSymbolDropdowns();
    
    // Import and initialize widgets
    try {
        console.log('Initializing dashboard widgets...');
        
        // Import widgets from the new location
        console.log('Importing widgets...');
        const { initReport } = await import('./widgets/report/index.js');
        console.log('Report widget imported');
        const { initPortfolio } = await import('./widgets/portfolio/index.js');
        console.log('Portfolio widget imported');
        const { initOrders } = await import('./widgets/orders/index.js');
        console.log('Orders widget imported');
        const { initDividends } = await import('./widgets/dividends/index.js');
        console.log('Dividends widget imported');
        const { initProfitLoss } = await import('./widgets/profit_loss/index.js');
        console.log('Profit/Loss widget imported');
        
        // Initialize widgets with a small delay to ensure HTML is rendered
        setTimeout(() => {
            try {
                console.log('Initializing Report widget...');
                initReport();
                console.log('Report widget initialized');
                
                console.log('Initializing Portfolio widget...');
                initPortfolio();
                console.log('Portfolio widget initialized');
                
                console.log('Initializing Orders widget...');
                initOrders();
                console.log('Orders widget initialized');
                
                console.log('Initializing Dividends widget...');
                initDividends();
                console.log('Dividends widget initialized');
                
                console.log('Initializing Profit/Loss widget...');
                initProfitLoss();
                console.log('Profit/Loss widget initialized');
                
                console.log('All dashboard widgets initialized successfully');
                
                // Setup minimize buttons AFTER widgets are initialized
                console.log('Setting up minimize buttons...');
                WidgetUtils.setupMinimizeButtons();
                console.log('Minimize buttons setup complete');
            } catch (error) {
                console.error('Error during widget initialization:', error);
            }
        }, 100); // Small delay to ensure HTML is rendered
    } catch (error) {
        console.error('Error initializing dashboard widgets:', error);
    }
    
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

// Global 10-minute sync timer for integrations
setInterval(async () => {
    try {
        console.log('[Global Sync] Triggering Robinhood pull...');
        await Utils.apiRequest('/api/robinhood/pull', { method: 'POST' });
        console.log('[Global Sync] Robinhood pull complete.');
    } catch (err) {
        console.error('[Global Sync] Robinhood pull failed:', err);
    }
    try {
        console.log('[Global Sync] Triggering Polygon symbol data refresh...');
        await Utils.apiRequest('/api/portfolio/refresh-symbols', { method: 'POST' });
        console.log('[Global Sync] Polygon symbol data refresh complete.');
    } catch (err) {
        console.error('[Global Sync] Polygon symbol data refresh failed:', err);
    }
}, 10 * 60 * 1000); // 10 minutes in ms

// Initial sync on page load
setTimeout(async () => {
    try {
        console.log('[Initial Sync] Triggering Polygon symbol data refresh...');
        await Utils.apiRequest('/api/portfolio/refresh-symbols', { method: 'POST' });
        console.log('[Initial Sync] Polygon symbol data refresh complete.');
    } catch (err) {
        console.error('[Initial Sync] Polygon symbol data refresh failed:', err);
    }
}, 2000); // Wait 2 seconds after page load

// Export for use in other modules
window.AppState = AppState;
window.Utils = Utils;
window.ChartUtils = ChartUtils;
window.Navigation = Navigation;
window.WidgetUtils = WidgetUtils;

// Export validation utilities globally
window.DataModels = {
    validateData,
    validateAndTransform,
    withValidatedData,
    validateApiResponse,
    formatValidationErrors,
    handleValidationError,
    SCHEMA_REGISTRY
};

// Login functionality
let currentUser = null;

// DOM elements
const loginBtn = document.getElementById('loginBtn');
const loginBtnText = document.getElementById('loginBtnText');
const loginModal = document.getElementById('loginModal');
const closeLoginModal = document.getElementById('closeLoginModal');
const loginForm = document.getElementById('loginForm');
const registerBtn = document.getElementById('registerBtn');
const loginError = document.getElementById('loginError');

// Show login modal
function showLoginModal() {
    loginModal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
    
    // Focus on email input after modal is shown
    setTimeout(() => {
        const emailInput = document.getElementById('email');
        if (emailInput) {
            emailInput.focus();
        }
    }, 100);
}

// Hide login modal
function hideLoginModal() {
    loginModal.classList.add('hidden');
    document.body.style.overflow = 'auto';
    loginError.classList.add('hidden');
    loginForm.reset();
}

// Show error message
function showError(message) {
    loginError.textContent = message;
    loginError.classList.remove('hidden');
}

function showCreateAccountError(message) {
    const errorDiv = document.getElementById('createAccountError');
    if (errorDiv) {
        errorDiv.textContent = message;
        errorDiv.classList.remove('hidden');
    }
}

function hideCreateAccountError() {
    const errorDiv = document.getElementById('createAccountError');
    if (errorDiv) {
        errorDiv.classList.add('hidden');
    }
}

function showCreateAccountSuccess(message) {
    const successDiv = document.getElementById('createAccountSuccess');
    if (successDiv) {
        successDiv.textContent = message;
        successDiv.classList.remove('hidden');
    }
}

function hideCreateAccountSuccess() {
    const successDiv = document.getElementById('createAccountSuccess');
    if (successDiv) {
        successDiv.classList.add('hidden');
    }
}

// Update login button text
function updateLoginButton() {
    if (currentUser) {
        loginBtnText.textContent = currentUser.name || currentUser.email;
        loginBtn.className = 'bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg flex items-center gap-2 transition-colors';
        loginBtn.innerHTML = '<i class="fas fa-user"></i><span>' + (currentUser.name || currentUser.email) + '</span>';
    } else {
        loginBtnText.textContent = 'Login';
        loginBtn.className = 'bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg flex items-center gap-2 transition-colors';
        loginBtn.innerHTML = '<i class="fas fa-sign-in-alt"></i><span>Login</span>';
    }
}

// Check if user is logged in on page load
async function checkAuthStatus() {
    try {
        console.log('Checking auth status...');
        console.log('Current pathname:', window.location.pathname);
        console.log('Cookies:', document.cookie);
        
        console.log('Making auth request to /api/auth/me...');
        const response = await fetch('/api/auth/me', {
            credentials: 'include'  // Required to send authentication cookies
        });
        console.log('Auth response received:', response.status, response.statusText);
        console.log('Auth status response:', response.status, response.statusText);
        
        if (response.ok) {
            const data = await response.json();
            console.log('Auth data received:', data);
            
            // Extract user data from the response structure
            if (data.success && data.user && data.user.user_id) {
                currentUser = {
                    user_id: data.user.user_id,
                    email: data.user.email,
                    name: data.user.name
                };
                updateLoginButton();
                console.log('User is logged in:', currentUser);
                
                // If user is logged in and on landing page or create account page, redirect to dashboard
                if (window.location.pathname.includes('landing.html') || 
                    window.location.pathname.includes('create-account.html') || 
                    window.location.pathname === '/') {
                    console.log('User is logged in but on landing page - redirecting to dashboard');
                    window.location.href = '/dashboard.html';
                }
            } else {
                console.log('Auth response indicates not logged in');
                currentUser = null;
                updateLoginButton();
                
                // If user is not logged in and on dashboard, redirect to landing page
                if (window.location.pathname.includes('dashboard.html')) {
                    console.log('User is not logged in and on dashboard - redirecting to landing page');
                    window.location.href = '/landing.html';
                }
            }
        } else {
            const errorData = await response.json().catch(() => ({}));
            console.log('Auth check failed:', response.status, errorData);
            console.log('User is not logged in');
            currentUser = null;
            updateLoginButton();
            
            // If user is not logged in and on dashboard, redirect to landing page
            if (window.location.pathname.includes('dashboard.html')) {
                console.log('Auth failed and user is on dashboard - redirecting to landing page');
                window.location.href = '/landing.html';
            }
        }
    } catch (error) {
        console.error('Error checking auth status:', error);
        currentUser = null;
        updateLoginButton();
        
        // If auth check fails and user is on dashboard, redirect to landing page
        if (window.location.pathname.includes('dashboard.html')) {
            console.log('Auth check error and user is on dashboard - redirecting to landing page');
            window.location.href = '/landing.html';
        }
    }
}

// Handle login form submission
async function handleLogin(event) {
    event.preventDefault();
    
    const formData = new FormData(loginForm);
    const email = formData.get('email');
    const password = formData.get('password');
    
    try {
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include',  // Required to send authentication cookies
            body: JSON.stringify({ email, password }),
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            currentUser = {
                user_id: data.user.user_id,
                email: data.user.email,
                name: data.user.name
            };
            updateLoginButton();
            hideLoginModal();
            
            // Show success message
            showToast('Login successful!', 'success');
            
            // Check if we're on the landing page and redirect to dashboard
            if (window.location.pathname.includes('landing.html') || window.location.pathname === '/') {
                setTimeout(() => {
                    window.location.href = '/dashboard.html';
                }, 1500);
                return;
            }
            
            // Refresh all widget data without page reload
            setTimeout(() => {
                console.log('Refreshing all widget data after login...');
                
                // Refresh symbol data first to get current market prices
                fetch('/api/portfolio/refresh-symbols', { method: 'POST' })
                    .then(() => {
                        console.log('Symbol data refreshed after login');
                        
                        // Refresh portfolio data
                        if (typeof window.fetchPositionsAndSettings === 'function') {
                            window.fetchPositionsAndSettings();
                        } else if (typeof window.fetchPositionsAndCash === 'function') {
                            window.fetchPositionsAndCash();
                        }
                        
                        // Refresh orders data
                        if (typeof window.fetchAndRenderOrders === 'function') {
                            window.fetchAndRenderOrders();
                        }
                        
                        // Refresh dividends data
                        if (typeof window.fetchAndRenderDividends === 'function') {
                            window.fetchAndRenderDividends();
                        }
                        
                        // Refresh profit/loss data
                        if (typeof window.fetchAndRenderProfitLoss === 'function') {
                            window.fetchAndRenderProfitLoss();
                        }
                    })
                    .catch(err => {
                        console.error('Failed to refresh symbol data after login:', err);
                        // Still refresh other widgets even if symbol refresh fails
                        
                        // Refresh portfolio data
                        if (typeof window.fetchPositionsAndSettings === 'function') {
                            window.fetchPositionsAndSettings();
                        } else if (typeof window.fetchPositionsAndCash === 'function') {
                            window.fetchPositionsAndCash();
                        }
                        
                        // Refresh orders data
                        if (typeof window.fetchAndRenderOrders === 'function') {
                            window.fetchAndRenderOrders();
                        }
                        
                        // Refresh dividends data
                        if (typeof window.fetchAndRenderDividends === 'function') {
                            window.fetchAndRenderDividends();
                        }
                        
                        // Refresh profit/loss data
                        if (typeof window.fetchAndRenderProfitLoss === 'function') {
                            window.fetchAndRenderProfitLoss();
                        }
                    });
            }, 1000);
        } else {
            showError(data.message || 'Login failed');
        }
    } catch (error) {
        console.error('Login error:', error);
        showError('Network error. Please try again.');
    }
}

// Handle create account form submission
async function handleCreateAccount(event) {
    event.preventDefault();
    
    const formData = new FormData(createAccountForm);
    const name = formData.get('name');
    const email = formData.get('email');
    const password = formData.get('password');
    const confirmPassword = formData.get('confirmPassword');
    const terms = formData.get('terms');
    
    // Clear previous errors
    hideCreateAccountError();
    hideCreateAccountSuccess();
    
    // Validation
    if (!name || !email || !password || !confirmPassword) {
        showCreateAccountError('Please fill in all fields');
        return;
    }
    
    if (password.length < 8) {
        showCreateAccountError('Password must be at least 8 characters long');
        return;
    }
    
    if (password !== confirmPassword) {
        showCreateAccountError('Passwords do not match');
        return;
    }
    
    if (!terms) {
        showCreateAccountError('Please agree to the Terms of Service and Privacy Policy');
        return;
    }
    
    try {
        const response = await fetch('/api/auth/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify({ 
                email, 
                password, 
                password_confirm: password,
                name 
            }),
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            showCreateAccountSuccess('Account created successfully! Redirecting to dashboard...');
            
            // Set current user
            currentUser = {
                user_id: data.user.user_id,
                email: data.user.email,
                name: data.user.name
            };
            updateLoginButton();
            
            // Redirect to dashboard after a short delay
            setTimeout(() => {
                window.location.href = '/dashboard.html';
            }, 2000);
        } else {
            showCreateAccountError(data.message || 'Account creation failed');
        }
    } catch (error) {
        console.error('Create account error:', error);
        showCreateAccountError('Network error. Please try again.');
    }
}

// Handle registration (for modal)
async function handleRegister() {
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const name = email.split('@')[0]; // Use email prefix as name
    
    if (!email || !password) {
        showError('Please fill in all fields');
        return;
    }
    
    if (password.length < 8) {
        showError('Password must be at least 8 characters long');
        return;
    }
    
    try {
        const response = await fetch('/api/auth/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include',  // Required to send authentication cookies
            body: JSON.stringify({ 
                email, 
                password, 
                password_confirm: password,
                name 
            }),
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            currentUser = {
                user_id: data.user.user_id,
                email: data.user.email,
                name: data.user.name
            };
            updateLoginButton();
            hideLoginModal();
            
            // Show success message
            showToast('Registration successful!', 'success');
            
            // Refresh all widget data without page reload
            setTimeout(() => {
                console.log('Refreshing all widget data after registration...');
                
                // Refresh symbol data first to get current market prices
                fetch('/api/portfolio/refresh-symbols', { method: 'POST' })
                    .then(() => {
                        console.log('Symbol data refreshed after registration');
                        
                        // Refresh portfolio data
                        if (typeof window.fetchPositionsAndSettings === 'function') {
                            window.fetchPositionsAndSettings();
                        } else if (typeof window.fetchPositionsAndCash === 'function') {
                            window.fetchPositionsAndCash();
                        }
                        
                        // Refresh orders data
                        if (typeof window.fetchAndRenderOrders === 'function') {
                            window.fetchAndRenderOrders();
                        }
                        
                        // Refresh dividends data
                        if (typeof window.fetchAndRenderDividends === 'function') {
                            window.fetchAndRenderDividends();
                        }
                        
                        // Refresh profit/loss data
                        if (typeof window.fetchAndRenderProfitLoss === 'function') {
                            window.fetchAndRenderProfitLoss();
                        }
                    })
                    .catch(err => {
                        console.error('Failed to refresh symbol data after registration:', err);
                        // Still refresh other widgets even if symbol refresh fails
                        
                        // Refresh portfolio data
                        if (typeof window.fetchPositionsAndSettings === 'function') {
                            window.fetchPositionsAndSettings();
                        } else if (typeof window.fetchPositionsAndCash === 'function') {
                            window.fetchPositionsAndCash();
                        }
                        
                        // Refresh orders data
                        if (typeof window.fetchAndRenderOrders === 'function') {
                            window.fetchAndRenderOrders();
                        }
                        
                        // Refresh dividends data
                        if (typeof window.fetchAndRenderDividends === 'function') {
                            window.fetchAndRenderDividends();
                        }
                        
                        // Refresh profit/loss data
                        if (typeof window.fetchAndRenderProfitLoss === 'function') {
                            window.fetchAndRenderProfitLoss();
                        }
                    });
            }, 1000);
        } else {
            showError(data.message || 'Registration failed');
        }
    } catch (error) {
        console.error('Registration error:', error);
        showError('Network error. Please try again.');
    }
}

// Handle logout
async function handleLogout() {
    try {
        const response = await fetch('/api/auth/logout', {
            method: 'POST',
            credentials: 'include',  // Required to send authentication cookies
        });
        
        if (response.ok) {
            currentUser = null;
            updateLoginButton();
            showToast('Logged out successfully', 'info');
            
            // Redirect to landing page if on dashboard
            if (window.location.pathname.includes('dashboard.html')) {
                setTimeout(() => {
                    window.location.href = '/landing.html';
                }, 1500);
                return;
            }
            
            // Clear portfolio data gracefully
            setTimeout(() => {
                // Clear portfolio display
                const portfolioTable = document.getElementById('positionsTbody');
                if (portfolioTable) {
                    portfolioTable.innerHTML = '<tr><td colspan="11" class="text-center text-gray-400 py-4">Please log in to view your portfolio</td></tr>';
                }
                
                // Clear other widgets
                const ordersTable = document.querySelector('[id*="orders"] tbody');
                if (ordersTable) {
                    ordersTable.innerHTML = '<tr><td colspan="6" class="text-center text-gray-400 py-4">Please log in to view your orders</td></tr>';
                }
                
                const dividendsTable = document.querySelector('[id*="dividends"] tbody');
                if (dividendsTable) {
                    dividendsTable.innerHTML = '<tr><td colspan="7" class="text-center text-gray-400 py-4">Please log in to view your dividends</td></tr>';
                }
            }, 1000);
        }
    } catch (error) {
        console.error('Logout error:', error);
    }
}

// Simple toast notification
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `fixed top-4 right-4 z-50 p-4 rounded-lg text-white ${
        type === 'success' ? 'bg-green-600' : 
        type === 'error' ? 'bg-red-600' : 'bg-blue-600'
    }`;
    toast.textContent = message;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.remove();
    }, 3000);
}

// Event listeners
if (loginBtn) loginBtn.addEventListener('click', () => {
    if (currentUser) {
        // Show logout confirmation
        if (confirm('Are you sure you want to logout?')) {
            handleLogout();
        }
    } else {
        showLoginModal();
    }
});

if (closeLoginModal) closeLoginModal.addEventListener('click', hideLoginModal);

if (loginModal) loginModal.addEventListener('click', (e) => {
    if (e.target === loginModal) {
        hideLoginModal();
    }
});

if (loginForm) loginForm.addEventListener('submit', handleLogin);

if (registerBtn) registerBtn.addEventListener('click', () => {
    hideLoginModal();
    window.location.href = '/create-account.html';
});

// Initialize auth status on page load
console.log('Initializing auth status check...');
checkAuthStatus();

// Also check auth status when DOM is fully loaded
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded - checking auth status again...');
    checkAuthStatus();
});

// Landing page event listeners
const learnMoreBtn = document.getElementById('learnMoreBtn');

if (learnMoreBtn) {
    learnMoreBtn.addEventListener('click', () => {
        // Scroll to features section
        const featuresSection = document.querySelector('.bg-slate-800');
        if (featuresSection) {
            featuresSection.scrollIntoView({ behavior: 'smooth' });
        }
    });
}

// Create account page event listeners
const createAccountForm = document.getElementById('createAccountForm');
const switchToLogin = document.getElementById('switchToLogin');

if (createAccountForm) {
    createAccountForm.addEventListener('submit', handleCreateAccount);
}

if (switchToLogin) {
    switchToLogin.addEventListener('click', (e) => {
        e.preventDefault();
        showLoginModal();
    });
} 