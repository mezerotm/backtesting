import subprocess
import sys
import webbrowser
import time
import signal
from server.dashboard_generator import generate_dashboard

if __name__ == '__main__':
    print('Generating dashboard...')
    generate_dashboard()
    print('Dashboard generated.')

    print('Starting FastAPI server...')
    proc = subprocess.Popen([
        sys.executable, '-m', 'uvicorn', 'server.api.main:app', '--reload', '--host', '0.0.0.0', '--port', '8000'
    ])

    # Optionally open browser
    time.sleep(2)
    print('Opening browser to http://localhost:8000/')
    webbrowser.open('http://localhost:8000/')

    try:
        proc.wait()
    except KeyboardInterrupt:
        print('Received Ctrl+C, shutting down server...')
        proc.send_signal(signal.SIGINT)
        proc.wait()
        print('Server stopped.')
