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
import logging

logger = logging.getLogger(__name__)

def get_report_metadata(report_dir):
    """Extract metadata from report directory's metadata.json file."""
    metadata_path = os.path.join(report_dir, "metadata.json")
    
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
                
                # Add additional info that might not be in metadata
                metadata['dir'] = os.path.basename(report_dir)
                
                # Standardize dates to ISO format
                if 'start_date' in metadata:
                    metadata['start_date'] = datetime.strptime(metadata['start_date'], '%Y-%m-%d').strftime('%Y-%m-%d')
                if 'end_date' in metadata:
                    metadata['end_date'] = datetime.strptime(metadata['end_date'], '%Y-%m-%d').strftime('%Y-%m-%d')
                if 'created' in metadata:
                    metadata['created'] = datetime.strptime(metadata['created'], '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H:%M:%S')
                
                # Ensure we have a path property
                if 'path' not in metadata:
                    metadata['path'] = f"results/{metadata['dir']}/index.html"
                    
                return metadata
        except Exception as e:
            print(f"Error reading metadata from {metadata_path}: {e}")
            
    # If we couldn't read the metadata, create a basic one from the directory name
    dir_name = os.path.basename(report_dir)
    parts = dir_name.split('_')
    
    metadata = {
        'dir': dir_name,
        'path': f"results/{dir_name}/index.html",
        'type': 'unknown',
        'created': datetime.fromtimestamp(
            os.path.getctime(report_dir)
        ).strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # Try to determine report type from directory name
    if 'comparison' in dir_name.lower():
        metadata['type'] = 'comparison'
    elif any(strategy in dir_name.lower() for strategy in ['sma', 'ema', 'macd', 'bb']):
        metadata['type'] = 'backtest'
    else:
        metadata['type'] = 'chart'
    
    # Try to extract symbol
    if parts and parts[0].isalpha() and len(parts[0]) <= 5:
        metadata['symbol'] = parts[0]
    
    # Try to extract strategy
    if len(parts) >= 2:
        for strategy in ['SMA', 'EMA', 'MACD', 'BB', 'RSI', 'Bollinger']:
            if any(strategy.lower() in part.lower() for part in parts):
                metadata['strategy'] = strategy
                break
    
    return metadata

def format_report_date(report):
    """Format the report date based on report type."""
    if not report:
        return '-'
    
    if report.get('timeframe') == "snapshot" or report.get('type') == "financial":
        return report.get('created', '-').split(' ')[0]  # Just get the date part
    
    start = report.get('start_date', '-')
    end = report.get('end_date', '-')
    return f"{start} → {end}"

def generate_dashboard(refresh_interval=1000):
    """Generate a dashboard HTML file with links to all reports."""
    try:
        # Get the path to the results directory
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        public_dir = os.path.join(script_dir, 'public')
        results_dir = os.path.join(public_dir, 'results')
        
        # Ensure results directory exists
        if not os.path.exists(results_dir):
            os.makedirs(results_dir)
        
        # Find all report directories
        report_dirs = []
        for item in os.listdir(results_dir):
            item_path = os.path.join(results_dir, item)
            if os.path.isdir(item_path):
                report_dirs.append(item_path)
        
        # Extract metadata from each report directory
        reports = []
        for dir in report_dirs:
            try:
                metadata = get_report_metadata(dir)
                if metadata:
                    reports.append(metadata)
            except Exception as e:
                logger.error(f"Error processing report directory {dir}: {e}")
                continue
        
        # Sort reports by creation time (newest first)
        reports.sort(key=lambda x: x.get('created', ''), reverse=True)
        
        # Set up Jinja environment
        env = Environment(loader=FileSystemLoader('templates'))
        template = env.get_template('dashboard.html')
        
        # Render dashboard with reports data
        dashboard_html = template.render(
            reports=reports,
            refresh_interval=refresh_interval,
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            format_report_date=format_report_date  # Pass the function to template
        )
        
        # Save dashboard
        dashboard_path = os.path.join(public_dir, 'index.html')
        with open(dashboard_path, 'w', encoding='utf-8') as f:
            f.write(dashboard_html)
        
        return dashboard_path
        
    except Exception as e:
        logger.error(f"Error generating dashboard: {e}", exc_info=True)
        raise

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
            # Add this method to handle file not found errors
            def send_error(self, code, message=None):
                if code == 404:
                    # Path to custom 404 page
                    error_page_path = os.path.join(public_dir, '404.html')
                    
                    if os.path.exists(error_page_path):
                        # Read the custom 404 page
                        with open(error_page_path, 'rb') as f:
                            content = f.read()
                        
                        # Send response
                        self.send_response(404)
                        self.send_header('Content-type', 'text/html')
                        self.send_header('Content-Length', str(len(content)))
                        self.end_headers()
                        self.wfile.write(content)
                        return
                
                # If no custom page or different error, use default handler
                SimpleHTTPRequestHandler.send_error(self, code, message)
            
            def do_GET(self):
                if self.path == '/reports-data':
                    try:
                        # Get the results directory path
                        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                        public_dir = os.path.join(script_dir, 'public')
                        results_dir = os.path.join(public_dir, 'results')
                        
                        # Find all report directories
                        report_dirs = []
                        for item in os.listdir(results_dir):
                            item_path = os.path.join(results_dir, item)
                            if os.path.isdir(item_path):
                                report_dirs.append(item_path)
                        
                        # Extract metadata from each report directory
                        reports = [get_report_metadata(dir) for dir in report_dirs]
                        
                        # Sort reports by creation time, newest first
                        reports = sorted(reports, key=lambda report: report.get('created_timestamp', 0), reverse=True)
                        
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
                        public_dir = os.path.join(script_dir, 'public')
                        results_dir = os.path.join(public_dir, 'results')
                        
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
                elif self.path.startswith('/delete-report/'):
                    try:
                        # Extract report directory name from URL
                        report_dir = self.path.split('/delete-report/')[1]
                        
                        # Get the results directory path
                        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                        public_dir = os.path.join(script_dir, 'public')
                        results_dir = os.path.join(public_dir, 'results')
                        report_path = os.path.join(results_dir, report_dir)
                        
                        # Verify the path is within results directory and exists
                        if os.path.commonprefix([os.path.abspath(report_path), results_dir]) == results_dir and os.path.exists(report_path):
                            # Delete the report directory
                            shutil.rmtree(report_path)
                            
                            # Send success response
                            self.send_response(200)
                            self.send_header('Content-type', 'application/json')
                            self.end_headers()
                            self.wfile.write(json.dumps({'message': 'Report deleted successfully'}).encode())
                        else:
                            raise ValueError('Invalid report directory')
                            
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
    public_dir = os.path.join(script_dir, 'public')
    results_dir = os.path.join(public_dir, 'results')
    
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