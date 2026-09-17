# CDP Browser Self-Testing for UI Changes

## Why

The user should never see console errors. Before the user tests a UI change, verify it yourself via headless Chrome CDP.

## Prerequisites

Shared Chrome service must be running:
```bash
systemctl --user status chrome-shared
```

If not running:
```bash
systemctl --user start chrome-shared
```

## The Script

`/home/mezerotm/workspaces/agents/scripts/browser_check.py`

Usage:
```bash
python3 /home/mezerotm/workspaces/agents/scripts/browser_check.py <url> [wait_seconds]
```

Example:
```bash
python3 /home/mezerotm/workspaces/agents/scripts/browser_check.py http://192.168.1.184:9129/ 5
```

Output:
```json
{
  "title": "Finance Dashboard",
  "errors": [],
  "warnings": []
}
```

If errors exist, fix them before asking the user to test.

## Workflow

1. Make frontend changes to `public/index.html` (no build needed)
2. Run `browser_check.py` against the dashboard URL
3. If errors reported → fix them → repeat step 2
4. Only when clean → tell the user to refresh

## How It Works

- Opens a new browser tab via Chrome DevTools Protocol (CDP) on port 9222
- Listens for `Runtime.consoleAPICalled`, `Runtime.exceptionThrown`, and `Network.loadingFailed` events
- Waits the configured time for the page to load and all scripts to execute
- Returns captured errors/warnings as JSON
- Closes the test tab automatically

## Known Limitations

- Only catches errors that fire during page load + the wait period
- Async errors that fire seconds later (e.g. after sync completes) won't be caught unless wait is increased
- Network failures for API calls (404, 500) ARE caught via `Network.loadingFailed`
- Alpine expression errors (like `formatElapsed is not defined`) ARE caught via `Runtime.consoleAPICalled`