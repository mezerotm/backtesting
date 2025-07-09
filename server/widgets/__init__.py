"""
Widget Folder Structure and JS Build Logic

- Each widget (e.g. report, portfolio) lives in its own subfolder here.
- Each widget's folder contains:
    - index.html   (the widget's HTML)
    - index.js     (the widget's JavaScript logic, ES module)
    - widget.py    (optional: Python render logic)

- You should edit the JS source files in these folders.
- When you run `make server` (which runs main.py), the latest JS files are automatically copied to public/js/ as:
    - public/js/report.js
    - public/js/portfolio.js
  (and so on for other widgets)
- The dashboard imports the JS from public/js/ for production use.
- This ensures you can edit source files safely, and only the latest code is served to the browser.

To add a new widget:
- Create a new folder here (e.g. mywidget/), add index.html and index.js.
- Add a copy step in main.py to copy mywidget/index.js to public/js/mywidget.js.
"""
