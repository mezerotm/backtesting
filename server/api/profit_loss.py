from fastapi import APIRouter, HTTPException, Query, Body, Request
from server.models import get_model_manager, ProfitLoss, ProfitLossCache, validate_profit_loss_data, validate_profit_loss_cache_data, transform_pocketbase_record, transform_to_pocketbase_data
from server.api.auth import get_current_user_id
from config.backend.logger import get_api_logger
from config.backend.settings import POLYGON_API_KEY
import os
import json
import requests
from datetime import datetime, timedelta
from typing import List, Dict
import pandas as pd

logger = get_api_logger("profit_loss")

router = APIRouter(prefix="/api/profit-loss", tags=["profit_loss"])

# Note: This API now uses PocketBase for data storage instead of
# file-based caching


async def calculate_all_periods(request: Request = None):
    """Calculate P/L for all time periods and cache the results."""
    periods = ['1W', '1M', '3M', 'YTD', 'MAX']
    results = {}

    # Load existing polygon cache to avoid API calls
    polygon_cache = load_polygon_close_cache()

    for period in periods:
        try:
            positions = await get_positions(request)
            orders = await get_orders(request)
            start_date, end_date = get_date_range(period)

            # Calculate current unrealized P/L using existing cache data
            current_unrealized = 0.0
            for pos in positions:
                symbol = pos["symbol"]
                if symbol in polygon_cache:
                    # Get the most recent price from cache
                    dates = sorted(polygon_cache[symbol].keys(), reverse=True)
                    if dates:
                        latest_price = polygon_cache[symbol][dates[0]]['price']
                        current_unrealized += (latest_price -
                                               pos["buy_price"]) * pos["quantity"]

            # Calculate realized P/L (simplified - just sum from orders)
            realized = 0.0
            for order in orders:
                if order.get('side') == 'sell':
                    # Calculate P/L for sell orders
                    buy_price = order.get('average_price', 0)
                    sell_price = order.get('price', 0)
                    quantity = order.get('quantity', 0)
                    pl = (sell_price - buy_price) * quantity
                    realized += pl

            # For now, use current unrealized as the total change
            # This is much faster than calculating historical changes
            total = realized + current_unrealized

            # Format decimals
            results[period] = {
                "total": round(total, 2),
                "unrealized": round(current_unrealized, 2),
                "realized": round(realized, 2),
                "calculated_at": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error calculating P/L for period {period}: {e}")
            results[period] = {
                "total": 0.0,
                "unrealized": 0.0,
                "realized": 0.0,
                "calculated_at": datetime.now().isoformat(),
                "error": str(e)
            }

    cache_data = {
        "last_updated": datetime.now().isoformat(),
        "periods": results
    }
    save_pl_cache(cache_data)
    return cache_data

# Helper: get all positions


async def get_positions(request: Request = None, user_id: str = None):
    """Get positions from PocketBase via ModelManager."""
    try:
        if user_id is None and request:
            user_id = await get_current_user_id(request)

        if not user_id:
            logger.warning("No user ID provided, returning empty positions")
            return []

        model_manager = get_model_manager()
        return model_manager.get_positions(user_id)
    except Exception as e:
        logger.error(f"Error getting positions: {e}")
        return []


async def get_orders(request: Request = None, user_id: str = None):
    """Get orders from PocketBase via ModelManager."""
    try:
        if user_id is None and request:
            user_id = await get_current_user_id(request)

        if not user_id:
            logger.warning("No user ID provided, returning empty orders")
            return []

        model_manager = get_model_manager()
        return model_manager.get_orders(user_id)
    except Exception as e:
        logger.error(f"Error getting orders: {e}")
        return []


# Cache for Polygon API calls to avoid repeated requests
_polygon_cache = {}
_polygon_cache_file = os.path.join("public", "data", "polygon_cache.json")

# P/L cache file
_pl_cache_file = os.path.join("public", "data", "pl_summary.json")


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
        logger.error(f"Error saving Polygon cache: {e}")


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
        logger.error(f"Error getting latest price for {symbol}: {e}")

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
    url = f"https://api.polygon.io/v2/aggs/ticker/{
        symbol}/range/1/day/{date_str}/{date_str}"
    params = {"adjusted": "true", "apiKey": POLYGON_API_KEY}

    try:
        resp = requests.get(
            url,
            params=params,
            timeout=10)  # Increased timeout
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

        resp_prev = requests.get(
            url_prev,
            params=params_prev,
            timeout=10)  # Increased timeout
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
        logger.error(f"Error getting historical price for {
                     symbol} on {date_str}: {e}")

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
                    order_dt = datetime.strptime(
                        order_date.split('T')[0], '%Y-%m-%d')
                    if start_date and order_dt < start_date:
                        continue
                    if end_date and order_dt > end_date:
                        continue
                    filtered_orders.append(order)
                except BaseException:
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
                buy_orders[buy_index]['quantity'] = buy_quantity - \
                    sell_quantity
                sell_index += 1
            elif sell_quantity > buy_quantity:
                sell_orders[sell_index]['quantity'] = sell_quantity - \
                    buy_quantity
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
        except BaseException:
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
                total_cost = (current_quantity *
                              current_avg_price) + (quantity * price)
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

# Helper: calculate unrealized P/L change during a time period (accurate
# version)


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
                start_unrealized += (start_price - \
                                     pos_data['avg_price']) * pos_data['quantity']

    # Calculate unrealized P/L at end
    end_unrealized = 0.0
    for symbol, pos_data in end_positions.items():
        if pos_data['quantity'] > 0:
            end_price = end_prices.get(symbol)
            if end_price is not None:
                end_unrealized += (end_price - \
                                   pos_data['avg_price']) * pos_data['quantity']

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

# --- Polygon Trading Days Helper (with file-based cache for closes) ---


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
        logger.debug(f"Could not fetch holidays from Polygon: {e}")
    # Build list of trading days
    trading_days = []
    today = datetime.now().date()
    days_checked = 0
    while len(trading_days) < n_days and days_checked < n_days * 3:
        d = today - timedelta(days=days_checked)
        if d.weekday() < 5 and d.strftime('%Y-%m-%d') not in holidays:
            trading_days.append(d.strftime('%Y-%m-%d'))
        days_checked += 1
    logger.debug(f"Using {len(trading_days)} trading days (most recent: {
                 trading_days[0]}, oldest: {trading_days[-1]})")
    return trading_days


POLYGON_CACHE_PATH = os.path.join("public", "data", "polygon_cache.json")


def load_polygon_close_cache():
    if not os.path.exists(POLYGON_CACHE_PATH):
        return {}
    try:
        with open(POLYGON_CACHE_PATH, "r") as f:
            cache = json.load(f)
            # Convert old format to new format if needed
            if cache and isinstance(
                next(
                    iter(
                        cache.values())),
                dict) and 'price' in next(
                iter(
                    cache.values())):
                logger.debug("Converting old cache format to new format")
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
    except Exception:
        return {}


def save_polygon_close_cache(cache):
    try:
        with open(POLYGON_CACHE_PATH, "w") as f:
            json.dump(cache, f, indent=2)
    except Exception:
        logger.error("Error saving polygon close cache")

# --- Trading Day-Aware Close Fetcher (with cache) ---


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
            logger.debug(f"{symbol} {date}: cache hit")
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
                        logger.debug(
                            f"{symbol} {date}: cache miss, fetched and saved")
            except Exception:
                continue

    if updated:
        save_polygon_close_cache(cache)

    s = pd.Series(closes)
    s.index = pd.to_datetime(s.index)
    s = s.sort_index()
    logger.debug(
        f"{symbol}: fetched {
            len(s)} closes for trading days, sample: {
            s.head() if not s.empty else 'empty'}")
    return s

# NOTE: These helpers can be used for:
# - Making P/L calculations trading-day aware
# - Generating accurate P/L/performance charts
# - Any feature that needs to align with real market/trading days


@router.get("/summary")
async def get_profit_loss_summary(request: Request, period: str = Query(
        'YTD', description="Time period: 1W, 1M, 3M, YTD, MAX")) -> Dict:
    """Get profit/loss summary from cached data in PocketBase."""
    try:
        user_id = await get_current_user_id(request)
        if not user_id:
            logger.warning("No user ID provided, returning empty summary")
            return {
                "total": 0.0,
                "unrealized": 0.0,
                "realized": 0.0,
                "calculated_at": datetime.now().isoformat(),
                "period": period
            }

        model_manager = get_model_manager()

        # Try to get cached data first
        cache_records = model_manager.get_profit_loss_cache_records(user_id)

        # Find the specific period in cache
        cached_data = None
        for record in cache_records:
            if record.get("period") == period:
                cached_data = record
                break

        if cached_data:
            # Use cached data
            result = {
                "total": round(cached_data.get("total", 0.0), 2),
                "unrealized": round(cached_data.get("unrealized", 0.0), 2),
                "realized": round(cached_data.get("realized", 0.0), 2),
                "calculated_at": cached_data.get("calculated_at", datetime.now().isoformat()),
                "period": period
            }
            logger.info(
                f"Retrieved cached profit/loss summary for user {user_id}, period {period}: {result}")
            return result
        else:
            # Fallback to calculating from individual records if cache not
            # available
            logger.warning(f"No cached data found for period {
                           period}, falling back to calculation")
            profit_loss_records = model_manager.get_profit_loss_records(
                user_id)

            # Calculate summary from records
            total_unrealized = 0.0
            total_realized = 0.0

            for record in profit_loss_records:
                amount = record.get("amount", 0.0)
                record_type = record.get("type", "")

                if record_type == "Unrealized":
                    total_unrealized += amount
                elif record_type == "Realized":
                    total_realized += amount

            total = total_unrealized + total_realized

            result = {
                "total": round(total, 2),
                "unrealized": round(total_unrealized, 2),
                "realized": round(total_realized, 2),
                "calculated_at": datetime.now().isoformat(),
                "period": period
            }

            logger.info(
                f"Calculated profit/loss summary for user {user_id}: {result}")
            return result

    except Exception as e:
        logger.error(f"Error getting profit/loss summary: {e}")
        return {
            "total": 0.0,
            "unrealized": 0.0,
            "realized": 0.0,
            "calculated_at": datetime.now().isoformat(),
            "period": period
        }


@router.post("/refresh-cache")
async def refresh_pl_cache(request: Request):
    """Manually refresh the P/L cache by recalculating all periods."""
    try:
        cache_data = await calculate_all_periods(request)
        return {
            "status": "success",
            "message": "P/L cache refreshed successfully",
            "last_updated": cache_data["last_updated"],
            "periods_calculated": list(cache_data["periods"].keys())
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error refreshing cache: {e}")


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
async def get_profit_loss_chart(
    request: Request,
    period: str = Query(
        'YTD',
        description="Time period: 1W, 1M, 3M, YTD, MAX")) -> Dict:
    """Get profit/loss chart data using cached values."""
    try:
        user_id = await get_current_user_id(request)
        if not user_id:
            logger.warning("No user ID provided, returning empty chart data")
            return {"labels": [], "values": [], "period": period}

        model_manager = get_model_manager()
        cache_records = model_manager.get_profit_loss_cache_records(user_id)

        # Find the specific period in cache
        cached_data = None
        for record in cache_records:
            if record.get("period") == period:
                cached_data = record
                break

        if cached_data:
            # Use cached data to create a simple chart
            total_pl = cached_data.get("total", 0.0)
            unrealized_pl = cached_data.get("unrealized", 0.0)
            realized_pl = cached_data.get("realized", 0.0)

            # Create a simple chart with current data
            # For now, just show the current total P/L
            labels = [datetime.now().strftime('%Y-%m-%d')]
            values = [round(total_pl, 2)]

            logger.info(f"Retrieved chart data for period {
                        period}: total={total_pl}")
            return {"labels": labels, "values": values, "period": period}
        else:
            # Fallback: create empty chart if no cached data
            logger.warning(f"No cached data found for period {period}")
            return {"labels": [], "values": [], "period": period}

    except Exception as e:
        logger.error(f"Error getting profit/loss chart data: {e}")
        return {"labels": [], "values": [], "period": period}


@router.get("/cache")
async def get_profit_loss_cache(request: Request) -> Dict:
    """Get all cached profit/loss data for all periods."""
    try:
        user_id = await get_current_user_id(request)
        if not user_id:
            logger.warning("No user ID provided, returning empty cache")
            return {
                "last_updated": datetime.now().isoformat(),
                "periods": {}
            }

        model_manager = get_model_manager()
        cache_records = model_manager.get_profit_loss_cache_records(user_id)

        # Convert to the expected format
        periods = {}
        last_updated = datetime.now().isoformat()

        for record in cache_records:
            period = record.get("period")
            if period:
                periods[period] = {
                    "total": round(
                        record.get(
                            "total", 0.0), 2), "unrealized": round(
                        record.get(
                            "unrealized", 0.0), 2), "realized": round(
                        record.get(
                            "realized", 0.0), 2), "calculated_at": record.get(
                                "calculated_at", datetime.now().isoformat())}
                # Use the most recent last_updated
                record_updated = record.get("last_updated")
                if record_updated and record_updated > last_updated:
                    last_updated = record_updated

        result = {
            "last_updated": last_updated,
            "periods": periods
        }

        logger.info(
            f"Retrieved profit/loss cache for user {user_id}: {len(periods)} periods")
        return result
    except Exception as e:
        logger.error(f"Error getting profit/loss cache: {e}")
        return {
            "last_updated": datetime.now().isoformat(),
            "periods": {}
        }


@router.get("/details")
async def get_profit_loss_details(request: Request) -> List[Dict]:
    """Get profit/loss details from cached data and current positions."""
    try:
        user_id = await get_current_user_id(request)
        if not user_id:
            logger.warning("No user ID provided, returning empty details")
            return []

        model_manager = get_model_manager()

        # Get current positions to show unrealized P/L by symbol
        positions = model_manager.get_positions(user_id)
        symbol_cache = model_manager.get_symbol_cache()

        details = []

        # Add unrealized P/L for each position
        for pos in positions:
            symbol = pos["symbol"]
            quantity = pos["quantity"]
            buy_price = pos["buy_price"]

            # Get latest price from symbol cache
            symbol_data = [
                r for r in symbol_cache if r.get("symbol") == symbol]
            if symbol_data:
                latest_price = symbol_data[0].get("price", buy_price)
                unrealized_pl = (latest_price - buy_price) * quantity

                details.append({
                    "symbol": symbol,
                    "type": "Unrealized",
                    "amount": round(unrealized_pl, 2)
                })

        # Add realized P/L from orders (simplified)
        orders = model_manager.get_orders(user_id)
        realized_by_symbol = {}

        for order in orders:
            if order.get('type') == 'sell':
                symbol = order.get('symbol', '')
                if symbol not in realized_by_symbol:
                    realized_by_symbol[symbol] = 0.0
                # Simple P/L calculation for sell orders
                buy_price = order.get('price', 0)
                sell_price = order.get('price', 0)
                quantity = order.get('quantity', 0)
                pl = (sell_price - buy_price) * quantity
                realized_by_symbol[symbol] += pl

        # Add realized P/L entries
        for symbol, realized_pl in realized_by_symbol.items():
            if realized_pl != 0:
                details.append({
                    "symbol": symbol,
                    "type": "Realized",
                    "amount": round(realized_pl, 2)
                })

        logger.info(
            f"Retrieved {
                len(details)} profit/loss details for user {user_id}")
        return details
    except Exception as e:
        logger.error(f"Error getting profit/loss details: {e}")
        return []


@router.post("/record_trade")
async def record_trade(request: Request, data: dict = Body(...)):
    # data: {symbol, quantity, buy_price, sell_price, pl}
    try:
        user_id = await get_current_user_id(request)
        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="User not authenticated")

        model_manager = get_model_manager()

        # Add new order
        new_order = {
            "symbol": data.get('symbol', ''),
            "side": "buy" if data.get('buy_price') else "sell",
            "quantity": data.get('quantity', 0),
            "price": data.get('buy_price') or data.get('sell_price', 0),
            "date": data.get('date', datetime.now().isoformat()),
            "fees": 0.0,
            "notes": "Manual trade entry",
            "source": "manual",
            "user": user_id
        }

        # Use ModelManager to add the order
        success = model_manager.add_order(new_order)
        if success:
            return {'status': 'ok', 'message': 'Trade recorded successfully'}
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to record trade")
    except Exception as e:
        logger.error(f"Error recording trade: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error recording trade: {e}")
