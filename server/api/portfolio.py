from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import json
import os
from pydantic import BaseModel
from fastapi.responses import JSONResponse
import requests
import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from utils.logger import get_widget_logger
from utils.config import POLYGON_API_KEY

# Initialize logger for portfolio widget
logger = get_widget_logger('portfolio')

# File paths
PORTFOLIO_PATH = os.path.join("public", "data", "positions.json")
PORTFOLIO_CASH_PATH = os.path.join("public", "data", "portfolio.json")

class Position(BaseModel):
    id: int
    symbol: str
    quantity: float
    buy_price: float
    notes: Optional[str] = None
    source: Optional[str] = None

def load_positions() -> List[dict]:
    if not os.path.exists(PORTFOLIO_PATH):
        return []
    with open(PORTFOLIO_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_positions(positions: List[dict]):
    with open(PORTFOLIO_PATH, "w", encoding="utf-8") as f:
        json.dump(positions, f, indent=2)

# --- Portfolio Cash, BTC, and BTC Avg Buy Price Logic ---
def load_portfolio_cash_btc() -> dict:
    if not os.path.exists(PORTFOLIO_CASH_PATH):
        return {
            "total_portfolio_cash": 0.0,
            "total_portfolio_btc": 0.0,
            "btc_avg_buy_price": 0.0,
            "robinhood_enabled": False,
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
        if "robinhood_username" not in data:
            data["robinhood_username"] = ""
        if "robinhood_password" not in data:
            data["robinhood_password"] = ""
        if "robinhood_mfa" not in data:
            data["robinhood_mfa"] = ""
        # Remove robinhood_display if present
        data.pop("robinhood_display", None)
        return data

def save_portfolio_cash_btc(data: dict):
    # Always write all fields, including new Robinhood settings
    out = {
        "total_portfolio_cash": float(data.get("total_portfolio_cash", 0.0)),
        "total_portfolio_btc": float(data.get("total_portfolio_btc", 0.0)),
        "btc_avg_buy_price": float(data.get("btc_avg_buy_price", 0.0)),
        "robinhood_enabled": bool(data.get("robinhood_enabled", False)),
        "robinhood_username": data.get("robinhood_username", ""),
        "robinhood_password": data.get("robinhood_password", ""),
        "robinhood_mfa": data.get("robinhood_mfa", "")
    }
    with open(PORTFOLIO_CASH_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

# Helper to get all unique symbols in the portfolio
def get_portfolio_symbols():
    positions = load_positions()
    return sorted(set(p["symbol"] for p in positions if p.get("symbol")))

def fetch_ticker_details(symbol):
    if not POLYGON_API_KEY:
        raise Exception("Polygon API key not set")
    url = f"https://api.polygon.io/v3/reference/tickers/{symbol}"
    params = {"apiKey": POLYGON_API_KEY}
    try:
        resp = requests.get(url, params=params, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            fundamentals = data.get("results", {}).get("fundamentals", {})
            beta = fundamentals.get("beta")
            return {"beta": beta}
    except Exception as e:
        return {"beta": None, "error": str(e)}
    return {"beta": None}

# Helper to fetch raw symbol data from Polygon.io
# Returns: {symbol: {"last_price": float, "previous_close": float, "timestamp": float, ..., "beta": float}}
def load_polygon_close_cache():
    if not os.path.exists(POLYGON_CACHE_PATH):
        return {}
    try:
        with open(POLYGON_CACHE_PATH, "r") as f:
            cache = json.load(f)
            # Check if this is the old format (flat structure with symbol_date keys)
            if cache and isinstance(next(iter(cache.values())), dict) and 'price' in next(iter(cache.values())):
                # This is already the new format, return as is
                return cache
            # Check if this is the very old format (symbol_date keys)
            elif cache and '_' in next(iter(cache.keys())):
                logger.debug("[DEBUG] Converting old cache format to new format")
                new_cache = {}
                for key, value in cache.items():
                    if '_' in key:
                        parts = key.split('_', 1)
                        if len(parts) == 2:
                            symbol, date = parts
                            if symbol not in new_cache:
                                new_cache[symbol] = {}
                            if isinstance(value, dict) and 'price' in value:
                                new_cache[symbol][date] = {
                                    'price': value['price'],
                                    'timestamp': value.get('timestamp', 0),
                                    'date': date
                                }
                            else:
                                new_cache[symbol][date] = {
                                    'price': value,
                                    'timestamp': 0,
                                    'date': date
                                }
                # Save the converted cache
                save_polygon_close_cache(new_cache)
                return new_cache
            return cache
    except Exception as e:
        logger.debug(f"[DEBUG] Error loading polygon cache: {e}")
        return {}

def save_polygon_close_cache(cache):
    try:
        with open(POLYGON_CACHE_PATH, "w") as f:
            json.dump(cache, f, indent=2)
    except Exception as e:
        logger.debug(f"[DEBUG] Error saving polygon close cache: {e}")

def get_current_symbol_data(symbol):
    """Get current symbol data from unified cache."""
    cache = load_polygon_close_cache()
    if symbol in cache and 'current' in cache[symbol]:
        data = cache[symbol]['current']
        logger.debug(f"[DEBUG] Retrieved current data for {symbol}: {data}")
        return data
    logger.debug(f"[DEBUG] No current data found for {symbol}")
    return None

def set_current_symbol_data(symbol, data):
    """Set current symbol data in unified cache."""
    cache = load_polygon_close_cache()
    if symbol not in cache:
        cache[symbol] = {}
    cache[symbol]['current'] = data
    save_polygon_close_cache(cache)
    logger.debug(f"[DEBUG] Saved current data for {symbol}: {data}")



# Updated functions to use unified cache
def load_symbol_data():
    """Load symbol data from unified cache (for backward compatibility)."""
    cache = load_polygon_close_cache()
    result = {}
    logger.debug(f"[DEBUG] load_symbol_data: cache keys: {list(cache.keys())}")
    for symbol, data in cache.items():
        if 'current' in data:
            result[symbol] = data['current']
            logger.debug(f"[DEBUG] load_symbol_data: found current data for {symbol}: {data['current']}")
        else:
            logger.debug(f"[DEBUG] load_symbol_data: no current data for {symbol}")
    logger.debug(f"[DEBUG] load_symbol_data: returning {len(result)} symbols")
    return result

def save_symbol_data(data):
    """Save symbol data to unified cache (for backward compatibility)."""
    cache = load_polygon_close_cache()
    for symbol, symbol_data in data.items():
        if symbol not in cache:
            cache[symbol] = {}
        cache[symbol]['current'] = symbol_data
    save_polygon_close_cache(cache)

def fetch_symbol_data(symbols):
    result = {}
    cache = load_polygon_close_cache()
    
    for symbol in symbols:
        # Check if we have recent current data in cache
        current_data = get_current_symbol_data(symbol)
        cache_age = 0
        if current_data and 'timestamp' in current_data:
            cache_age = time.time() - current_data['timestamp']
        
        # Use cache if less than 5 minutes old
        if current_data and cache_age < 300:
            result[symbol] = current_data
            logger.debug(f"[DEBUG] {symbol}: using cached current data (age: {cache_age:.1f}s)")
            continue
        
        # Fetch fresh data from Polygon
        # First get previous day's data
        prev_url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/prev"
        prev_params = {"adjusted": "true", "apiKey": POLYGON_API_KEY}
        
        # Then get current day's data
        current_url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/minute/{datetime.now().strftime('%Y-%m-%d')}/{datetime.now().strftime('%Y-%m-%d')}"
        current_params = {"adjusted": "true", "apiKey": POLYGON_API_KEY, "sort": "desc", "limit": 1}
        
        try:
            # Get previous close
            prev_resp = requests.get(prev_url, params=prev_params, timeout=5)
            prev_close = None
            if prev_resp.status_code == 200:
                prev_data = prev_resp.json()
                prev_results = prev_data.get("results", [])
                if prev_results:
                    prev_close = prev_results[0].get("c")
            
            # Get current price
            current_resp = requests.get(current_url, params=current_params, timeout=5)
            last_price = None
            if current_resp.status_code == 200:
                current_data = current_resp.json()
                current_results = current_data.get("results", [])
                if current_results:
                    last_price = current_results[0].get("c")
            
            # If no current price, try using previous close as current price
            if last_price is None and prev_close is not None:
                last_price = prev_close
                logger.debug(f"[DEBUG] {symbol}: using previous close as current price")
            
            # Fetch beta from ticker details
            ticker_details = fetch_ticker_details(symbol)
            beta = ticker_details.get("beta")
            
            symbol_data = {
                "last_price": last_price,
                "previous_close": prev_close,
                "timestamp": time.time(),
                "beta": beta
            }
            result[symbol] = symbol_data
            # Save to unified cache
            set_current_symbol_data(symbol, symbol_data)
            logger.debug(f"[DEBUG] {symbol}: fetched fresh current data - last_price={last_price}, prev_close={prev_close}, beta={beta}")
        except Exception as e:
            symbol_data = {"last_price": None, "previous_close": None, "timestamp": time.time(), "beta": None, "error": str(e)}
            result[symbol] = symbol_data
            set_current_symbol_data(symbol, symbol_data)
            logger.debug(f"[DEBUG] {symbol}: error fetching data - {e}")
    return result

def fetch_daily_closes(symbol, start_date, end_date):
    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/day/{start_date}/{end_date}"
    params = {"adjusted": "true", "apiKey": POLYGON_API_KEY, "sort": "asc", "limit": 5000}
    resp = requests.get(url, params=params, timeout=10)
    if resp.status_code != 200:
        logger.debug(f"[DEBUG] No data for {symbol}: HTTP {resp.status_code}")
        return None
    data = resp.json()
    bars = data.get("results", [])
    if not bars:
        logger.debug(f"[DEBUG] No bars for {symbol}")
        return None
    df = pd.DataFrame(bars)
    if 't' not in df or 'c' not in df:
        logger.debug(f"[DEBUG] Missing columns in bars for {symbol}")
        return None
    df['date'] = pd.to_datetime(df['t'], unit='ms')
    df.set_index('date', inplace=True)
    df.sort_index(inplace=True)
    logger.debug(f"[DEBUG] {symbol}: fetched {len(df)} closes, dates: {list(df.index.strftime('%Y-%m-%d'))}")
    return df['c']

def calculate_beta(stock_prices, market_prices):
    # Align on dates
    df = pd.DataFrame({'stock': stock_prices, 'market': market_prices}).dropna()
    if len(df) < 2:
        return None
    stock_returns = df['stock'].pct_change().dropna()
    market_returns = df['market'].pct_change().dropna()
    if len(stock_returns) < 2 or len(market_returns) < 2:
        return None
    # Align again after pct_change
    df2 = pd.DataFrame({'stock': stock_returns, 'market': market_returns}).dropna()
    if len(df2) < 2:
        return None
    cov = np.cov(df2['stock'], df2['market'])[0][1]
    var = np.var(df2['market'])
    if var == 0:
        return None
    beta = cov / var
    return float(beta)

# --- Polygon Trading Days Helper ---
POLYGON_CACHE_PATH = os.path.join("public", "data", "polygon_cache.json")

def get_polygon_trading_days(n_days=365):
    """
    Fetch the most recent n_days trading days (YYYY-MM-DD) from Polygon, skipping weekends/holidays.
    Returns a list of date strings, most recent first.
    """
    url = f"https://api.polygon.io/v1/marketstatus/upcoming"
    params = {"apiKey": POLYGON_API_KEY}
    holidays = set()
    try:
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            for h in data.get("marketHolidays", []):
                if h.get("date"):
                    holidays.add(h["date"])
    except Exception as e:
        logger.debug(f"[DEBUG] Could not fetch holidays from Polygon: {e}")
    # Build list of trading days
    trading_days = []
    today = datetime.now().date()
    days_checked = 0
    while len(trading_days) < n_days and days_checked < n_days * 3:
        d = today - timedelta(days=days_checked)
        if d.weekday() < 5 and d.strftime('%Y-%m-%d') not in holidays:
            trading_days.append(d.strftime('%Y-%m-%d'))
        days_checked += 1
    logger.debug(f"[DEBUG] Using {len(trading_days)} trading days (most recent: {trading_days[0]}, oldest: {trading_days[-1]})")
    return trading_days

# --- Beta Calculation with Trading Days ---
def fetch_closes_for_trading_days(symbol, trading_days):
    """
    Fetch closes for a symbol for the given list of trading days (YYYY-MM-DD).
    Uses file-based cache in public/data/polygon_cache.json.
    Returns a pandas Series indexed by date.
    """
    cache = load_polygon_close_cache()
    closes = {}
    updated = False
    
    # Initialize symbol in cache if not exists
    if symbol not in cache:
        cache[symbol] = {}
    
    for date in trading_days:
        if date in cache[symbol]:
            cached_entry = cache[symbol][date]
            closes[date] = cached_entry['price']
            logger.debug(f"[DEBUG] {symbol} {date}: cache hit")
        else:
            url = f"https://api.polygon.io/v1/open-close/{symbol}/{date}"
            params = {"adjusted": "true", "apiKey": POLYGON_API_KEY}
            try:
                resp = requests.get(url, params=params, timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    close = data.get("close")
                    if close is not None:
                        closes[date] = close
                        cache[symbol][date] = {
                            'price': close,
                            'timestamp': datetime.now().timestamp(),
                            'date': date
                        }
                        updated = True
                        logger.debug(f"[DEBUG] {symbol} {date}: cache miss, fetched and saved")
            except Exception as e:
                continue
    
    if updated:
        save_polygon_close_cache(cache)
    
    s = pd.Series(closes)
    s.index = pd.to_datetime(s.index)
    s = s.sort_index()
    logger.debug(f"[DEBUG] {symbol}: fetched {len(s)} closes for trading days, sample: {s.head() if not s.empty else 'empty'}")
    return s

def calculate_and_save_betas(symbols, market_symbol='SPY', lookback_days=365):
    logger.debug(f"[DEBUG] Starting beta calculation for {len(symbols)} symbols (plus NVDA)")
    test_symbols = set(symbols)
    test_symbols.add('NVDA')
    trading_days = get_polygon_trading_days(lookback_days)
    for symbol in test_symbols:
        stock_closes = fetch_closes_for_trading_days(symbol, trading_days)
        market_closes = fetch_closes_for_trading_days(market_symbol, trading_days)
        # Align on dates
        df = pd.DataFrame({'stock': stock_closes, 'market': market_closes}).dropna()
        if len(df) < 2:
            logger.debug(f"[DEBUG] {symbol}: Not enough aligned trading days for beta (have {len(df)})")
            beta = None
        else:
            beta = calculate_beta(df['stock'], df['market'])
            logger.debug(f"[DEBUG] {symbol}: beta={beta} (using {len(df)} aligned trading days)")
        # Save beta to unified cache
        current_data = get_current_symbol_data(symbol)
        if current_data is None:
            current_data = {"last_price": None, "previous_close": None, "timestamp": time.time(), "beta": None}
        current_data['beta'] = beta
        set_current_symbol_data(symbol, current_data)
    logger.debug(f"[DEBUG] Finished beta calculation for all symbols.")

# NOTE: The get_polygon_trading_days helper could also be used for:
# - P/L calculations (to ensure only trading days are considered)
# - Performance metrics (e.g., rolling returns, volatility)
# - Any feature that needs to align with real market/trading days

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])

@router.get("/", response_model=List[Position])
def get_positions():
    return load_positions()

@router.post("/", response_model=Position)
def add_position(pos: Position):
    positions = load_positions()
    if any(p["id"] == pos.id for p in positions):
        raise HTTPException(status_code=400, detail="ID already exists")
    positions.append(pos.dict())
    save_positions(positions)
    return pos

@router.put("/{pos_id}", response_model=Position)
def update_position(pos_id: int, pos: Position):
    positions = load_positions()
    for i, p in enumerate(positions):
        if p["id"] == pos_id:
            positions[i] = pos.dict()
            save_positions(positions)
            return pos
    raise HTTPException(status_code=404, detail="Position not found")

@router.delete("/{pos_id}")
def delete_position(pos_id: int):
    positions = load_positions()
    new_positions = [p for p in positions if p["id"] != pos_id]
    if len(new_positions) == len(positions):
        raise HTTPException(status_code=404, detail="Position not found")
    save_positions(new_positions)
    return JSONResponse(content={"detail": "Deleted"})

@router.get("/search-symbols")
def search_symbols(query: str = Query(..., min_length=1)):
    """Search for symbols using Polygon.io's ticker search API."""
    if not POLYGON_API_KEY:
        raise HTTPException(status_code=500, detail="Polygon API key not set")
    url = f"https://api.polygon.io/v3/reference/tickers"
    params = {
        "search": query,
        "active": "true",
        "apiKey": POLYGON_API_KEY,
        "limit": 10
    }
    resp = requests.get(url, params=params)
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Polygon API error: {resp.text}")
    data = resp.json()
    # Return a list of {symbol, name}
    results = [
        {"symbol": t["ticker"], "name": t.get("name", "")} for t in data.get("results", [])
    ]
    return results

@router.get("/latest-price/{symbol}")
def get_latest_price(symbol: str):
    """Get the latest price for a symbol from unified cache or Polygon.io."""
    # First try to get from cache
    current_data = get_current_symbol_data(symbol)
    if current_data and current_data.get('last_price') is not None:
        cache_age = time.time() - current_data.get('timestamp', 0)
        if cache_age < 300:  # 5 minutes
            return {"price": current_data['last_price'], "source": "cache"}
    
    # Fallback to direct API call
    if not POLYGON_API_KEY:
        raise HTTPException(status_code=500, detail="Polygon API key not set")
    
    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/prev"
    params = {"adjusted": "true", "apiKey": POLYGON_API_KEY}
    
    try:
        resp = requests.get(url, params=params, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            results = data.get("results", [])
            if results:
                price = results[0].get("c")
                # Update cache with fresh data
                symbol_data = {
                    "last_price": price,
                    "previous_close": price,
                    "timestamp": time.time(),
                    "beta": None
                }
                set_current_symbol_data(symbol, symbol_data)
                return {"price": price, "source": "api"}
        raise HTTPException(status_code=404, detail="No price data found")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Polygon API error: {str(e)}")

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
    if "robinhood_username" in data:
        current["robinhood_username"] = data["robinhood_username"] or ""
    if "robinhood_password" in data:
        current["robinhood_password"] = data["robinhood_password"] or ""
    if "robinhood_mfa" in data:
        current["robinhood_mfa"] = data["robinhood_mfa"] or ""
    # Remove robinhood_display if present
    current.pop("robinhood_display", None)
    save_portfolio_cash_btc(current)
    return {"status": "ok"}

@router.get("/cash")
def get_portfolio_cash():
    """
    Get the total portfolio cash, BTC (dollar value), and BTC avg buy price from portfolio.json.
    Returns: {"total_portfolio_cash": float, "total_portfolio_btc": float, "btc_avg_buy_price": float}
    """
    return load_portfolio_cash_btc()

@router.post("/cash")
def set_portfolio_cash(data: dict):
    """
    Set the total portfolio cash, BTC (dollar value), and/or BTC avg buy price in portfolio.json.
    Accepts any of: {"total_portfolio_cash": float, "total_portfolio_btc": float, "btc_avg_buy_price": float}
    """
    # Load current, update only provided fields
    current = load_portfolio_cash_btc()
    if "total_portfolio_cash" in data:
        current["total_portfolio_cash"] = float(data["total_portfolio_cash"])
    if "total_portfolio_btc" in data:
        current["total_portfolio_btc"] = float(data["total_portfolio_btc"])
    if "btc_avg_buy_price" in data:
        current["btc_avg_buy_price"] = float(data["btc_avg_buy_price"])
    save_portfolio_cash_btc(current)
    return {"status": "ok"}

@router.get("/btc")
def get_portfolio_btc():
    """Get the total portfolio BTC value from portfolio.json."""
    return {"total_portfolio_btc": load_portfolio_cash_btc().get("total_portfolio_btc", 0.0)}

@router.post("/btc")
def set_portfolio_btc(data: dict):
    """Set the total portfolio BTC value in portfolio.json. Accepts {"total_portfolio_btc": float}."""
    if "total_portfolio_btc" not in data:
        raise HTTPException(status_code=400, detail="Missing total_portfolio_btc field")
    current = load_portfolio_cash_btc()
    current["total_portfolio_btc"] = float(data["total_portfolio_btc"])
    save_portfolio_cash_btc(current)
    return {"status": "ok"}

@router.post("/refresh-symbols")
def refresh_symbol_data():
    symbols = get_portfolio_symbols()
    data = fetch_symbol_data(symbols)
    save_symbol_data(data)
    # Now calculate and save betas
    calculate_and_save_betas(symbols)
    return {"status": "ok", "symbols": list(data.keys())}

@router.get("/summary")
def get_portfolio_summary():
    positions = load_positions()
    symbol_data = load_symbol_data()
    summary = []
    for pos in positions:
        symbol = pos["symbol"]
        quantity = pos["quantity"]
        buy_price = pos["buy_price"]
        last_price = symbol_data.get(symbol, {}).get("last_price")
        prev_close = symbol_data.get(symbol, {}).get("previous_close")
        beta = symbol_data.get(symbol, {}).get("beta")
        # Calculated fields
        market_value = quantity * last_price if last_price is not None else None
        todays_return = None
        if last_price is not None and prev_close and prev_close != 0:
            todays_return = ((last_price - prev_close) / prev_close) * 100
        total_return = None
        if last_price is not None and buy_price and buy_price != 0:
            total_return = ((last_price - buy_price) / buy_price) * 100
        # Delta (for stocks/ETFs)
        delta = quantity
        # Debug logging for all columns
        logger.debug(f"[DEBUG] {symbol}: last_price={last_price}, prev_close={prev_close}, buy_price={buy_price}, market_value={market_value}, todays_return={todays_return}, total_return={total_return}, beta={beta}, delta={delta}")

        # Format decimals to 0.00 precision
        todays_return = round(todays_return, 2) if todays_return is not None else None
        total_return = round(total_return, 2) if total_return is not None else None
        beta = round(beta, 2) if beta is not None else None
        delta = round(delta, 2) if delta is not None else None

        summary.append({
            "id": pos["id"],
            "symbol": symbol,
            "quantity": pos["quantity"],
            "buy_price": round(pos["buy_price"], 2),
            "market_value": round(market_value, 2) if market_value is not None else None,
            "todays_return": todays_return,
            "total_return": total_return,
            "beta": beta,
            "delta": delta,
            "notes": pos.get("notes", ""),
            "source": pos.get("source", "manual")
        })
    return summary 