"""
Widget JS Build and Copy Logic

- Each widget (e.g. report, portfolio) lives in its own folder under server/widgets/.
- Each widget folder contains:
    - index.html   (widget HTML)
    - index.js     (widget JavaScript, ES module)
    - widget.py    (optional: Python render logic)

- You should edit the JS source files in these folders.
- When you run `make server` (which runs this script), the latest JS files are automatically copied to public/js/ as:
    - public/js/report.js
    - public/js/portfolio.js
  (and so on for other widgets)
- The dashboard imports the JS from public/js/ for production use.
- This ensures you can edit source files safely, and only the latest code is served to the browser.

To add a new widget:
- Create a new folder in server/widgets/ (e.g. mywidget/), add index.html and index.js.
- Add a copy step below to copy mywidget/index.js to public/js/mywidget.js.
"""
import subprocess
import sys
import webbrowser
import time
import signal
import shutil
import os
from server.dashboard_generator import generate_dashboard

if __name__ == '__main__':
    print('Generating dashboard...')
    generate_dashboard()
    print('Dashboard generated.')

    # Copy widget JS files to public/js with widget-prefixed names
    os.makedirs('public/js', exist_ok=True)
    widgets_dir = 'server/widgets'
    for widget_name in os.listdir(widgets_dir):
        widget_path = os.path.join(widgets_dir, widget_name)
        js_src = os.path.join(widget_path, 'index.js')
        if os.path.isdir(widget_path) and os.path.isfile(js_src):
            js_dst = os.path.join('public/js', f'{widget_name}.js')
            shutil.copyfile(js_src, js_dst)
            print(f'Copied {js_src} to {js_dst}')
    print('Copied widget JS files to public/js/')

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
