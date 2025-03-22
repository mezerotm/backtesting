import os
import glob
import re
import pandas as pd
from datetime import datetime
import webbrowser
from jinja2 import Template, FileSystemLoader, Environment
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
    
    # Try to determine report type
    if 'comparison' in filename.lower():
        metadata['type'] = 'comparison'
        # Create more specific titles for comparison reports
        if parts[0].isalpha() and len(parts[0]) <= 5:  # Likely a symbol
            metadata['symbol'] = parts[0]
            metadata['title'] = f"{parts[0]} Strategy Comparison"
        else:
            metadata['symbol'] = 'Various'
            metadata['title'] = 'Multi-Strategy Comparison'
    elif 'report' in filename.lower() and 'backtest' not in filename.lower():
        metadata['type'] = 'comparison'
        metadata['title'] = 'Strategy Comparison Report'
        
        # Extract symbol if it's in the filename (first part is usually the symbol)
        if len(parts) >= 1 and parts[0].isalpha() and len(parts[0]) <= 5:
            metadata['symbol'] = parts[0]
            metadata['title'] = f"{parts[0]} {metadata['title']}"
        else:
            metadata['symbol'] = 'Various'
    # Check for chart-only reports (no backtest results)
    elif 'chart' in filename.lower() or all(indicator in filename.lower() for indicator in ['sma', '1d']):
        metadata['type'] = 'chart'
        
        if len(parts) >= 1 and parts[0].isalpha() and len(parts[0]) <= 5:
            metadata['symbol'] = parts[0]
            metadata['title'] = f"{parts[0]} Chart"
        else:
            metadata['symbol'] = 'Unknown'
            metadata['title'] = "Price Chart"
            
        if len(parts) >= 2:
            indicator = parts[1]
            metadata['strategy'] = indicator
            metadata['title'] += f" with {indicator}"
            
        # The timeframe might be part of the remaining elements
        timeframe_patterns = ['1m', '5m', '15m', '30m', '1h', '1d', '1w']
        for pattern in timeframe_patterns:
            if pattern in parts[2:]:
                metadata['timeframe'] = pattern
                metadata['title'] += f" ({pattern})"
                break
    else:
        # It's likely a single strategy backtest
        metadata['type'] = 'backtest'
        
        # Extract symbol, strategy, timeframe if possible
        if len(parts) >= 1 and parts[0].isalpha() and len(parts[0]) <= 5:
            metadata['symbol'] = parts[0]
            # Update title with symbol
            metadata['title'] = f"{parts[0]}"
        else:
            metadata['symbol'] = 'Unknown'
            metadata['title'] = "Backtest"
            
        if len(parts) >= 2:
            metadata['strategy'] = parts[1]
            # Add strategy to title
            metadata['title'] += f" {parts[1]} Strategy"
            
        # The timeframe might be part of the remaining elements
        timeframe_patterns = ['1m', '5m', '15m', '30m', '1h', '1d', '1w']
        for pattern in timeframe_patterns:
            if pattern in parts[2:]:
                metadata['timeframe'] = pattern
                metadata['title'] += f" ({pattern})"
                break
    
    # Try to extract dates
    date_pattern = r'(\d{4}-\d{2}-\d{2})'
    dates = re.findall(date_pattern, filename)
    if len(dates) >= 1:
        metadata['start_date'] = dates[0]
    if len(dates) >= 2:
        metadata['end_date'] = dates[1]
        
        # Add date range to title if we have both dates
        if 'start_date' in metadata and 'end_date' in metadata and 'title' in metadata:
            metadata['title'] += f" {metadata['start_date']} to {metadata['end_date']}"
    
    # Read the HTML file to extract more accurate information if possible
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # Try to extract title from HTML
            title_match = re.search(r'<title>(.*?)</title>', content)
            if title_match and 'title' not in metadata:
                metadata['title'] = title_match.group(1)
                
            # For backtest reports, try to identify strategy from content
            if metadata['type'] == 'unknown' or metadata['type'] == 'backtest':
                strategy_patterns = ['SMA', 'EMA', 'MACD', 'RSI', 'Bollinger']
                for pattern in strategy_patterns:
                    if pattern in content:
                        metadata['strategy'] = pattern
                        if 'title' in metadata:
                            if "Strategy" not in metadata['title'] and "Chart" not in metadata['title']:
                                metadata['title'] += f" {pattern} Strategy"
                        break
                
                # Try to determine if it's a chart-only report
                if 'Backtest Results' not in content and any(indicator in content for indicator in 
                                                          ['SMA', 'EMA', 'MACD', 'RSI', 'Bollinger']):
                    metadata['type'] = 'chart'
                    if 'title' in metadata and 'Chart' not in metadata['title']:
                        metadata['title'] = metadata['title'].replace('Strategy', 'Chart')
    except Exception as e:
        print(f"Warning: Could not extract additional metadata from {html_path}: {e}")
    
    # Get file creation/modification time
    metadata['created'] = datetime.fromtimestamp(
        os.path.getctime(html_path)
    ).strftime('%Y-%m-%d %H:%M:%S')
    
    return metadata

def generate_dashboard(refresh_interval=1000):
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
    
    # Set up Jinja2 environment to load template from file
    templates_dir = os.path.join(script_dir, 'templates')
    env = Environment(loader=FileSystemLoader(templates_dir))
    template = env.get_template('dashboard.html')
    
    # Render the template with our data
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    current_year = datetime.now().year
    
    dashboard_html = template.render(
        reports=reports,
        symbols=symbols,
        strategies=strategies,
        now=current_time,
        current_year=current_year,
        refresh_interval=refresh_interval
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
        # For deletion events, wait a bit longer to let all deletions complete
        current_time = time.time()
        if current_time - self.last_update_time < self.update_cooldown:
            return
            
        self.last_update_time = current_time
        print(f"Detected file deletion: {event.src_path}")
        # Add a small delay to allow multiple deletions to complete
        time.sleep(0.5)
        print("Regenerating dashboard after deletion...")
        generate_dashboard()
        
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
            def do_GET(self):
                if self.path == '/reports-data':
                    try:
                        # Get the results directory path
                        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                        results_dir = os.path.join(script_dir, 'results')
                        
                        # Find all HTML files in the results directory
                        html_files = glob.glob(os.path.join(results_dir, '*.html'))
                        
                        # Extract metadata from each report
                        reports = [get_report_metadata(file) for file in html_files]
                        
                        # Sort reports: comparison reports first, then by date (newest first)
                        reports.sort(key=lambda x: (0 if x['type'] == 'comparison' else 1, 
                                                  x.get('created', ''), 
                                                  x.get('symbol', '')))
                        
                        # Prepare the response data
                        response_data = {
                            'reports': reports,
                            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        }
                        
                        # Send response
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps(response_data, default=str).encode())
                    except Exception as e:
                        self.send_response(500)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps({'error': str(e)}).encode())
                else:
                    super().do_GET()
            
            def do_POST(self):
                if self.path == '/clean-results':
                    try:
                        # Get the results directory path
                        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                        results_dir = os.path.join(script_dir, 'results')
                        
                        # Check if directory exists before cleaning
                        if os.path.exists(results_dir):
                            # Clean the results directory
                            for item in os.listdir(results_dir):
                                item_path = os.path.join(results_dir, item)
                                try:
                                    if os.path.isfile(item_path):
                                        os.unlink(item_path)
                                    elif os.path.isdir(item_path):
                                        shutil.rmtree(item_path)
                                except Exception as e:
                                    print(f"Error while deleting {item_path}: {e}")
                        
                        # Wait a moment for file system events to settle
                        time.sleep(0.5)
                        
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
    
    # Set refresh interval to 1 second (1000 ms)
    refresh_interval = 1000
    
    # Generate the initial dashboard with the refresh interval
    dashboard_path = generate_dashboard(refresh_interval=refresh_interval)
    
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
        print(f"Auto-refresh interval: {refresh_interval/1000} seconds")
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
    # Set refresh interval to 1 second (1000 ms)
    refresh_interval = 1000
        
    dashboard_path = generate_dashboard(refresh_interval=refresh_interval)
    return dashboard_path

if __name__ == "__main__":
    start_dashboard_server() 