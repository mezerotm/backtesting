from fastapi import APIRouter, Request, HTTPException, Query
from server.models import get_model_manager
from server.models.data_models import (
    Position,
    PortfolioSettings,
    SymbolCache,
    PortfolioSummary,
    validate_position_data,
    validate_portfolio_data,
    validate_symbol_cache_data,
    transform_pocketbase_record,
    transform_to_pocketbase_data)
from server.api.auth import get_current_user_id
from utils.logger import get_api_logger
from typing import List, Dict, Any, Optional
import time
import requests
from utils.config import POLYGON_API_KEY
from fastapi.responses import JSONResponse

logger = get_api_logger("portfolio")

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


# =============================================================================
# PORTFOLIO CALCULATIONS
# =============================================================================

def calculate_position_amount(position: Position) -> float:
    """Calculate total amount invested in a position."""
    return round(position.quantity * position.buy_price, 2)


def calculate_position_market_value(
        position: Position,
        current_price: Optional[float]) -> Optional[float]:
    """Calculate current market value of a position."""
    if current_price is None:
        return None
    return round(position.quantity * current_price, 2)


def calculate_position_total_return(
        position: Position,
        current_price: Optional[float]) -> Optional[float]:
    """Calculate total return percentage for a position."""
    if current_price is None or position.buy_price == 0:
        return None
    return round(((current_price - position.buy_price) /
                 position.buy_price) * 100, 2)


def calculate_position_todays_return(
        position: Position,
        current_price: Optional[float],
        previous_close: Optional[float]) -> Optional[float]:
    """Calculate today's return percentage for a position."""
    if current_price is None or previous_close is None or previous_close == 0:
        return None
    return round(((current_price - previous_close) / previous_close) * 100, 2)


def calculate_position_delta(position: Position) -> float:
    """Calculate position delta (for stocks/ETFs, delta = quantity)."""
    return round(position.quantity, 2)


def calculate_portfolio_total_value(
        positions: List[Position],
        total_cash: float = 0.0,
        total_btc: float = 0.0) -> float:
    """Calculate total portfolio value including positions, cash, and BTC."""
    total_value = total_cash + total_btc

    for position in positions:
        position_value = position.market_value or calculate_position_amount(
            position)
        total_value += position_value or 0

    return round(total_value, 2)


def calculate_position_percentages(
        positions: List[Position],
        total_portfolio_value: float) -> None:
    """Calculate percentage of portfolio for each position."""
    if total_portfolio_value <= 0:
        return

    for position in positions:
        position_value = position.market_value or calculate_position_amount(
            position)
        position.percent_of_portfolio = round(
            (position_value / total_portfolio_value) * 100, 2)


def create_portfolio_summary(positions: List[Position],
                             total_cash: float = 0.0,
                             total_btc: float = 0.0,
                             btc_avg_price: float = 0.0) -> PortfolioSummary:
    """Create portfolio summary with calculated values."""
    # Calculate total portfolio value
    total_value = calculate_portfolio_total_value(
        positions, total_cash, total_btc)

    # Create summary
    summary = PortfolioSummary(
        positions=positions,
        total_cash=total_cash,
        total_btc=total_btc,
        btc_avg_price=btc_avg_price,
        total_value=total_value
    )

    # Calculate percentages
    calculate_position_percentages(positions, total_value)

    return summary


def enrich_positions_with_market_data(
        positions: List[Position], market_data: Dict[str, Dict[str, Any]]) -> None:
    """Enrich positions with market data and calculated values."""
    for position in positions:
        symbol = position.symbol
        market_info = market_data.get(symbol, {})

        # Get market prices
        current_price = market_info.get("last_price")
        previous_close = market_info.get("previous_close")

        # Calculate market value
        position.market_value = calculate_position_market_value(
            position, current_price)

        # Calculate returns
        position.total_return = calculate_position_total_return(
            position, current_price)
        position.todays_return = calculate_position_todays_return(
            position, current_price, previous_close)

        # Set other market data
        position.beta = market_info.get("beta")
        position.delta = calculate_position_delta(position)


def get_position_summary_dict(position: Position) -> Dict[str, Any]:
    """Convert position to dictionary for API response."""
    return {
        "id": position.id,
        "symbol": position.symbol,
        "quantity": position.quantity,
        "buy_price": position.buy_price,
        "market_value": position.market_value,
        "todays_return": position.todays_return,
        "total_return": position.total_return,
        "beta": position.beta,
        "delta": position.delta,
        "notes": position.notes or "",
        "source": position.source or "manual",
        "percent_of_portfolio": position.percent_of_portfolio
    }


def get_portfolio_summary_dict(summary: PortfolioSummary) -> Dict[str, Any]:
    """Convert portfolio summary to dictionary for API response."""
    return {
        "positions": [
            get_position_summary_dict(pos) for pos in summary.positions],
        "total_value": summary.total_value,
        "total_cash": summary.total_cash,
        "total_btc": summary.total_btc,
        "btc_avg_price": summary.btc_avg_price}


# Position model is now imported from data_models


async def get_portfolio_symbols(request: Request):
    """Get all unique symbols in the portfolio from PocketBase."""
    try:
        model_manager = get_model_manager()
        user_id = await get_current_user_id(request)
        if not user_id:
            logger.warning(
                "No authenticated user found, returning empty symbols list")
            return []
        positions = model_manager.get_positions(user_id)
        symbols = set()
        for position in positions:
            symbol = position.get("symbol")
            if symbol:
                symbols.add(symbol)
        return sorted(list(symbols))
    except Exception as e:
        logger.error(f"Error getting portfolio symbols: {e}")
        return []


def get_current_symbol_data(symbol):
    """Get current symbol data from PocketBase symbol cache."""
    try:
        model_manager = get_model_manager()
        cached_records = model_manager.get_symbol_cache()
        symbol_records = [
            r for r in cached_records if r.get("symbol") == symbol]
        if not symbol_records:
            logger.debug(f"No cached data found for {symbol}")
            return None

        # Get the most recent record by date (today's date first, then fallback
        # to any)
        today = time.strftime('%Y-%m-%d')
        today_records = [r for r in symbol_records if r.get("date") == today]

        if today_records:
            most_recent = today_records[0]  # Take the first one for today
        else:
            # Fallback to any record for this symbol
            most_recent = symbol_records[0] if symbol_records else None

        if not most_recent:
            logger.debug(f"No valid cached data found for {symbol}")
            return None

        # Transform to SymbolCache model for validation
        try:
            symbol_cache = transform_pocketbase_record(
                most_recent, SymbolCache)
            current_data = {
                "last_price": symbol_cache.price,
                "previous_close": symbol_cache.price,  # For now, use same as price
                "timestamp": time.time(),
                "beta": symbol_cache.beta
            }
            logger.debug(f"Retrieved current data for {
                         symbol}: {current_data}")
            return current_data
        except Exception as validation_error:
            logger.error(f"Validation error for symbol {
                         symbol}: {validation_error}")
            return None

    except Exception as e:
        logger.error(f"Error getting current symbol data for {symbol}: {e}")
        return None


def get_crypto_historical_price(symbol: str, date: str) -> Optional[float]:
    """Get historical crypto price from CoinGecko for a specific date."""
    try:
        # CoinGecko historical data endpoint
        url = f"https://api.coingecko.com/api/v3/coins/{
            symbol.lower()}/history"
        params = {
            'date': date,
            'localization': 'false'
        }

        logger.info(f"Fetching historical price for {symbol} on {date}")
        response = requests.get(url, params=params, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if 'market_data' in data and 'current_price' in data['market_data']:
                price = data['market_data']['current_price']['usd']
                logger.info(f"Historical price for {
                            symbol} on {date}: ${price}")
                return float(price)
            else:
                logger.warning(
                    f"No price data in CoinGecko response for {symbol} on {date}")
                return None
        else:
            logger.warning(
                f"CoinGecko API error for {symbol} on {date}: {
                    response.status_code}")
            return None

    except Exception as e:
        logger.error(f"Error getting historical price for {
                     symbol} on {date}: {e}")
        return None


def set_current_symbol_data(symbol, data):
    """Set current symbol data in PocketBase symbol cache with daily records."""
    try:
        model_manager = get_model_manager()
        today = time.strftime('%Y-%m-%d')

        # Check if we already have a record for today
        cached_records = model_manager.get_symbol_cache()
        today_records = [r for r in cached_records if r.get(
            "symbol") == symbol and r.get("date") == today]

        # Create SymbolCache model for validation
        cache_data = {
            "symbol": symbol,
            "price": data.get("last_price"),
            "date": today,
            "beta": data.get("beta"),
            "delta": data.get("delta", None)
        }

        # Validate the data
        try:
            symbol_cache = validate_symbol_cache_data(cache_data)
            cache_data = transform_to_pocketbase_data(symbol_cache)
        except Exception as validation_error:
            logger.error(f"Validation error for symbol {
                         symbol}: {validation_error}")
            return False

        if today_records:
            # Update existing record for today
            record_id = today_records[0]["id"]
            result = model_manager.pb_client.update_record(
                "symbol_cache", record_id, cache_data) is not None
            logger.debug(f"Updated existing cache data for {
                         symbol} on {today}: {result}")
        else:
            # Create new record for today
            result = model_manager.pb_client.create_record(
                "symbol_cache", cache_data) is not None
            logger.debug(f"Created new cache data for {
                         symbol} on {today}: {result}")

        return result
    except Exception as e:
        logger.error(f"Error setting current symbol data for {symbol}: {e}")
        return False


def fetch_symbol_data(symbols):
    """Fetch symbol data from Polygon.io and cache in PocketBase."""
    result = {}

    # Check if Polygon API key is available
    if not POLYGON_API_KEY:
        logger.warning("POLYGON_API_KEY not set, skipping market data fetch")
        return result

    for symbol in symbols:
        try:
            # Check if this is a crypto symbol (common crypto symbols)
            crypto_symbols = {
                'BTC',
                'ETH',
                'ADA',
                'DOGE',
                'XRP',
                'LTC',
                'BCH',
                'ETC',
                'LINK',
                'UNI',
                'AAVE',
                'COMP',
                'MKR',
                'YFI',
                'SUSHI',
                'CRV',
                'BAL',
                'REN',
                'ZRX',
                'BAT',
                'ZEC',
                'DASH',
                'XLM',
                'TRX',
                'VET',
                'ALGO',
                'ATOM',
                'DOT',
                'SOL',
                'AVAX',
                'MATIC',
                'FTM',
                'NEAR',
                'AR',
                'ICP',
                'FIL',
                'THETA',
                'XTZ',
                'EOS',
                'TRX',
                'XMR',
                'NEO',
                'QTUM',
                'IOTA',
                'NANO',
                'BTT',
                'WIN',
                'BTTOLD',
                'WINOLD'}

            if symbol in crypto_symbols:
                # For crypto, try to get data from CoinGecko API (free and
                # reliable)
                try:
                    # Map common crypto symbols to CoinGecko IDs
                    coin_id_map = {
                        'BTC': 'bitcoin',
                        'ETH': 'ethereum',
                        'SOL': 'solana',
                        'XRP': 'ripple',
                        'DOGE': 'dogecoin',
                        'ADA': 'cardano',
                        'LTC': 'litecoin',
                        'BCH': 'bitcoin-cash',
                        'ETC': 'ethereum-classic',
                        'LINK': 'chainlink',
                        'UNI': 'uniswap',
                        'AAVE': 'aave',
                        'COMP': 'compound-governance-token',
                        'MKR': 'maker',
                        'YFI': 'yearn-finance',
                        'SUSHI': 'sushi',
                        'CRV': 'curve-dao-token',
                        'BAL': 'balancer',
                        'REN': 'republic-protocol',
                        'ZRX': '0x',
                        'BAT': 'basic-attention-token',
                        'ZEC': 'zcash',
                        'DASH': 'dash',
                        'XLM': 'stellar',
                        'TRX': 'tron',
                        'VET': 'vechain',
                        'ALGO': 'algorand',
                        'ATOM': 'cosmos',
                        'AVAX': 'avalanche-2',
                        'MATIC': 'matic-network',
                        'FTM': 'fantom',
                        'NEAR': 'near',
                        'AR': 'arweave',
                        'ICP': 'internet-computer',
                        'FIL': 'filecoin',
                        'THETA': 'theta-token',
                        'XTZ': 'tezos',
                        'EOS': 'eos',
                        'XMR': 'monero',
                        'NEO': 'neo',
                        'QTUM': 'qtum',
                        'IOTA': 'iota',
                        'NANO': 'nano',
                        'TRUMP': 'trump'  # Note: This might not exist on CoinGecko
                    }
                    
                    coin_id = coin_id_map.get(symbol, symbol.lower())
                    crypto_url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
                    logger.info(f"Fetching crypto price for {symbol} using CoinGecko ID: {coin_id}")
                    
                    # Add small delay to avoid rate limiting
                    time.sleep(0.1)
                    
                    crypto_resp = requests.get(crypto_url, timeout=10)
                    if crypto_resp.status_code == 200:
                        crypto_data = crypto_resp.json()
                        if coin_id in crypto_data and 'usd' in crypto_data[coin_id]:
                            last_price = float(crypto_data[coin_id]['usd'])
                            prev_close = last_price  # For crypto, use current price as previous close
                            logger.info(f"{symbol} (crypto): got price: ${last_price}")
                        else:
                            last_price = None
                            prev_close = None
                            logger.warning(f"{symbol} (crypto): no price data available for {coin_id}")
                    else:
                        last_price = None
                        prev_close = None
                        logger.warning(f"{symbol} (crypto): API request failed with status {crypto_resp.status_code}")
                except Exception as crypto_error:
                    logger.warning(f"{symbol} (crypto): failed to get crypto price: {crypto_error}")
                    last_price = None
                    prev_close = None
            else:
                # For stocks, use Polygon.io
                prev_url = f"https://api.polygon.io/v2/aggs/ticker/{
                    symbol}/prev"
                prev_params = {"adjusted": "true", "apiKey": POLYGON_API_KEY}
                prev_resp = requests.get(
                    prev_url, params=prev_params, timeout=10)
                prev_close = None
                last_price = None

                if prev_resp.status_code == 200:
                    prev_data = prev_resp.json()
                    prev_results = prev_data.get("results", [])
                    if prev_results:
                        prev_close = prev_results[0].get("c")
                        last_price = prev_close
                        logger.debug(
                            f"{symbol} (stock): got previous close: {prev_close}")

            # Return data in the format expected by the new schema
            symbol_data = {
                "last_price": last_price,
                "previous_close": prev_close,
                "timestamp": time.time(),
                "beta": None
            }
            result[symbol] = symbol_data
            logger.debug(f"{symbol}: market data prepared")
        except Exception as e:
            symbol_data = {
                "last_price": None,
                "previous_close": None,
                "timestamp": time.time(),
                "beta": None
            }
            result[symbol] = symbol_data
            logger.error(f"{symbol}: market data fetch failed - {e}")
    return result


def save_symbol_data(data):
    """Save symbol data to PocketBase symbol cache."""
    try:
        for symbol, symbol_data in data.items():
            set_current_symbol_data(symbol, symbol_data)
        logger.info(f"Saved symbol data for {len(data)} symbols to PocketBase")
    except Exception as e:
        logger.error(f"Error saving symbol data: {e}")


def calculate_and_save_betas(symbols):
    """Calculate and save betas for symbols to PocketBase."""
    logger.debug(f"Starting beta calculation for {len(symbols)} symbols")
    # Placeholder for beta calculation
    for symbol in symbols:
        try:
            current_data = get_current_symbol_data(symbol)
            if current_data is None:
                current_data = {
                    "last_price": None,
                    "previous_close": None,
                    "timestamp": time.time(),
                    "beta": None
                }
            # Beta calculation would go here
            current_data['beta'] = None
            set_current_symbol_data(symbol, current_data)
        except Exception as e:
            logger.error(f"Error calculating beta for {symbol}: {e}")
    logger.debug("Finished beta calculation for all symbols.")


@router.get("/", response_model=List[Position])
async def get_positions(request: Request):
    """Get all positions from PocketBase."""
    try:
        logger.info("Getting positions from PocketBase...")
        model_manager = get_model_manager()

        # Get user ID from authenticated session
        user_id = await get_current_user_id(request)
        if not user_id:
            logger.warning(
                "No authenticated user found, returning empty positions")
            return []

        positions = model_manager.get_positions(user_id)
        logger.info(
            f"Retrieved {
                len(positions)} positions from PocketBase for user {user_id}")
        return positions
    except Exception as e:
        logger.error(f"Error getting positions: {e}")
        raise HTTPException(status_code=500, detail="Failed to get positions")


@router.post("/", response_model=Position)
async def add_position(pos: Position, request: Request):
    """Add a new position to PocketBase."""
    try:
        logger.info(f"Adding position for {pos.symbol}...")
        model_manager = get_model_manager()

        # Get user ID from authenticated session
        user_id = await get_current_user_id(request)
        if not user_id:
            logger.warning(
                "Portfolio API called without authentication - expected for fresh starts")
            raise HTTPException(
                status_code=401,
                detail="User not authenticated")

        position_data = pos.dict()
        if position_data.get("id"):
            del position_data["id"]  # Let PocketBase assign the ID

        if model_manager.add_position(position_data):
            # Get the newly created position
            positions = model_manager.get_positions(user_id)
            new_position = None
            for p in positions:
                if (p.get("symbol") == pos.symbol and p.get("quantity") ==
                        pos.quantity and p.get("buy_price") == pos.buy_price):
                    new_position = p
                    break

            if new_position:
                logger.info(f"Successfully added position for {pos.symbol}")
                return new_position
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Position added but could not retrieve it")
        else:
            raise HTTPException(
                status_code=400,
                detail="Failed to add position")
    except Exception as e:
        logger.error(f"Error adding position: {e}")
        raise HTTPException(status_code=500, detail="Failed to add position")


@router.put("/{pos_id}", response_model=Position)
async def update_position(pos_id: str, pos: Position, request: Request):
    """Update an existing position in PocketBase."""
    try:
        logger.info(f"Updating position {pos_id}...")
        model_manager = get_model_manager()

        # Get user ID from authenticated session
        user_id = await get_current_user_id(request)
        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="User not authenticated")

        position_data = pos.dict()
        if position_data.get("id"):
            del position_data["id"]  # Keep the existing ID

        if model_manager.update_position(pos_id, position_data):
            # Get the updated position
            positions = model_manager.get_positions(user_id)
            updated_position = None
            for p in positions:
                if p.get("id") == pos_id:
                    updated_position = p
                    break

            if updated_position:
                logger.info(f"Successfully updated position {pos_id}")
                return updated_position
            else:
                raise HTTPException(
                    status_code=404,
                    detail="Position not found after update")
        else:
            raise HTTPException(status_code=404, detail="Position not found")
    except Exception as e:
        logger.error(f"Error updating position {pos_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to update position")


@router.delete("/{pos_id}")
async def delete_position(pos_id: str, request: Request):
    """Delete a position from PocketBase."""
    try:
        logger.info(f"Deleting position {pos_id}...")
        model_manager = get_model_manager()

        # Get user ID from authenticated session
        user_id = await get_current_user_id(request)
        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="User not authenticated")

        if model_manager.delete_position(pos_id):
            logger.info(f"Successfully deleted position {pos_id}")
            return JSONResponse(content={"detail": "Deleted"})
        else:
            raise HTTPException(status_code=404, detail="Position not found")
    except Exception as e:
        logger.error(f"Error deleting position {pos_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to delete position")


@router.get("/search-symbols")
def search_symbols(query: str = Query(..., min_length=1)):
    """Search for symbols using Polygon.io's ticker search API."""
    if not POLYGON_API_KEY:
        raise HTTPException(status_code=500, detail="Polygon API key not set")
    url = "https://api.polygon.io/v3/reference/tickers"
    params = {
        "search": query,
        "active": "true",
        "apiKey": POLYGON_API_KEY,
        "limit": 10
    }
    resp = requests.get(url, params=params)
    if resp.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Polygon API error: {resp.text}")
    data = resp.json()
    # Return a list of {symbol, name}
    results = [{"symbol": t["ticker"], "name": t.get(
        "name", "")} for t in data.get("results", [])]
    return results


@router.get("/latest-price/{symbol}")
def get_latest_price(symbol: str):
    """Get the latest price for a symbol from PocketBase cache or Polygon.io."""
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
        raise HTTPException(
            status_code=502,
            detail=f"Polygon API error: {str(e)}")


@router.get("/settings")
async def get_portfolio_settings(request: Request):
    """Get portfolio settings from PocketBase."""
    try:
        logger.info("Getting portfolio settings from PocketBase...")
        model_manager = get_model_manager()

        # Get user ID from authenticated session
        user_id = await get_current_user_id(request)
        if not user_id:
            logger.warning(
                "No authenticated user found, returning empty settings")
            return {}

        settings = model_manager.get_portfolio_data(user_id)
        logger.info("Retrieved portfolio settings from PocketBase")
        return settings
    except Exception as e:
        logger.error(f"Error getting portfolio settings: {e}")
        raise HTTPException(status_code=500,
                            detail="Failed to get portfolio settings")


@router.post("/settings")
async def set_portfolio_settings(data: dict, request: Request):
    """Set portfolio settings in PocketBase."""
    try:
        logger.info("Updating portfolio settings in PocketBase...")
        logger.info(f"Received data: {data}")
        model_manager = get_model_manager()

        # Get user ID from authenticated session
        user_id = await get_current_user_id(request)
        logger.info(f"User ID: {user_id}")
        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="User not authenticated")

        # Get current settings and update with new data
        current_settings = model_manager.get_portfolio_data(user_id)
        logger.info(f"Current settings: {current_settings}")

        # Update with provided data
        for key, value in data.items():
            if key in [
                "total_portfolio_cash",
                "total_portfolio_btc",
                    "btc_avg_buy_price"]:
                try:
                    current_settings[key] = float(value or 0)
                    logger.info(f"Updated {key} to {current_settings[key]}")
                except (ValueError, TypeError):
                    current_settings[key] = 0.0
                    logger.warning(
                        f"Invalid value for {key}: {value}, set to 0.0")
            elif key == "robinhood_enabled":
                current_settings[key] = bool(value)
                logger.info(f"Updated {key} to {current_settings[key]}")
            elif key in ["robinhood_username", "robinhood_password", "robinhood_mfa"]:
                current_settings[key] = value or ""
                logger.info(f"Updated {key} to '{current_settings[key]}'")

        logger.info(f"Final settings to save: {current_settings}")

        if model_manager.update_portfolio_data(user_id, current_settings):
            logger.info(
                "Successfully updated portfolio settings in PocketBase")
            return {"status": "ok"}
        else:
            logger.error("Model manager update_portfolio_data returned False")
            raise HTTPException(status_code=400,
                                detail="Failed to update portfolio settings")
    except Exception as e:
        logger.error(f"Error updating portfolio settings: {e}")
        raise HTTPException(status_code=500,
                            detail="Failed to update portfolio settings")


@router.get("/cash")
async def get_portfolio_cash(request: Request):
    """Get portfolio cash amount from PocketBase."""
    try:
        logger.info("Getting portfolio cash from PocketBase...")
        model_manager = get_model_manager()

        # Get user ID from authenticated session
        user_id = await get_current_user_id(request)
        if not user_id:
            logger.warning("No authenticated user found, returning 0 cash")
            return {"total_portfolio_cash": 0.0}

        portfolio_data = model_manager.get_portfolio_data(user_id)
        cash = portfolio_data.get("total_portfolio_cash", 0.0)
        logger.info(f"Retrieved portfolio cash from PocketBase: ${cash}")
        return {"total_portfolio_cash": cash}
    except Exception as e:
        logger.error(f"Error getting portfolio cash: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get portfolio cash")


@router.post("/cash")
async def set_portfolio_cash(data: dict, request: Request):
    """Set portfolio cash amount in PocketBase."""
    try:
        logger.info("Setting portfolio cash in PocketBase...")
        model_manager = get_model_manager()

        # Get user ID from authenticated session
        user_id = await get_current_user_id(request)
        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="User not authenticated")

        current_data = model_manager.get_portfolio_data(user_id)
        if "total_portfolio_cash" in data:
            current_data["total_portfolio_cash"] = float(
                data["total_portfolio_cash"])

        if model_manager.update_portfolio_data(user_id, current_data):
            logger.info(
                f"Set portfolio cash in PocketBase to: ${
                    current_data['total_portfolio_cash']}")
            return {"status": "ok"}
        else:
            raise HTTPException(
                status_code=400,
                detail="Failed to set portfolio cash")
    except Exception as e:
        logger.error(f"Error setting portfolio cash: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to set portfolio cash")


@router.get("/btc")
async def get_portfolio_btc(request: Request):
    """Get portfolio BTC value from PocketBase."""
    try:
        logger.info("Getting portfolio BTC from PocketBase...")
        model_manager = get_model_manager()

        # Get user ID from authenticated session
        user_id = await get_current_user_id(request)
        if not user_id:
            logger.warning("No authenticated user found, returning 0 BTC")
            return {"total_portfolio_btc": 0.0}

        portfolio_data = model_manager.get_portfolio_data(user_id)
        btc = portfolio_data.get("total_portfolio_btc", 0.0)
        logger.info(f"Retrieved portfolio BTC from PocketBase: {btc}")
        return {"total_portfolio_btc": btc}
    except Exception as e:
        logger.error(f"Error getting portfolio BTC: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get portfolio BTC")


@router.post("/btc")
async def set_portfolio_btc(data: dict, request: Request):
    """Set portfolio BTC value in PocketBase."""
    try:
        logger.info("Setting portfolio BTC in PocketBase...")
        if "total_portfolio_btc" not in data:
            raise HTTPException(status_code=400,
                                detail="Missing total_portfolio_btc field")

        model_manager = get_model_manager()

        # Get user ID from authenticated session
        user_id = await get_current_user_id(request)
        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="User not authenticated")

        current_data = model_manager.get_portfolio_data(user_id)
        current_data["total_portfolio_btc"] = float(
            data["total_portfolio_btc"])

        if model_manager.update_portfolio_data(user_id, current_data):
            logger.info(
                f"Set portfolio BTC in PocketBase to: {
                    current_data['total_portfolio_btc']}")
            return {"status": "ok"}
        else:
            raise HTTPException(
                status_code=400,
                detail="Failed to set portfolio BTC")
    except Exception as e:
        logger.error(f"Error setting portfolio BTC: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to set portfolio BTC")


@router.post("/refresh-symbols")
async def refresh_symbol_data(request: Request):
    """Refresh symbol data from Polygon.io and save to PocketBase."""
    try:
        logger.info("Refreshing symbol data...")
        symbols = await get_portfolio_symbols(request)
        data = fetch_symbol_data(symbols)
        save_symbol_data(data)
        # Now calculate and save betas
        calculate_and_save_betas(symbols)
        logger.info(f"Refreshed symbol data for {len(data)} symbols")
        return {"status": "ok", "symbols": list(data.keys())}
    except Exception as e:
        logger.error(f"Error refreshing symbol data: {e}")
        raise HTTPException(status_code=500,
                            detail="Failed to refresh symbol data")


@router.get("/summary")
async def get_portfolio_summary(request: Request):
    """Get portfolio summary with positions and market data from PocketBase."""
    try:
        logger.info("Getting portfolio summary...")
        model_manager = get_model_manager()

        # Get user ID from authenticated session
        user_id = await get_current_user_id(request)
        if not user_id:
            logger.warning(
                "No authenticated user found, returning empty summary")
            return {
                "positions": [],
                "total_value": 0.0,
                "total_cash": 0.0,
                "total_btc": 0.0,
                "btc_avg_price": 0.0
            }

        logger.info(f"Getting portfolio summary for user: {user_id}")

        # Get positions filtered by user ID
        raw_positions = model_manager.get_positions(user_id)

        # Transform and validate positions
        positions = []
        symbols = []
        for raw_pos in raw_positions:
            try:
                position = transform_pocketbase_record(raw_pos, Position)
                positions.append(position)
                symbols.append(position.symbol)
            except Exception as e:
                logger.error(
                    f"Error validating position {
                        raw_pos.get('id')}: {e}")
                continue

        # Load symbol data for market prices
        symbol_data = {}
        for symbol in symbols:
            data = get_current_symbol_data(symbol)
            if data:
                symbol_data[symbol] = data

        # Enrich positions with market data and calculations
        enrich_positions_with_market_data(positions, symbol_data)

        # Log positions with missing market data
        for position in positions:
            if position.market_value is None:
                logger.warning(f"{position.symbol}: missing market data")

        # Create portfolio summary
        summary = create_portfolio_summary(positions)

        # Convert to dictionary for JSON response
        summary_dict = get_portfolio_summary_dict(summary)

        logger.info(
            f"Generated portfolio summary with {
                len(summary_dict)} positions for user {user_id}")
        return summary_dict
    except Exception as e:
        logger.error(f"Error generating portfolio summary: {e}")
        raise HTTPException(status_code=500,
                            detail="Failed to generate portfolio summary")
