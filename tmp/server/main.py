"""
FastAPI Server Entry Point

This script starts the FastAPI backend server that provides:
- API endpoints for portfolio, orders, dividends, profit/loss data
- Authentication endpoints
- Report generation endpoints
- Static file serving for the built frontend

==============================================================================
SECURITY NOTE: STATIC FILE SERVING
==============================================================================
IMPORTANT: Only files in the 'public' directory should be served to users!

Source directories that should NEVER be served:
- server/     (API source code, templates, configuration)
- utils/      (utility modules, database clients)
- strategies/ (trading strategy source code)
- workflows/  (workflow source code)
- libs/       (libraries, binaries, PocketBase)
- logs/       (sensitive log files)

The 'public' directory is the ONLY safe directory to serve because it contains:
- Compiled/built assets (CSS, JS, images) from Vite
- Static files safe for public access
- No source code or sensitive information

When adding new static files, always place them in 'public/' and reference them as '/static/filename'
==============================================================================
"""
import subprocess
import sys
import webbrowser
import time
import signal
import shutil
import os
import logging

# Configure logging to suppress verbose HTTP logs
logging.basicConfig(
    level=logging.WARNING,
    format='%(levelname)s:%(name)s:%(message)s'
)

# Suppress verbose HTTP request logs
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

if __name__ == '__main__':
    print('Starting FastAPI server...')
    print('Frontend assets are built by Vite - run "make build-frontend" to build')
    proc = subprocess.Popen([sys.executable,
                             '-m',
                             'uvicorn',
                             'server.api.main:app',
                             '--host',
                             '0.0.0.0',
                             '--port',
                             '8000',
                             '--log-level',
                             'error',
                             '--no-access-log'])

    # Optionally open browser
    time.sleep(2)
    print('Opening browser to http://localhost:8000/')
    webbrowser.open('http://localhost:8000/')

    try:
        proc.wait()
    except KeyboardInterrupt:
        print('Received Ctrl+C, shutting down server...')
        proc.send_signal(signal.SIGINT)
        try:
            proc.wait(timeout=10)  # Wait up to 10 seconds for clean shutdown
        except subprocess.TimeoutExpired:
            print('Server not responding, forcing shutdown...')
            proc.kill()  # Force kill if it doesn't respond
            proc.wait()
        print('Server stopped.')
