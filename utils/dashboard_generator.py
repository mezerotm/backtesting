import os
import glob
import re
import pandas as pd
from datetime import datetime
import webbrowser
from jinja2 import Template
import json
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import shutil

def get_report_metadata(html_path):
    """Extract metadata from report filename and content."""
    filename = os.path.basename(html_path)
    
    # Extract information from filename
    # Pattern: SYMBOL_STRATEGY_TIMEFRAME_START_END.html or similar patterns
    parts = filename.replace('.html', '').split('_')
    
    metadata = {
        'path': filename,  # Store just the filename, not the full path
        'filename': filename,
        'type': 'unknown'
    }
    
    # Try to determine if it's a comparison report or single strategy report
    if 'comparison' in filename.lower() or 'report' in filename.lower():
        metadata['type'] = 'comparison'
        metadata['title'] = 'Strategy Comparison Report'
    else:
        # It's likely a single strategy backtest
        metadata['type'] = 'backtest'
        
        # Extract symbol, strategy, timeframe if possible
        if len(parts) >= 3:
            metadata['symbol'] = parts[0]
            metadata['strategy'] = parts[1]
            
            # The timeframe might be part of the remaining elements
            timeframe_patterns = ['1m', '5m', '15m', '30m', '1h', '1d', '1w']
            for pattern in timeframe_patterns:
                if pattern in parts[2:]:
                    metadata['timeframe'] = pattern
                    break
    
    # Try to extract dates
    date_pattern = r'(\d{4}-\d{2}-\d{2})'
    dates = re.findall(date_pattern, filename)
    if len(dates) >= 1:
        metadata['start_date'] = dates[0]
    if len(dates) >= 2:
        metadata['end_date'] = dates[1]
    
    # Get file creation/modification time
    metadata['created'] = datetime.fromtimestamp(
        os.path.getctime(html_path)
    ).strftime('%Y-%m-%d %H:%M:%S')
    
    return metadata

def generate_dashboard():
    """Generate a dashboard HTML file with links to all reports."""
    # Get the path to the results directory
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    results_dir = os.path.join(script_dir, 'results')
    
    # Ensure results directory exists
    if not os.path.exists(results_dir):
        os.makedirs(results_dir)
    
    # Ensure public directory exists
    public_dir = os.path.join(script_dir, 'public')
    if not os.path.exists(public_dir):
        os.makedirs(public_dir)
    
    # Find all HTML files in the results directory
    html_files = glob.glob(os.path.join(results_dir, '*.html'))
    
    # Extract metadata from each report
    reports = [get_report_metadata(file) for file in html_files]
    
    # Sort reports: comparison reports first, then by date (newest first)
    reports.sort(key=lambda x: (0 if x['type'] == 'comparison' else 1, 
                               x.get('created', ''), 
                               x.get('symbol', '')))
    
    # Get unique symbols and strategies for filtering
    symbols = sorted(list(set(report.get('symbol', '') for report in reports if 'symbol' in report)))
    strategies = sorted(list(set(report.get('strategy', '') for report in reports if 'strategy' in report)))
    
    # Create the dashboard HTML template using Tailwind CSS
    template = Template('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Trading Strategy Dashboard</title>
        <!-- Favicon -->
        <link rel="icon" href="favicon.ico" type="image/x-icon">
        <link rel="shortcut icon" href="favicon.ico" type="image/x-icon">
        <!-- Tailwind CSS CDN -->
        <script src="https://cdn.tailwindcss.com"></script>
        <script>
            // Auto-refresh functionality
            let countdown = 10;
            let countdownInterval;
            
            function startCountdown() {
                countdown = 10;
                document.getElementById('countdown').textContent = countdown;
                
                countdownInterval = setInterval(() => {
                    countdown--;
                    document.getElementById('countdown').textContent = countdown;
                    
                    if (countdown <= 0) {
                        clearInterval(countdownInterval);
                        refreshPage();
                    }
                }, 1000);
            }
            
            function refreshPage() {
                clearInterval(countdownInterval);
                window.location.reload();
            }
            
            function cleanResults() {
                if (confirm('Are you sure you want to clean all results? This action cannot be undone.')) {
                    fetch('/clean-results', { method: 'POST' })
                        .then(response => response.json())
                        .then(data => {
                            alert(data.message);
                            refreshPage();
                        })
                        .catch(error => {
                            console.error('Error cleaning results:', error);
                            alert('Error cleaning results. See console for details.');
                        });
                }
            }
            
            // Start countdown on page load
            document.addEventListener('DOMContentLoaded', startCountdown);
        </script>
    </head>
    <body class="bg-gray-100 font-sans">
        <div class="max-w-7xl mx-auto px-4 py-6">
            <!-- Header -->
            <header class="bg-slate-800 text-white p-6 rounded-lg shadow-md mb-6">
                <div class="flex justify-between items-center">
                    <div>
                        <h1 class="text-3xl font-bold">Trading Strategy Dashboard</h1>
                        <p class="text-gray-300">Access and analyze all your trading strategy backtest results</p>
                    </div>
                    <div class="flex space-x-4">
                        <div class="flex items-center">
                            <button onclick="refreshPage()" class="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-md transition duration-300">
                                Refresh
                            </button>
                            <span class="ml-2 text-gray-300">Auto-refresh: <span id="countdown">10</span>s</span>
                        </div>
                        <button onclick="cleanResults()" class="bg-red-500 hover:bg-red-600 text-white px-4 py-2 rounded-md transition duration-300">
                            Clean Results
                        </button>
                    </div>
                </div>
            </header>
            
            <div class="flex flex-col lg:flex-row gap-6">
                <!-- Filters Panel -->
                <div class="w-full lg:w-1/4 bg-white p-6 rounded-lg shadow-sm">
                    <h2 class="text-xl font-bold mb-4 text-gray-800">Filters</h2>
                    
                    <div class="mb-4">
                        <label for="report-type" class="block font-medium text-gray-700 mb-1">Report Type:</label>
                        <select id="report-type" class="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500">
                            <option value="all">All Reports</option>
                            <option value="comparison">Comparison Reports</option>
                            <option value="backtest">Backtest Reports</option>
                        </select>
                    </div>
                    
                    <div class="mb-4">
                        <label for="symbol" class="block font-medium text-gray-700 mb-1">Symbol:</label>
                        <select id="symbol" class="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500">
                            <option value="all">All Symbols</option>
                            {% for symbol in symbols %}
                            <option value="{{ symbol }}">{{ symbol }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    
                    <div class="mb-4">
                        <label for="strategy" class="block font-medium text-gray-700 mb-1">Strategy:</label>
                        <select id="strategy" class="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500">
                            <option value="all">All Strategies</option>
                            {% for strategy in strategies %}
                            <option value="{{ strategy }}">{{ strategy }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    
                    <div class="mb-6">
                        <label for="date-range" class="block font-medium text-gray-700 mb-1">Date Range:</label>
                        <input type="date" id="start-date" class="w-full border border-gray-300 rounded-md px-3 py-2 mb-2 focus:outline-none focus:ring-2 focus:ring-blue-500" placeholder="Start Date">
                        <input type="date" id="end-date" class="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" placeholder="End Date">
                    </div>
                    
                    <div class="flex gap-2">
                        <button id="apply-filters" class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md transition duration-300 flex-1">Apply Filters</button>
                        <button id="reset-filters" class="bg-gray-200 hover:bg-gray-300 text-gray-800 px-4 py-2 rounded-md transition duration-300 flex-1">Reset</button>
                    </div>
                </div>
                
                <!-- Reports Panel -->
                <div class="w-full lg:w-3/4 bg-white p-6 rounded-lg shadow-sm">
                    <h2 class="text-xl font-bold mb-4 text-gray-800">Available Reports</h2>
                    
                    <!-- Last Updated Indicator -->
                    <div class="text-sm text-gray-500 mb-4">
                        Last updated: <span id="last-updated">{{ now }}</span>
                    </div>
                    
                    <!-- Comparison Reports Section -->
                    <div class="mb-8">
                        <h3 class="text-lg font-semibold mb-3 text-gray-700 border-b pb-2">Strategy Comparison Reports</h3>
                        {% set has_comparison = false %}
                        <div class="overflow-x-auto">
                            <table id="comparison-table" class="min-w-full">
                                <thead class="bg-gray-50">
                                    <tr>
                                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Action</th>
                                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Symbol</th>
                                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Report</th>
                                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Timeframe</th>
                                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date Range</th>
                                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Created</th>
                                    </tr>
                                </thead>
                                <tbody class="bg-white divide-y divide-gray-200">
                                    {% for report in reports %}
                                        {% if report.type == 'comparison' %}
                                            {% set has_comparison = true %}
                                            <tr class="report-row hover:bg-gray-50" 
                                                data-type="{{ report.type }}" 
                                                data-symbol="{{ report.get('symbol', '') }}" 
                                                data-strategy="{{ report.get('strategy', '') }}"
                                                data-start-date="{{ report.get('start_date', '') }}"
                                                data-end-date="{{ report.get('end_date', '') }}">
                                                <td class="px-6 py-4 whitespace-nowrap text-sm">
                                                    <a href="results/{{ report.path }}" target="_blank" class="text-blue-600 hover:text-blue-900 font-medium">View Report</a>
                                                </td>
                                                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{{ report.get('symbol', 'Multiple') }}</td>
                                                <td class="px-6 py-4 whitespace-nowrap">
                                                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">Comparison</span>
                                                    <span class="ml-2">{{ report.get('title', report.filename) }}</span>
                                                </td>
                                                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{{ report.get('timeframe', 'Various') }}</td>
                                                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                    {% if report.get('start_date') and report.get('end_date') %}
                                                        {{ report.get('start_date') }} to {{ report.get('end_date') }}
                                                    {% else %}
                                                        Various
                                                    {% endif %}
                                                </td>
                                                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{{ report.created }}</td>
                                            </tr>
                                        {% endif %}
                                    {% endfor %}
                                    {% if not has_comparison %}
                                        <tr>
                                            <td colspan="6" class="px-6 py-8 text-center text-gray-500 italic">No comparison reports available</td>
                                        </tr>
                                    {% endif %}
                                </tbody>
                            </table>
                        </div>
                    </div>
                    
                    <!-- Backtest Reports Section -->
                    <div>
                        <h3 class="text-lg font-semibold mb-3 text-gray-700 border-b pb-2">Individual Backtest Reports</h3>
                        {% set has_backtest = false %}
                        <div class="overflow-x-auto">
                            <table id="backtest-table" class="min-w-full">
                                <thead class="bg-gray-50">
                                    <tr>
                                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Action</th>
                                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Symbol</th>
                                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Strategy</th>
                                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Timeframe</th>
                                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date Range</th>
                                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Created</th>
                                    </tr>
                                </thead>
                                <tbody class="bg-white divide-y divide-gray-200">
                                    {% for report in reports %}
                                        {% if report.type == 'backtest' %}
                                            {% set has_backtest = true %}
                                            <tr class="report-row hover:bg-gray-50" 
                                                data-type="{{ report.type }}" 
                                                data-symbol="{{ report.get('symbol', '') }}" 
                                                data-strategy="{{ report.get('strategy', '') }}"
                                                data-start-date="{{ report.get('start_date', '') }}"
                                                data-end-date="{{ report.get('end_date', '') }}">
                                                <td class="px-6 py-4 whitespace-nowrap text-sm">
                                                    <a href="results/{{ report.path }}" target="_blank" class="text-blue-600 hover:text-blue-900 font-medium">View Report</a>
                                                </td>
                                                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{{ report.get('symbol', 'Unknown') }}</td>
                                                <td class="px-6 py-4 whitespace-nowrap">
                                                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">Backtest</span>
                                                    <span class="ml-2">{{ report.get('strategy', 'Unknown') }}</span>
                                                </td>
                                                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{{ report.get('timeframe', 'Unknown') }}</td>
                                                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                    {% if report.get('start_date') and report.get('end_date') %}
                                                        {{ report.get('start_date') }} to {{ report.get('end_date') }}
                                                    {% else %}
                                                        Unknown
                                                    {% endif %}
                                                </td>
                                                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{{ report.created }}</td>
                                            </tr>
                                        {% endif %}
                                    {% endfor %}
                                    {% if not has_backtest %}
                                        <tr>
                                            <td colspan="6" class="px-6 py-8 text-center text-gray-500 italic">No backtest reports available</td>
                                        </tr>
                                    {% endif %}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Glossary Section -->
            <div class="mt-8 bg-white p-6 rounded-lg shadow-sm">
                <h2 class="text-xl font-bold mb-4 text-gray-800">Trading Strategy Glossary</h2>
                
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    <div class="p-4 border border-gray-100 rounded-lg shadow-sm">
                        <div class="font-semibold text-gray-800">Return [%]</div>
                        <div class="mt-1 text-sm text-gray-600">The total percentage return of the strategy over the backtest period.</div>
                    </div>
                    
                    <div class="p-4 border border-gray-100 rounded-lg shadow-sm">
                        <div class="font-semibold text-gray-800">Buy & Hold Return [%]</div>
                        <div class="mt-1 text-sm text-gray-600">The percentage return from buying and holding the asset for the entire backtest period.</div>
                    </div>
                    
                    <div class="p-4 border border-gray-100 rounded-lg shadow-sm">
                        <div class="font-semibold text-gray-800">Max. Drawdown [%]</div>
                        <div class="mt-1 text-sm text-gray-600">The maximum observed loss from a peak to a trough during the backtest period, expressed as a percentage.</div>
                    </div>
                    
                    <div class="p-4 border border-gray-100 rounded-lg shadow-sm">
                        <div class="font-semibold text-gray-800">Sharpe Ratio</div>
                        <div class="mt-1 text-sm text-gray-600">A measure of risk-adjusted return. Higher values indicate better risk-adjusted performance.</div>
                    </div>
                    
                    <div class="p-4 border border-gray-100 rounded-lg shadow-sm">
                        <div class="font-semibold text-gray-800">SQN (System Quality Number)</div>
                        <div class="mt-1 text-sm text-gray-600">A metric that rates trading systems based on the consistency and size of profits relative to risk.</div>
                    </div>
                    
                    <div class="p-4 border border-gray-100 rounded-lg shadow-sm">
                        <div class="font-semibold text-gray-800">Win Rate [%]</div>
                        <div class="mt-1 text-sm text-gray-600">The percentage of trades that were profitable.</div>
                    </div>
                    
                    <div class="p-4 border border-gray-100 rounded-lg shadow-sm">
                        <div class="font-semibold text-gray-800">SMA (Simple Moving Average)</div>
                        <div class="mt-1 text-sm text-gray-600">The average price over a specific number of periods, giving equal weight to each period.</div>
                    </div>
                    
                    <div class="p-4 border border-gray-100 rounded-lg shadow-sm">
                        <div class="font-semibold text-gray-800">EMA (Exponential Moving Average)</div>
                        <div class="mt-1 text-sm text-gray-600">A type of weighted moving average that gives more importance to recent prices.</div>
                    </div>
                    
                    <div class="p-4 border border-gray-100 rounded-lg shadow-sm">
                        <div class="font-semibold text-gray-800">MACD (Moving Average Convergence Divergence)</div>
                        <div class="mt-1 text-sm text-gray-600">A trend-following momentum indicator that shows the relationship between two moving averages of a security's price.</div>
                    </div>
                    
                    <div class="p-4 border border-gray-100 rounded-lg shadow-sm">
                        <div class="font-semibold text-gray-800">RSI (Relative Strength Index)</div>
                        <div class="mt-1 text-sm text-gray-600">A momentum oscillator that measures the speed and change of price movements on a scale from 0 to 100.</div>
                    </div>
                    
                    <div class="p-4 border border-gray-100 rounded-lg shadow-sm">
                        <div class="font-semibold text-gray-800">Bollinger Bands</div>
                        <div class="mt-1 text-sm text-gray-600">A volatility indicator consisting of a moving average (middle band) with an upper and lower band representing standard deviations from that average.</div>
                    </div>
                </div>
            </div>
            
            <footer class="mt-8 text-center text-gray-500 text-sm">
                <p>Auto-updating dashboard for trading strategy reports</p>
            </footer>
        </div>
        
        <script>
            // Filtering system
            document.addEventListener('DOMContentLoaded', function() {
                const applyFiltersBtn = document.getElementById('apply-filters');
                const resetFiltersBtn = document.getElementById('reset-filters');
                const reportRows = document.querySelectorAll('.report-row');
                
                applyFiltersBtn.addEventListener('click', function() {
                    const reportType = document.getElementById('report-type').value;
                    const symbol = document.getElementById('symbol').value;
                    const strategy = document.getElementById('strategy').value;
                    const startDate = document.getElementById('start-date').value;
                    const endDate = document.getElementById('end-date').value;
                    
                    reportRows.forEach(row => {
                        // Start with visible and then apply filters
                        let visible = true;
                        
                        // Filter by report type
                        if (reportType !== 'all' && row.dataset.type !== reportType) {
                            visible = false;
                        }
                        
                        // Filter by symbol
                        if (visible && symbol !== 'all' && row.dataset.symbol !== symbol) {
                            visible = false;
                        }
                        
                        // Filter by strategy
                        if (visible && strategy !== 'all' && row.dataset.strategy !== strategy) {
                            visible = false;
                        }
                        
                        // Filter by date range
                        if (visible && startDate && row.dataset.startDate && row.dataset.startDate < startDate) {
                            visible = false;
                        }
                        if (visible && endDate && row.dataset.endDate && row.dataset.endDate > endDate) {
                            visible = false;
                        }
                        
                        // Apply visibility
                        row.classList.toggle('hidden', !visible);
                    });
                });
                
                resetFiltersBtn.addEventListener('click', function() {
                    document.getElementById('report-type').value = 'all';
                    document.getElementById('symbol').value = 'all';
                    document.getElementById('strategy').value = 'all';
                    document.getElementById('start-date').value = '';
                    document.getElementById('end-date').value = '';
                    
                    reportRows.forEach(row => {
                        row.classList.remove('hidden');
                    });
                });
                
                // Start the auto-refresh countdown
                startCountdown();
            });
        </script>
    </body>
    </html>
    ''')
    
    # Render the template with our data
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    dashboard_html = template.render(
        reports=reports,
        symbols=symbols,
        strategies=strategies,
        now=current_time
    )
    
    # Create the dashboard HTML file in the public directory as index.html
    public_dir = os.path.join(script_dir, 'public')
    dashboard_path = os.path.join(public_dir, 'index.html')
    with open(dashboard_path, 'w') as f:
        f.write(dashboard_html)
    
    print(f"Dashboard generated at: {dashboard_path}")
    return dashboard_path

# File watcher class to detect changes and update the dashboard
class DashboardUpdateHandler(FileSystemEventHandler):
    def __init__(self, results_dir):
        self.results_dir = results_dir
        self.last_update_time = time.time()
        # Prevent multiple updates within this time window (seconds)
        self.update_cooldown = 5
        
    def on_created(self, event):
        self._handle_event(event)
        
    def on_modified(self, event):
        self._handle_event(event)
        
    def on_deleted(self, event):
        self._handle_event(event)
        
    def _handle_event(self, event):
        # Skip if not an HTML file or if it's the dashboard itself
        if not event.src_path.endswith('.html') or 'dashboard.html' in event.src_path:
            return
        
        # Skip if we've updated recently (to avoid multiple rapid updates)
        current_time = time.time()
        if current_time - self.last_update_time < self.update_cooldown:
            return
            
        self.last_update_time = current_time
        print(f"Detected change in results directory: {event.src_path}")
        print("Regenerating dashboard...")
        generate_dashboard()

# HTTP server to serve the dashboard
class DashboardServer:
    def __init__(self, port=8000):
        self.port = port
        self.server = None
        self.server_thread = None
        
    def start(self):
        # Get the script directory and public directory
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        public_dir = os.path.join(script_dir, 'public')
        
        # Change to the public directory to serve files from there
        os.chdir(public_dir)
        
        # Create a custom handler that can handle the clean results request
        class CustomHTTPHandler(SimpleHTTPRequestHandler):
            def do_POST(self):
                if self.path == '/clean-results':
                    try:
                        # Get the results directory path
                        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                        results_dir = os.path.join(script_dir, 'results')
                        
                        # Clean the results directory
                        for item in os.listdir(results_dir):
                            item_path = os.path.join(results_dir, item)
                            if os.path.isfile(item_path):
                                os.unlink(item_path)
                            elif os.path.isdir(item_path):
                                shutil.rmtree(item_path)
                        
                        # Regenerate the dashboard after cleaning
                        generate_dashboard()
                        
                        # Send response
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps({'message': 'Results cleaned successfully'}).encode())
                    except Exception as e:
                        self.send_response(500)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps({'error': str(e)}).encode())
                else:
                    self.send_response(404)
                    self.end_headers()
            
            # Override log_message method to reduce console output
            def log_message(self, format, *args):
                # Only log errors, not regular requests
                if args[1].startswith('4') or args[1].startswith('5'):
                    super().log_message(format, *args)
                    
            # Override translate_path to handle /results/ URLs
            def translate_path(self, path):
                # First get the standard translation
                path = SimpleHTTPRequestHandler.translate_path(self, path)
                
                # Check if it's a request for a results file
                if 'results/' in self.path and not os.path.exists(path):
                    # Find the actual results directory
                    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    results_dir = os.path.join(script_dir, 'results')
                    
                    # Get the filename from the path
                    filename = os.path.basename(self.path)
                    
                    # Return the path to the file in the results directory
                    return os.path.join(results_dir, filename)
                    
                return path
        
        # Use CustomHTTPHandler to handle requests
        handler = CustomHTTPHandler
        self.server = HTTPServer(('localhost', self.port), handler)
        
        # Run server in a separate thread
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()
        
        # Ensure favicon exists in the public directory
        favicon_path = os.path.join(public_dir, 'favicon.ico')
        if not os.path.exists(favicon_path):
            print(f"Note: No favicon.ico found in {public_dir}")
            print("You may want to add one for better user experience")
        
        print(f"Dashboard server running at http://localhost:{self.port}/")
        
    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            print("Dashboard server stopped")

def start_dashboard_server(open_browser=True):
    """Start a server to host the dashboard with live updates."""
    # Get the results directory path
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    results_dir = os.path.join(script_dir, 'results')
    
    # Generate the initial dashboard
    dashboard_path = generate_dashboard()
    
    # Set up file watcher
    event_handler = DashboardUpdateHandler(results_dir)
    observer = Observer()
    observer.schedule(event_handler, results_dir, recursive=True)
    observer.start()
    
    # Start HTTP server
    server = DashboardServer()
    server.start()
    
    url = f"http://localhost:{server.port}/"
    if open_browser:
        webbrowser.open(url)
    
    try:
        print(f"Dashboard is running at {url}")
        print("Press Ctrl+C to stop the server")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping dashboard server...")
        observer.stop()
        server.stop()
        observer.join()

def open_dashboard():
    """Generate and open the dashboard in a web browser."""
    # For backwards compatibility
    start_dashboard_server(open_browser=True)
    
def generate_dashboard_only():
    """Generate the dashboard without opening it in a browser."""
    dashboard_path = generate_dashboard()
    return dashboard_path

if __name__ == "__main__":
    start_dashboard_server() 