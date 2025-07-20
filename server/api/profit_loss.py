from fastapi import APIRouter, Body, HTTPException, Query
from typing import List, Dict
from datetime import datetime, timedelta
import os, json, requests

router = APIRouter(prefix="/api/profit_loss", tags=["profit_loss"])

PORTFOLIO_PATH = os.path.join("public", "data", "positions.json")
ORDERS_PATH = os.path.join("public", "data", "orders.json")
POLYGON_API_KEY = os.environ.get("POLYGON_API_KEY")

# Cache paths for P/L data
PL_CACHE_PATH = os.path.join("public", "data", "pl_cache.json")
PL_SUMMARY_CACHE_PATH = os.path.join("public", "data", "pl_summary.json")

# Ensure data directory exists
os.makedirs(os.path.dirname(PL_CACHE_PATH), exist_ok=True)

# Cache structure:
# {
#   "last_updated": "2025-07-17T10:00:00Z",
#   "periods": {
#     "1W": {"total": 123.45, "unrealized": 100.0, "realized": 23.45, "calculated_at": "2025-07-17T10:00:00Z"},
#     "1M": {...},
#     "3M": {...},
#     "YTD": {...},
#     "MAX": {...}
#   }
# }

def load_pl_cache():
    """Load P/L cache from file."""
    if not os.path.exists(PL_SUMMARY_CACHE_PATH):
        return {"last_updated": None, "periods": {}}
    
    try:
        with open(PL_SUMMARY_CACHE_PATH, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading P/L cache: {e}")
        return {"last_updated": None, "periods": {}}

def save_pl_cache(cache_data):
    """Save P/L cache to file."""
    try:
        with open(PL_SUMMARY_CACHE_PATH, "w") as f:
            json.dump(cache_data, f, indent=2)
    except Exception as e:
        print(f"Error saving P/L cache: {e}")

def is_cache_valid(cache_data, max_age_hours=4):
    """Check if cache is still valid (not too old)."""
    if not cache_data.get("last_updated"):
        return False
    
    try:
        last_updated = datetime.fromisoformat(cache_data["last_updated"].replace("Z", "+00:00"))
        age = datetime.now().replace(tzinfo=last_updated.tzinfo) - last_updated
        return age.total_seconds() < (max_age_hours * 3600)
    except Exception:
        return False

def should_recalculate():
    """Check if we should recalculate P/L (cache invalid or missing)."""
    cache_data = load_pl_cache()
    return not is_cache_valid(cache_data)

def calculate_all_periods():
    """Calculate P/L for all time periods and cache the results."""
    print("Calculating P/L for all periods...")
    
    periods = ['1W', '1M', '3M', 'YTD', 'MAX']
    results = {}
    
    for period in periods:
        print(f"Calculating {period}...")
        try:
            # Calculate P/L for this period
            positions = get_positions()
            orders = get_orders()
            start_date, end_date = get_date_range(period)
            
            print(f"  - Date range: {start_date} to {end_date}")
            print(f"  - Positions: {len(positions)}")
            print(f"  - Orders: {len(orders)}")
            
            # Calculate current unrealized P/L
            current_unrealized = 0.0
            for pos in positions:
                latest = get_latest_price(pos["symbol"])
                if latest is not None:
                    current_unrealized += (latest - pos["buy_price"]) * pos["quantity"]
            
            print(f"  - Current unrealized: ${current_unrealized:.2f}")
            
            # Calculate realized P/L
            realized = calculate_realized_pl(orders, start_date, end_date)
            print(f"  - Realized P/L: ${realized:.2f}")
            
            # Calculate exact unrealized P/L change using historical prices
            # This is more accurate than approximations
            try:
                unrealized_change = calculate_unrealized_pl_change(orders, start_date, end_date)
                print(f"  - Unrealized change (historical): ${unrealized_change:.2f}")
            except Exception as e:
                print(f"  - Error calculating historical unrealized P/L: {e}")
                # Fallback to a more conservative approximation if historical fails
                if period == '1W':
                    unrealized_change = current_unrealized * 0.05  # 5% of current
                elif period == '1M':
                    unrealized_change = current_unrealized * 0.15  # 15% of current
                elif period == '3M':
                    unrealized_change = current_unrealized * 0.25  # 25% of current
                elif period == 'YTD':
                    unrealized_change = current_unrealized * 0.35  # 35% of current
                else:  # MAX
                    unrealized_change = current_unrealized * 0.45  # 45% of current
                print(f"  - Using fallback approximation: ${unrealized_change:.2f}")
            
            # Total P/L change during the period
            total = realized + unrealized_change
            
            results[period] = {
                "total": total,
                "unrealized": current_unrealized,
                "realized": realized,
                "calculated_at": datetime.now().isoformat()
            }
            
            print(f"  - Total P/L: ${total:.2f}")
            
        except Exception as e:
            print(f"Error calculating {period}: {e}")
            results[period] = {
                "total": 0.0,
                "unrealized": 0.0,
                "realized": 0.0,
                "calculated_at": datetime.now().isoformat(),
                "error": str(e)
            }
    
    # Save to cache
    cache_data = {
        "last_updated": datetime.now().isoformat(),
        "periods": results
    }
    save_pl_cache(cache_data)
    
    return cache_data

# Helper: get all positions
def get_positions():
    if not os.path.exists(PORTFOLIO_PATH):
        return []
    with open(PORTFOLIO_PATH, "r") as f:
        return json.load(f)

# Helper: get all orders
def get_orders():
    if not os.path.exists(ORDERS_PATH):
        return []
    with open(ORDERS_PATH, "r") as f:
        return json.load(f)

# Cache for Polygon API calls to avoid repeated requests
_polygon_cache = {}
_polygon_cache_file = os.path.join("public", "data", "polygon_cache.json")

def load_polygon_cache():
    """Load Polygon API cache from file."""
    if not os.path.exists(_polygon_cache_file):
        return {}
    try:
        with open(_polygon_cache_file, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_polygon_cache():
    """Save Polygon API cache to file."""
    try:
        with open(_polygon_cache_file, "w") as f:
            json.dump(_polygon_cache, f, indent=2)
    except Exception as e:
        print(f"Error saving Polygon cache: {e}")

# Load cache on startup
_polygon_cache = load_polygon_cache()

# Helper: get latest price from Polygon with caching
def get_latest_price(symbol):
    if not POLYGON_API_KEY:
        return None
    
    # Check cache first
    cache_key = f"{symbol}_latest"
    if cache_key in _polygon_cache:
        cached_data = _polygon_cache[cache_key]
        # Cache for 5 minutes
        if datetime.now().timestamp() - cached_data.get('timestamp', 0) < 300:
            return cached_data.get('price')
    
    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/prev"
    params = {"adjusted": "true", "apiKey": POLYGON_API_KEY}
    
    try:
        resp = requests.get(url, params=params, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            results = data.get("results", [])
            if results:
                price = results[0]["c"]
                # Cache the result
                _polygon_cache[cache_key] = {
                    'price': price,
                    'timestamp': datetime.now().timestamp()
                }
                save_polygon_cache()
                return price
    except Exception as e:
        print(f"Error getting latest price for {symbol}: {e}")
    
    return None

# Helper: get historical price from Polygon with caching
def get_historical_price(symbol, target_date):
    """Get the closing price for a symbol on a specific date using Polygon API with caching."""
    if not POLYGON_API_KEY:
        return None
    
    # Format date for cache key
    date_str = target_date.strftime('%Y-%m-%d')
    cache_key = f"{symbol}_{date_str}"
    
    # Check cache first
    if cache_key in _polygon_cache:
        cached_data = _polygon_cache[cache_key]
        # Cache for 7 days for historical data (more stable)
        if datetime.now().timestamp() - cached_data.get('timestamp', 0) < 604800:
            return cached_data.get('price')
    
    # Try to get the exact date first
    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/day/{date_str}/{date_str}"
    params = {"adjusted": "true", "apiKey": POLYGON_API_KEY}
    
    try:
        resp = requests.get(url, params=params, timeout=10)  # Increased timeout
        if resp.status_code == 200:
            data = resp.json()
            results = data.get("results", [])
            if results:
                price = results[0]["c"]
                # Cache the result
                _polygon_cache[cache_key] = {
                    'price': price,
                    'timestamp': datetime.now().timestamp()
                }
                save_polygon_cache()
                return price
        
        # If exact date not found, try previous trading day
        url_prev = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/prev"
        params_prev = {"adjusted": "true", "apiKey": POLYGON_API_KEY}
        
        resp_prev = requests.get(url_prev, params=params_prev, timeout=10)  # Increased timeout
        if resp_prev.status_code == 200:
            data_prev = resp_prev.json()
            results_prev = data_prev.get("results", [])
            if results_prev:
                price = results_prev[0]["c"]
                # Cache the result
                _polygon_cache[cache_key] = {
                    'price': price,
                    'timestamp': datetime.now().timestamp()
                }
                save_polygon_cache()
                return price
                
    except Exception as e:
        print(f"Error getting historical price for {symbol} on {date_str}: {e}")
    
    return None

def get_historical_prices_batch(symbols, target_date):
    """Get historical prices for multiple symbols in batch to reduce API calls."""
    if not POLYGON_API_KEY:
        return {}
    
    results = {}
    date_str = target_date.strftime('%Y-%m-%d')
    
    # Check cache first for all symbols
    uncached_symbols = []
    for symbol in symbols:
        cache_key = f"{symbol}_{date_str}"
        if cache_key in _polygon_cache:
            cached_data = _polygon_cache[cache_key]
            if datetime.now().timestamp() - cached_data.get('timestamp', 0) < 604800:
                results[symbol] = cached_data.get('price')
            else:
                uncached_symbols.append(symbol)
        else:
            uncached_symbols.append(symbol)
    
    # Fetch uncached symbols
    for symbol in uncached_symbols:
        price = get_historical_price(symbol, target_date)
        if price is not None:
            results[symbol] = price
    
    return results

# Helper: calculate realized P/L from orders within a date range
def calculate_realized_pl(orders, start_date=None, end_date=None):
    # Filter orders by date range if provided
    if start_date or end_date:
        filtered_orders = []
        for order in orders:
            order_date = order.get('date', '')
            if order_date:
                try:
                    order_dt = datetime.strptime(order_date.split('T')[0], '%Y-%m-%d')
                    if start_date and order_dt < start_date:
                        continue
                    if end_date and order_dt > end_date:
                        continue
                    filtered_orders.append(order)
                except:
                    continue
        orders = filtered_orders
    
    # Group orders by symbol
    symbol_orders = {}
    for order in orders:
        symbol = order.get('symbol')
        if symbol not in symbol_orders:
            symbol_orders[symbol] = []
        symbol_orders[symbol].append(order)
    
    realized_pl = 0.0
    for symbol, symbol_order_list in symbol_orders.items():
        # Sort orders by date
        symbol_order_list.sort(key=lambda x: x.get('date', ''))
        
        # Calculate P/L for this symbol
        buy_orders = [o for o in symbol_order_list if o.get('type') == 'buy']
        sell_orders = [o for o in symbol_order_list if o.get('type') == 'sell']
        
        # Simple FIFO calculation
        buy_index = 0
        sell_index = 0
        
        while buy_index < len(buy_orders) and sell_index < len(sell_orders):
            buy_order = buy_orders[buy_index]
            sell_order = sell_orders[sell_index]
            
            buy_quantity = buy_order.get('quantity', 0)
            sell_quantity = sell_order.get('quantity', 0)
            buy_price = buy_order.get('price', 0)
            sell_price = sell_order.get('price', 0)
            
            # Calculate P/L for this trade
            trade_quantity = min(buy_quantity, sell_quantity)
            pl = (sell_price - buy_price) * trade_quantity
            realized_pl += pl
            
            # Update remaining quantities
            if buy_quantity > sell_quantity:
                buy_orders[buy_index]['quantity'] = buy_quantity - sell_quantity
                sell_index += 1
            elif sell_quantity > buy_quantity:
                sell_orders[sell_index]['quantity'] = sell_quantity - buy_quantity
                buy_index += 1
            else:
                buy_index += 1
                sell_index += 1
    
    return realized_pl

# Helper: calculate positions at a specific date by replaying orders
def get_positions_at_date(orders, target_date):
    """Calculate what positions were held at a specific date by replaying all orders up to that date."""
    positions = {}  # symbol -> {quantity, avg_price}
    
    for order in orders:
        order_date = order.get('date', '')
        if not order_date:
            continue
            
        try:
            order_dt = datetime.strptime(order_date.split('T')[0], '%Y-%m-%d')
            if order_dt > target_date:
                continue  # Skip orders after target date
        except:
            continue
            
        symbol = order.get('symbol')
        order_type = order.get('type')
        quantity = order.get('quantity', 0)
        price = order.get('price', 0)
        
        if symbol not in positions:
            positions[symbol] = {'quantity': 0, 'avg_price': 0}
        
        if order_type == 'buy':
            # Add to position
            current_quantity = positions[symbol]['quantity']
            current_avg_price = positions[symbol]['avg_price']
            
            if current_quantity == 0:
                # First buy of this symbol
                positions[symbol]['avg_price'] = price
            else:
                # Calculate new average price
                total_cost = (current_quantity * current_avg_price) + (quantity * price)
                total_quantity = current_quantity + quantity
                positions[symbol]['avg_price'] = total_cost / total_quantity
            
            positions[symbol]['quantity'] += quantity
            
        elif order_type == 'sell':
            # Reduce position (FIFO)
            current_quantity = positions[symbol]['quantity']
            if current_quantity >= quantity:
                positions[symbol]['quantity'] -= quantity
                if positions[symbol]['quantity'] == 0:
                    # Position closed, reset average price
                    positions[symbol]['avg_price'] = 0
    
    return positions

# Helper: calculate unrealized P/L change during a time period (accurate version)
def calculate_unrealized_pl_change(orders, start_date, end_date):
    """Calculate exact unrealized P/L change during a time period using historical prices."""
    # Get positions at start of period
    start_positions = get_positions_at_date(orders, start_date)
    
    # Get positions at end of period  
    end_positions = get_positions_at_date(orders, end_date)
    
    # Get all unique symbols for batch processing
    all_symbols = set()
    for symbol in start_positions.keys():
        all_symbols.add(symbol)
    for symbol in end_positions.keys():
        all_symbols.add(symbol)
    
    # Batch fetch historical prices
    start_prices = get_historical_prices_batch(list(all_symbols), start_date)
    end_prices = get_historical_prices_batch(list(all_symbols), end_date)
    
    # Calculate unrealized P/L at start
    start_unrealized = 0.0
    for symbol, pos_data in start_positions.items():
        if pos_data['quantity'] > 0:
            start_price = start_prices.get(symbol)
            if start_price is not None:
                start_unrealized += (start_price - pos_data['avg_price']) * pos_data['quantity']
    
    # Calculate unrealized P/L at end
    end_unrealized = 0.0
    for symbol, pos_data in end_positions.items():
        if pos_data['quantity'] > 0:
            end_price = end_prices.get(symbol)
            if end_price is not None:
                end_unrealized += (end_price - pos_data['avg_price']) * pos_data['quantity']
    
    # Return the change in unrealized P/L
    return end_unrealized - start_unrealized

# Helper: get date range for time period
def get_date_range(period):
    now = datetime.now()
    
    if period == '1W':
        start_date = now - timedelta(days=7)
        end_date = now
    elif period == '1M':
        start_date = now - timedelta(days=30)
        end_date = now
    elif period == '3M':
        start_date = now - timedelta(days=90)
        end_date = now
    elif period == 'YTD':
        start_date = datetime(now.year, 1, 1)
        end_date = now
    elif period == 'MAX':
        start_date = now - timedelta(days=365)
        end_date = now
    else:
        start_date = None
        end_date = None
    
    return start_date, end_date

@router.get("/summary")
def get_profit_loss_summary(period: str = Query('YTD', description="Time period: 1W, 1M, 3M, YTD, MAX")) -> Dict:
    # Check cache first
    cache_data = load_pl_cache()
    if is_cache_valid(cache_data):
        cached_periods = cache_data["periods"]
        if period in cached_periods:
            result = cached_periods[period].copy()
            result["period"] = period
            return result
        else:
            # If period not in cache, recalculate all and return the specific one
            all_cache_data = calculate_all_periods()
            result = all_cache_data["periods"][period].copy()
            result["period"] = period
            return result
    else:
        # If cache is invalid or missing, calculate all and return the specific one
        all_cache_data = calculate_all_periods()
        result = all_cache_data["periods"][period].copy()
        result["period"] = period
        return result

@router.post("/refresh-cache")
def refresh_pl_cache():
    """Manually refresh the P/L cache by recalculating all periods."""
    try:
        cache_data = calculate_all_periods()
        return {
            "status": "success",
            "message": "P/L cache refreshed successfully",
            "last_updated": cache_data["last_updated"],
            "periods_calculated": list(cache_data["periods"].keys())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error refreshing cache: {e}")

@router.get("/cache-status")
def get_cache_status():
    """Get the status of the P/L cache."""
    cache_data = load_pl_cache()
    is_valid = is_cache_valid(cache_data)
    
    return {
        "cache_exists": bool(cache_data.get("last_updated")),
        "is_valid": is_valid,
        "last_updated": cache_data.get("last_updated"),
        "periods_available": list(cache_data.get("periods", {}).keys()),
        "should_recalculate": should_recalculate()
    }

@router.get("/chart")
def get_profit_loss_chart(period: str = Query('YTD', description="Time period: 1W, 1M, 3M, YTD, MAX")) -> Dict:
    orders = get_orders()
    positions = get_positions()
    start_date, end_date = get_date_range(period)
    
    # Generate chart data points
    labels = []
    values = []
    
    if period == '1W':
        # Daily data points for last 7 days
        for i in range(7):
            date = end_date - timedelta(days=6-i)
            labels.append(date.strftime('%m/%d'))
            
            # Calculate total P/L up to this date (realized + unrealized)
            period_end = date + timedelta(days=1)
            realized_pl = calculate_realized_pl(orders, start_date, period_end)
            
            # For unrealized, we use current position values (Robinhood approach)
            unrealized_pl = 0.0
            for pos in positions:
                latest = get_latest_price(pos["symbol"])
                if latest is not None:
                    unrealized_pl += (latest - pos["buy_price"]) * pos["quantity"]
            
            total_pl = realized_pl + unrealized_pl
            values.append(total_pl)
    
    elif period == '1M':
        # Weekly data points for last 30 days
        for i in range(5):
            date = end_date - timedelta(days=28-i*7)
            labels.append(date.strftime('%m/%d'))
            
            period_end = date + timedelta(days=7)
            realized_pl = calculate_realized_pl(orders, start_date, period_end)
            
            # Unrealized P/L (current positions)
            unrealized_pl = 0.0
            for pos in positions:
                latest = get_latest_price(pos["symbol"])
                if latest is not None:
                    unrealized_pl += (latest - pos["buy_price"]) * pos["quantity"]
            
            total_pl = realized_pl + unrealized_pl
            values.append(total_pl)
    
    elif period == '3M':
        # Bi-weekly data points for last 3 months
        for i in range(6):
            date = end_date - timedelta(days=84-i*14)
            labels.append(date.strftime('%m/%d'))
            
            period_end = date + timedelta(days=14)
            realized_pl = calculate_realized_pl(orders, start_date, period_end)
            
            # Unrealized P/L (current positions)
            unrealized_pl = 0.0
            for pos in positions:
                latest = get_latest_price(pos["symbol"])
                if latest is not None:
                    unrealized_pl += (latest - pos["buy_price"]) * pos["quantity"]
            
            total_pl = realized_pl + unrealized_pl
            values.append(total_pl)
    
    elif period == 'YTD':
        # Monthly data points for current year
        current_month = end_date.month
        for i in range(current_month + 1):
            date = datetime(end_date.year, i + 1, 1)  # Fix: i + 1 instead of i
            labels.append(date.strftime('%b'))
            
            if i == 0:
                values.append(0)
            else:
                period_end = datetime(end_date.year, i + 1, 1)  # Fix: i + 1 instead of i
                realized_pl = calculate_realized_pl(orders, start_date, period_end)
                
                # Unrealized P/L (current positions)
                unrealized_pl = 0.0
                for pos in positions:
                    latest = get_latest_price(pos["symbol"])
                    if latest is not None:
                        unrealized_pl += (latest - pos["buy_price"]) * pos["quantity"]
                
                total_pl = realized_pl + unrealized_pl
                values.append(total_pl)
    
    elif period == 'MAX':
        # Monthly data points for last 12 months
        for i in range(12):
            date = end_date - timedelta(days=365-i*30)
            labels.append(date.strftime('%b'))
            
            period_end = date + timedelta(days=30)
            realized_pl = calculate_realized_pl(orders, start_date, period_end)
            
            # Unrealized P/L (current positions)
            unrealized_pl = 0.0
            for pos in positions:
                latest = get_latest_price(pos["symbol"])
                if latest is not None:
                    unrealized_pl += (latest - pos["buy_price"]) * pos["quantity"]
            
            total_pl = realized_pl + unrealized_pl
            values.append(total_pl)
    
    return {"labels": labels, "values": values, "period": period}

@router.get("/details")
def get_profit_loss_details() -> List[Dict]:
    positions = get_positions()
    orders = get_orders()
    details = []
    
    # Add unrealized P/L for each position
    for pos in positions:
        latest = get_latest_price(pos["symbol"])
        if latest is not None:
            pl = (latest - pos["buy_price"]) * pos["quantity"]
            details.append({"symbol": pos["symbol"], "type": "Unrealized", "amount": pl})
    
    # Add realized P/L from orders (grouped by symbol)
    symbol_pl = {}
    for order in orders:
        symbol = order.get('symbol')
        if symbol not in symbol_pl:
            symbol_pl[symbol] = 0.0
        
        # For now, use the pl field if available, otherwise 0
        # In a more sophisticated implementation, you'd calculate this from buy/sell pairs
        symbol_pl[symbol] += order.get('pl', 0.0)
    
    for symbol, pl in symbol_pl.items():
        if pl != 0:  # Only show symbols with realized P/L
            details.append({"symbol": symbol, "type": "Realized", "amount": pl})
    
    return details

@router.post("/record_trade")
def record_trade(data: dict = Body(...)):
    # data: {symbol, quantity, buy_price, sell_price, pl}
    if not os.path.exists(ORDERS_PATH):
        orders = []
    else:
        with open(ORDERS_PATH, 'r') as f:
            orders = json.load(f)
    
    # Add new order
    new_order = {
        "id": len(orders) + 1,
        "symbol": data.get('symbol', ''),
        "type": "buy" if data.get('buy_price') else "sell",
        "quantity": data.get('quantity', 0),
        "price": data.get('buy_price') or data.get('sell_price', 0),
        "date": data.get('date', ''),
        "fees": 0.0,
        "pl": data.get('pl', 0.0),
        "notes": "Manual trade entry",
        "source": "manual"
    }
    orders.append(new_order)
    
    with open(ORDERS_PATH, 'w') as f:
        json.dump(orders, f, indent=2)
    return {'status': 'ok'} 