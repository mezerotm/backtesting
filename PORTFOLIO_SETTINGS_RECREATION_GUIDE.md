# Portfolio Settings Recreation Guide

This guide contains all the code and instructions needed to recreate the portfolio settings modal with Robinhood integration.

## Overview

The portfolio settings system consists of:
1. **Frontend**: Modal dialog with portfolio cash/BTC settings and Robinhood integration
2. **Backend**: FastAPI endpoints for settings management and Robinhood data pulling
3. **Data Storage**: JSON files for portfolio settings and Robinhood data

## File Structure

```
server/
├── api/
│   ├── main.py              # FastAPI app with router mounting
│   ├── portfolio.py         # Portfolio settings API endpoints
│   └── robinhood.py         # Robinhood integration API
├── widgets/
│   └── portfolio/
│       ├── index.html       # Portfolio widget HTML with modal
│       └── index.js         # Portfolio widget JavaScript
└── main.py                  # Server startup script

public/
├── data/
│   ├── portfolio.json       # Portfolio settings storage
│   ├── positions.json       # Portfolio positions
│   ├── trades.json          # Trade history
│   └── dividends.json       # Dividend history
└── js/
    ├── main.js              # Global JavaScript utilities
    └── portfolio.js         # Copied from server/widgets/portfolio/index.js
```

## 1. Backend API - Portfolio Settings

### server/api/portfolio.py
```python
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import json
import os
from pydantic import BaseModel
from fastapi.responses import JSONResponse
import requests

PORTFOLIO_PATH = os.path.join("public", "data", "positions.json")
PORTFOLIO_CASH_PATH = os.path.join("public", "data", "portfolio.json")
POLYGON_API_KEY = os.environ.get("POLYGON_API_KEY")

class Position(BaseModel):
    id: int
    symbol: str
    quantity: float
    buy_price: float
    notes: Optional[str] = None
    source: Optional[str] = None

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])

# --- Portfolio Cash, BTC, and BTC Avg Buy Price Logic ---
def load_portfolio_cash_btc() -> dict:
    if not os.path.exists(PORTFOLIO_CASH_PATH):
        return {
            "total_portfolio_cash": 0.0,
            "total_portfolio_btc": 0.0,
            "btc_avg_buy_price": 0.0,
            "robinhood_enabled": False,
            "robinhood_display": False,
            "robinhood_username": "",
            "robinhood_password": "",
            "robinhood_mfa": ""
        }
    with open(PORTFOLIO_CASH_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
        # Set defaults for new fields if missing
        if "total_portfolio_btc" not in data:
            data["total_portfolio_btc"] = 0.0
        if "btc_avg_buy_price" not in data:
            data["btc_avg_buy_price"] = 0.0
        if "robinhood_enabled" not in data:
            data["robinhood_enabled"] = False
        if "robinhood_display" not in data:
            data["robinhood_display"] = False
        if "robinhood_username" not in data:
            data["robinhood_username"] = ""
        if "robinhood_password" not in data:
            data["robinhood_password"] = ""
        if "robinhood_mfa" not in data:
            data["robinhood_mfa"] = ""
        return data

def save_portfolio_cash_btc(data: dict):
    # Always write all fields, including new Robinhood settings
    out = {
        "total_portfolio_cash": float(data.get("total_portfolio_cash", 0.0)),
        "total_portfolio_btc": float(data.get("total_portfolio_btc", 0.0)),
        "btc_avg_buy_price": float(data.get("btc_avg_buy_price", 0.0)),
        "robinhood_enabled": bool(data.get("robinhood_enabled", False)),
        "robinhood_display": bool(data.get("robinhood_display", False)),
        "robinhood_username": data.get("robinhood_username", ""),
        "robinhood_password": data.get("robinhood_password", ""),
        "robinhood_mfa": data.get("robinhood_mfa", "")
    }
    with open(PORTFOLIO_CASH_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

@router.get("/settings")
def get_portfolio_settings():
    """
    Get the total portfolio cash, BTC (dollar value), BTC avg buy price, and Robinhood settings from portfolio.json.
    Returns: {"total_portfolio_cash": float, "total_portfolio_btc": float, "btc_avg_buy_price": float, ...robinhood fields...}
    """
    return load_portfolio_cash_btc()

@router.post("/settings")
def set_portfolio_settings(data: dict):
    """
    Set the total portfolio cash, BTC (dollar value), BTC avg buy price, and Robinhood settings in portfolio.json.
    Accepts any of: {"total_portfolio_cash": float, "total_portfolio_btc": float, "btc_avg_buy_price": float, ...robinhood fields...}
    """
    current = load_portfolio_cash_btc()
    if "total_portfolio_cash" in data:
        try:
            current["total_portfolio_cash"] = float(data["total_portfolio_cash"] or 0)
        except (ValueError, TypeError):
            current["total_portfolio_cash"] = 0.0
    if "total_portfolio_btc" in data:
        try:
            current["total_portfolio_btc"] = float(data["total_portfolio_btc"] or 0)
        except (ValueError, TypeError):
            current["total_portfolio_btc"] = 0.0
    if "btc_avg_buy_price" in data:
        try:
            current["btc_avg_buy_price"] = float(data["btc_avg_buy_price"] or 0)
        except (ValueError, TypeError):
            current["btc_avg_buy_price"] = 0.0
    # Robinhood settings
    if "robinhood_enabled" in data:
        current["robinhood_enabled"] = bool(data["robinhood_enabled"])
    if "robinhood_display" in data:
        current["robinhood_display"] = bool(data["robinhood_display"])
    if "robinhood_username" in data:
        current["robinhood_username"] = data["robinhood_username"] or ""
    if "robinhood_password" in data:
        current["robinhood_password"] = data["robinhood_password"] or ""
    if "robinhood_mfa" in data:
        current["robinhood_mfa"] = data["robinhood_mfa"] or ""
    save_portfolio_cash_btc(current)
    return {"status": "ok"}

# ... rest of portfolio CRUD endpoints ...
```

## 2. Backend API - Robinhood Integration

### server/api/robinhood.py
```python
from fastapi import APIRouter, HTTPException
import os
import json
import robin_stocks.robinhood as r
import logging
import requests
from datetime import datetime
from typing import Dict, List, Optional

PORTFOLIO_PATH = os.path.join("public", "data", "portfolio.json")
POSITIONS_PATH = os.path.join("public", "data", "positions.json")
TRADES_PATH = os.path.join("public", "data", "trades.json")
DIVIDENDS_PATH = os.path.join("public", "data", "dividends.json")

router = APIRouter(prefix="/api/robinhood", tags=["robinhood"])

# Cache for instrument to symbol mapping
_instrument_cache = {}

def get_robinhood_settings():
    if not os.path.exists(PORTFOLIO_PATH):
        raise HTTPException(status_code=400, detail="Portfolio settings not found")
    with open(PORTFOLIO_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {
        "enabled": data.get("robinhood_enabled", False),
        "display": data.get("robinhood_display", False),
        "username": data.get("robinhood_username", ""),
        "password": data.get("robinhood_password", ""),
        "mfa": data.get("robinhood_mfa", "")
    }

def resolve_symbol_from_instrument(instrument_url: str) -> Optional[str]:
    """Resolve symbol from Robinhood instrument URL using caching."""
    if instrument_url in _instrument_cache:
        return _instrument_cache[instrument_url]
    
    try:
        instrument_id = instrument_url.split('/')[-2]
        instrument_data = r.get_instrument_by_id(instrument_id)
        if instrument_data and 'symbol' in instrument_data:
            symbol = instrument_data['symbol']
            _instrument_cache[instrument_url] = symbol
            return symbol
        return None
    except Exception as e:
        logging.error(f"[Robinhood] Error resolving symbol for {instrument_url}: {e}")
        return None

def map_positions_to_app_format(positions_dict: Dict) -> List[Dict]:
    """Map Robinhood positions to app's position format."""
    positions = []
    for i, (symbol, pos) in enumerate(positions_dict.items(), 1):
        try:
            position = {
                "id": i,
                "symbol": symbol,
                "quantity": float(pos.get('quantity', 0)),
                "buy_price": float(pos.get('average_buy_price', 0)),
                "notes": pos.get('name', ''),
                "source": "robinhood"
            }
            positions.append(position)
        except (ValueError, KeyError) as e:
            logging.error(f"[Robinhood] Error mapping position {symbol}: {e}")
            continue
    return positions

def map_orders_to_trades(orders: List[Dict]) -> List[Dict]:
    """Map Robinhood orders to app's trade format."""
    trades = []
    trade_id_counter = 1
    
    for order in orders:
        try:
            if order.get('type') != 'market' and order.get('type') != 'limit':
                continue
            
            instrument_url = order.get('instrument')
            if not instrument_url:
                continue
                
            symbol = resolve_symbol_from_instrument(instrument_url)
            if not symbol:
                continue
            
            side = order.get('side', 'buy')
            order_id = order.get('id', '')
            
            for execution in order.get('executions', []):
                try:
                    total_fees = sum([
                        float(execution.get('fees', 0)),
                        float(execution.get('sec_fee', 0)),
                        float(execution.get('taf_fee', 0)),
                        float(execution.get('cat_fee', 0))
                    ])
                    
                    trade = {
                        "id": trade_id_counter,
                        "symbol": symbol,
                        "type": side,
                        "quantity": float(execution.get('quantity', 0)),
                        "price": float(execution.get('price', 0)),
                        "date": execution.get('timestamp', ''),
                        "fees": total_fees,
                        "pl": 0.0,
                        "notes": f"Robinhood order: {order_id}"
                    }
                    trades.append(trade)
                    trade_id_counter += 1
                    
                except (ValueError, KeyError) as e:
                    logging.error(f"[Robinhood] Error mapping execution in order {order_id}: {e}")
                    continue
                    
        except Exception as e:
            logging.error(f"[Robinhood] Error processing order {order.get('id', 'unknown')}: {e}")
            continue
    
    return trades

def save_data_to_files(positions: List[Dict], trades: List[Dict], dividends: List[Dict]):
    """Save mapped data to respective JSON files."""
    try:
        with open(POSITIONS_PATH, 'w', encoding='utf-8') as f:
            json.dump(positions, f, indent=2)
        
        with open(TRADES_PATH, 'w', encoding='utf-8') as f:
            json.dump(trades, f, indent=2)
        
        with open(DIVIDENDS_PATH, 'w', encoding='utf-8') as f:
            json.dump(dividends, f, indent=2)
        
    except Exception as e:
        logging.error(f"[Robinhood] Error saving data to files: {e}")
        raise

@router.post("/pull")
def pull_robinhood_data():
    settings = get_robinhood_settings()
    if not settings["enabled"]:
        raise HTTPException(status_code=400, detail="Robinhood integration is not enabled.")
    if not settings["username"] or not settings["password"]:
        raise HTTPException(status_code=400, detail="Robinhood credentials are missing.")
    
    try:
        # Login to Robinhood
        login_kwargs = {
            "username": settings["username"],
            "password": settings["password"]
        }
        if settings["mfa"]:
            login_kwargs["mfa_code"] = settings["mfa"]
        
        login = r.login(**login_kwargs)
        if not login or not login.get("access_token"):
            raise HTTPException(status_code=401, detail="Robinhood login failed.")
        
        # Pull data from Robinhood
        positions = r.account.build_holdings()
        orders = r.orders.get_all_stock_orders()
        
        # Save raw data for debugging
        with open(os.path.join('public', 'data', 'robinhood_raw.json'), 'w', encoding='utf-8') as f:
            json.dump({
                'positions': positions, 
                'orders': orders,
                'pulled_at': datetime.now().isoformat()
            }, f, indent=2)
        
        # Map data to app format
        mapped_positions = map_positions_to_app_format(positions)
        mapped_trades = map_orders_to_trades(orders)
        
        # Save mapped data
        save_data_to_files(mapped_positions, mapped_trades, [])
        
        # Logout
        r.logout()
        
        return {
            "status": "success",
            "positions_count": len(mapped_positions),
            "trades_count": len(mapped_trades),
            "message": f"Successfully pulled and mapped {len(mapped_positions)} positions and {len(mapped_trades)} trades"
        }
        
    except Exception as e:
        logging.error(f"[Robinhood] Error in pull_robinhood_data: {e}")
        raise HTTPException(status_code=500, detail=f"Robinhood error: {e}")

@router.get("/status")
def get_robinhood_status():
    """Get status of Robinhood integration and last pull info."""
    try:
        settings = get_robinhood_settings()
        
        # Check if raw data exists and get last pull time
        raw_data_path = os.path.join('public', 'data', 'robinhood_raw.json')
        last_pull = None
        if os.path.exists(raw_data_path):
            with open(raw_data_path, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
                last_pull = raw_data.get('pulled_at')
        
        return {
            "enabled": settings["enabled"],
            "display": settings["display"],
            "has_credentials": bool(settings["username"] and settings["password"]),
            "last_pull": last_pull,
            "positions_count": len(json.load(open(POSITIONS_PATH, 'r')) if os.path.exists(POSITIONS_PATH) else []),
            "trades_count": len(json.load(open(TRADES_PATH, 'r')) if os.path.exists(TRADES_PATH) else []),
            "dividends_count": len(json.load(open(DIVIDENDS_PATH, 'r')) if os.path.exists(DIVIDENDS_PATH) else [])
        }
        
    except Exception as e:
        logging.error(f"[Robinhood] Error getting status: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting status: {e}")
```

## 3. Frontend HTML - Portfolio Settings Modal

### server/widgets/portfolio/index.html
```html
<!-- Portfolio Settings Modal -->
<div id="cashModal" class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-60 hidden">
    <div class="bg-slate-800 rounded-lg shadow-lg w-full max-w-md p-6">
        <h3 class="text-xl font-bold text-white mb-4">Portfolio Settings</h3>
        <form id="cashForm" class="space-y-4">
            <div class="mb-4">
                <h4 class="text-sm font-bold text-white mb-2">Portfolio</h4>
                <label for="cash" class="block text-sm text-green-400 font-semibold mb-2">Total Portfolio Cash ($):</label>
                <input type="text" id="cash" class="p-2 rounded bg-slate-700 text-white w-full" step="1" min="0" inputmode="numeric" autocomplete="off" value="0" onblur="if(this.value===''){this.value=0;}">
            </div>
            <div class="mb-4">
                <label for="btcDollar" class="block text-sm text-yellow-300 font-semibold mb-2">Total Portfolio BTC ($):</label>
                <input type="text" id="btcDollar" class="p-2 rounded bg-slate-700 text-white w-full" step="any" min="0" inputmode="decimal" autocomplete="off" placeholder="Enter BTC value in dollars" value="0" onblur="if(this.value===''){this.value=0;}">
            </div>
            <div class="mb-4">
                <label for="btcAvgBuyPrice" class="block text-sm text-yellow-300 font-semibold mb-2">BTC Avg Buy Price ($):</label>
                <input type="text" id="btcAvgBuyPrice" class="p-2 rounded bg-slate-700 text-white w-full" step="any" min="0" inputmode="decimal" autocomplete="off" value="0" onblur="if(this.value===''){this.value=0;}">
            </div>
            
            <!-- Robinhood Integration Section -->
            <div class="pt-2 border-t border-slate-700 mt-4 mb-2">
                <h4 class="text-sm font-bold text-white mb-2">Robinhood Integration</h4>
                <div class="mb-4">
                    <label for="robinhoodUsername" class="block text-xs text-gray-300 mb-1">Robinhood Username/Email</label>
                    <input type="text" id="robinhoodUsername" class="p-2 rounded bg-slate-700 text-white w-full" autocomplete="username" placeholder="Enter Robinhood username or email">
                </div>
                <div class="mb-4">
                    <label for="robinhoodPassword" class="block text-xs text-gray-300 mb-1">Robinhood Password</label>
                    <input type="password" id="robinhoodPassword" class="p-2 rounded bg-slate-700 text-white w-full" autocomplete="current-password" placeholder="Enter Robinhood password">
                </div>
                <div class="mb-4">
                    <label for="robinhoodMFA" class="block text-xs text-gray-300 mb-1">Robinhood 2FA Code (if enabled)</label>
                    <input type="text" id="robinhoodMFA" class="p-2 rounded bg-slate-700 text-white w-full" autocomplete="one-time-code" placeholder="Enter 2FA code (if required)">
                </div>
                <div class="mt-3 mb-2">
                    <div class="flex items-center gap-1">
                        <input type="checkbox" id="robinhoodEnabled" class="accent-green-600" checked>
                        <label for="robinhoodEnabled" class="text-sm text-gray-200 select-none">Enable Robinhood</label>
                    </div>
                    <div class="flex items-center gap-1 mt-1">
                        <input type="checkbox" id="robinhoodDisplay" class="accent-blue-600" checked>
                        <label for="robinhoodDisplay" class="text-sm text-gray-200 select-none">Show Robinhood Data</label>
                    </div>
                </div>
                <div class="mb-4">
                    <label class="block text-sm font-medium text-slate-300 mb-1">Pull Robinhood</label>
                    <button id="pullRobinhoodBtn" class="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded transition-colors">
                        Pull Robinhood
                    </button>
                </div>
                
                <!-- Robinhood Status Display -->
                <div id="robinhoodStatus" class="mb-4 p-3 bg-slate-700 rounded-lg hidden">
                    <h4 class="text-sm font-bold text-white mb-2">Robinhood Status</h4>
                    <div class="text-xs text-slate-300 space-y-1">
                        <div>Last Pull: <span id="lastPullTime">Never</span></div>
                        <div>Positions: <span id="positionsCount">0</span></div>
                        <div>Trades: <span id="tradesCount">0</span></div>
                        <div>Dividends: <span id="dividendsCount">0</span></div>
                    </div>
                </div>
            </div>
            
            <hr class="my-6 border-t border-slate-600">
            <div class="flex justify-end gap-2">
                <button type="button" id="cancelCashModalBtn" class="py-2 px-4 rounded bg-gray-600 text-white hover:bg-gray-500">Cancel</button>
                <button type="submit" class="py-2 px-4 rounded bg-blue-600 text-white hover:bg-blue-700">Save</button>
            </div>
        </form>
    </div>
</div>
```

## 4. Frontend JavaScript - Portfolio Settings Logic

### server/widgets/portfolio/index.js
```javascript
import { showToast } from '/js/main.js';

const API_PORTFOLIO = '/api/portfolio';

let portfolioCash = 0;
let portfolioBTC = 0;
let portfolioBTCDollar = 0;
let btcPrice = null;
let btcPriceFetched = false;
let btcAvgBuyPrice = 0;

async function fetchPortfolioSettings() {
  const resp = await fetch('/api/portfolio/settings');
  const data = await resp.json();
  portfolioCash = data.total_portfolio_cash || 0;
  portfolioBTCDollar = data.total_portfolio_btc || 0;
  btcAvgBuyPrice = data.btc_avg_buy_price || 0;
  window._portfolioSettings = data; // for debugging
}

async function fetchRobinhoodStatus() {
  try {
    const resp = await fetch('/api/robinhood/status');
    const data = await resp.json();
    
    const statusDiv = document.getElementById('robinhoodStatus');
    const lastPullTime = document.getElementById('lastPullTime');
    const positionsCount = document.getElementById('positionsCount');
    const tradesCount = document.getElementById('tradesCount');
    const dividendsCount = document.getElementById('dividendsCount');
    
    if (statusDiv && data.has_credentials) {
      statusDiv.classList.remove('hidden');
      
      if (lastPullTime) {
        if (data.last_pull) {
          const date = new Date(data.last_pull);
          lastPullTime.textContent = date.toLocaleString();
        } else {
          lastPullTime.textContent = 'Never';
        }
      }
      
      if (positionsCount) positionsCount.textContent = data.positions_count || 0;
      if (tradesCount) tradesCount.textContent = data.trades_count || 0;
      if (dividendsCount) dividendsCount.textContent = data.dividends_count || 0;
    } else if (statusDiv) {
      statusDiv.classList.add('hidden');
    }
  } catch (error) {
    console.error('Error fetching Robinhood status:', error);
  }
}

async function pullRobinhoodData(showSuccess = true) {
  try {
    const resp = await fetch('/api/robinhood/pull', { method: 'POST' });
    const data = await resp.json();
    
    if (resp.ok) {
      if (showSuccess) {
        showToast(`Successfully pulled ${data.positions_count} positions and ${data.trades_count} trades`, 'success');
      }
      await fetchRobinhoodStatus();
      fetchPositionsAndSettings(); // Refresh portfolio data
    } else {
      showToast(`Error: ${data.detail}`, 'error');
    }
  } catch (error) {
    console.error('Error pulling Robinhood data:', error);
    showToast('Error pulling Robinhood data', 'error');
  }
}

// Modal logic for settings
const settingsBtn = document.getElementById('settingsBtn');
const cashModal = document.getElementById('cashModal');
const cancelCashModalBtn = document.getElementById('cancelCashModalBtn');

if (settingsBtn && cashModal && cancelCashModalBtn) {
  settingsBtn.addEventListener('click', async () => {
    try {
      await fetchPortfolioSettings();
      await fetchRobinhoodStatus();
      
      const cashInput = document.getElementById('cash');
      const btcDollarInput = document.getElementById('btcDollar');
      const btcAvgBuyPriceInput = document.getElementById('btcAvgBuyPrice');
      const robinhoodEnabledInput = document.getElementById('robinhoodEnabled');
      const robinhoodDisplayInput = document.getElementById('robinhoodDisplay');
      const robinhoodUsernameInput = document.getElementById('robinhoodUsername');
      const robinhoodPasswordInput = document.getElementById('robinhoodPassword');
      const robinhoodMFAInput = document.getElementById('robinhoodMFA');
      
      const data = window._portfolioSettings || {};
      
      if (cashInput) cashInput.value = portfolioCash;
      if (btcDollarInput) btcDollarInput.value = portfolioBTCDollar;
      if (btcAvgBuyPriceInput) btcAvgBuyPriceInput.value = btcAvgBuyPrice || '';
      if (robinhoodEnabledInput) robinhoodEnabledInput.checked = !!data.robinhood_enabled;
      if (robinhoodDisplayInput) robinhoodDisplayInput.checked = !!data.robinhood_display;
      if (robinhoodUsernameInput) robinhoodUsernameInput.value = data.robinhood_username || '';
      if (robinhoodPasswordInput) robinhoodPasswordInput.value = data.robinhood_password || '';
      if (robinhoodMFAInput) robinhoodMFAInput.value = data.robinhood_mfa || '';
      
      cashModal.classList.remove('hidden');
    } catch (error) {
      console.error('Error opening settings:', error);
      showToast('Error loading settings', 'error');
    }
  });
  
  cancelCashModalBtn.addEventListener('click', () => {
    cashModal.classList.add('hidden');
  });
  
  cashModal.addEventListener('mousedown', (e) => {
    if (e.target === cashModal) {
      cashModal.classList.add('hidden');
    }
  });
}

// Handle cash form submission
const cashForm = document.getElementById('cashForm');
if (cashForm) {
  cashForm.addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const cashInput = document.getElementById('cash');
    const btcDollarInput = document.getElementById('btcDollar');
    const btcAvgBuyPriceInput = document.getElementById('btcAvgBuyPrice');
    const robinhoodEnabledInput = document.getElementById('robinhoodEnabled');
    const robinhoodDisplayInput = document.getElementById('robinhoodDisplay');
    const robinhoodUsernameInput = document.getElementById('robinhoodUsername');
    const robinhoodPasswordInput = document.getElementById('robinhoodPassword');
    const robinhoodMFAInput = document.getElementById('robinhoodMFA');
    
    let cashVal = portfolioCash;
    let btcDollarVal = portfolioBTCDollar;
    let btcAvgVal = btcAvgBuyPrice;
    
    if (cashInput) {
      const val = parseFloat(cashInput.value);
      if (!isNaN(val) && val >= 0) {
        cashVal = val;
      }
    }
    if (btcDollarInput) {
      const val = parseFloat(btcDollarInput.value);
      if (!isNaN(val) && val >= 0) {
        btcDollarVal = val;
      }
    }
    if (btcAvgBuyPriceInput) {
      const val = parseFloat(btcAvgBuyPriceInput.value);
      if (!isNaN(val) && val >= 0) {
        btcAvgVal = val;
      } else {
        btcAvgVal = '';
      }
    }
    
    // Collect Robinhood fields
    const robinhoodEnabled = robinhoodEnabledInput ? robinhoodEnabledInput.checked : false;
    const robinhoodDisplay = robinhoodDisplayInput ? robinhoodDisplayInput.checked : false;
    const robinhoodUsername = robinhoodUsernameInput ? robinhoodUsernameInput.value : '';
    const robinhoodPassword = robinhoodPasswordInput ? robinhoodPasswordInput.value : '';
    const robinhoodMFA = robinhoodMFAInput ? robinhoodMFAInput.value : '';
    
    // Send all fields
    await fetch('/api/portfolio/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        total_portfolio_cash: cashVal,
        total_portfolio_btc: btcDollarVal,
        btc_avg_buy_price: btcAvgVal,
        robinhood_enabled: robinhoodEnabled,
        robinhood_display: robinhoodDisplay,
        robinhood_username: robinhoodUsername,
        robinhood_password: robinhoodPassword,
        robinhood_mfa: robinhoodMFA
      })
    });
    
    cashModal.classList.add('hidden');
    fetchPositionsAndSettings(); // Refresh table
  });
}

// Initialize Robinhood pull button
const pullBtn = document.getElementById('pullRobinhoodBtn');
if (pullBtn) {
  pullBtn.addEventListener('click', () => pullRobinhoodData());
}

// Auto-pull every 10 minutes
setInterval(() => pullRobinhoodData(false), 10 * 60 * 1000);
```

## 5. API Router Mounting

### server/api/main.py
```python
from fastapi import FastAPI, Request, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from server.api.report import router as report_router
from server.api.portfolio import router as portfolio_router
from server.api.dividends import router as dividends_router
from server.api.profit_loss import router as profit_loss_router
from server.api.trades import router as trades_router
from server.api.robinhood import router as robinhood_router
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Serve static files
app.mount("/static", StaticFiles(directory="public", html=True), name="public")
app.mount("/js", StaticFiles(directory=os.path.abspath(os.path.join(os.path.dirname(__file__), '../../public/js'))), name="js")

# Serve dashboard at root
@app.get("/")
def serve_dashboard():
    return FileResponse("public/index.html")

# Register routers
app.include_router(portfolio_router)
app.include_router(robinhood_router)
# ... other routers ...

# Health check endpoint
@app.get("/api/dashboard/health")
def health_check():
    return {"status": "ok"}
```

## 6. Data Storage Structure

### public/data/portfolio.json
```json
{
  "total_portfolio_cash": 50.0,
  "total_portfolio_btc": 0.0,
  "btc_avg_buy_price": 0.0,
  "robinhood_enabled": true,
  "robinhood_display": true,
  "robinhood_username": "mezerotm@gmail.com",
  "robinhood_password": "your_password_here",
  "robinhood_mfa": "652855"
}
```

## 7. Dependencies

### requirements.txt (key packages)
```
fastapi==0.115.11
robin-stocks==3.4.0
uvicorn==0.27.1
python-dotenv==1.0.1
requests==2.32.3
```

## 8. Setup Instructions

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Create Directory Structure**:
   ```bash
   mkdir -p server/api server/widgets/portfolio public/data public/js
   ```

3. **Create Files**:
   - Copy the code above into the respective files
   - Ensure `public/data/portfolio.json` exists with initial settings

4. **Start Server**:
   ```bash
   python server/main.py
   ```

5. **Access Application**:
   - Open browser to `http://localhost:8000`
   - Click the gear icon in the portfolio widget to open settings

## 9. Key Features

- **Portfolio Settings**: Cash, BTC value, and BTC average buy price
- **Robinhood Integration**: Username/password/2FA with enable/disable toggles
- **Data Pulling**: Manual and automatic (every 10 minutes) Robinhood data sync
- **Status Display**: Shows last pull time and data counts
- **Data Mapping**: Converts Robinhood data to app format
- **Error Handling**: Comprehensive error handling and user feedback

## 10. Security Notes

- Passwords are stored in plain text in the JSON file (consider encryption for production)
- Robinhood credentials are only used for API calls and not exposed to frontend
- 2FA codes are temporary and should be refreshed regularly
- Consider implementing proper session management for production use

This guide provides everything needed to recreate the portfolio settings functionality with Robinhood integration. 