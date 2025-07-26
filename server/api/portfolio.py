from fastapi import APIRouter, Request, HTTPException, Query
from server.models import get_model_manager
from server.api.auth import get_current_user_id
from utils.logger import get_api_logger
from pydantic import BaseModel
from typing import List
import time
import requests
from utils.config import POLYGON_API_KEY
from fastapi.responses import JSONResponse

logger = get_api_logger("portfolio")

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


class Position(BaseModel):
    id: str = None
    symbol: str
    quantity: float
    buy_price: float
    notes: str = None
    source: str = None


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
        most_recent = max(symbol_records, key=lambda x: x.get("cached_at", ""))
        current_data = {
            "last_price": most_recent.get("last_price"),
            "previous_close": most_recent.get("previous_close"),
            "timestamp": most_recent.get("timestamp", time.time()),
            "beta": most_recent.get("beta")
        }
        logger.debug(f"Retrieved current data for {symbol}: {current_data}")
        return current_data
    except Exception as e:
        logger.error(f"Error getting current symbol data for {symbol}: {e}")
        return None


def set_current_symbol_data(symbol, data):
    """Set current symbol data in PocketBase symbol cache."""
    try:
        model_manager = get_model_manager()
        cache_data = {
            "symbol": symbol,
            # Use last_price as the current price
            "price": data.get("last_price"),
            "date": time.strftime('%Y-%m-%d'),  # Current date
            "beta": data.get("beta"),
            "delta": None  # Placeholder for delta calculation
        }
        model_manager.update_symbol_cache(symbol, cache_data)
        logger.debug(f"Saved current data for {symbol}: {cache_data}")
    except Exception as e:
        logger.error(f"Error setting current symbol data for {symbol}: {e}")


def fetch_symbol_data(symbols):
    """Fetch symbol data from Polygon.io and cache in PocketBase."""
    result = []

    # Check if Polygon API key is available
    if not POLYGON_API_KEY:
        logger.warning("POLYGON_API_KEY not set, skipping market data fetch")
        return result

    for symbol in symbols:
        try:
            # Get previous day's data
            prev_url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/prev"
            prev_params = {"adjusted": "true", "apiKey": POLYGON_API_KEY}
            prev_resp = requests.get(prev_url, params=prev_params, timeout=10)
            prev_close = None
            last_price = None

            if prev_resp.status_code == 200:
                prev_data = prev_resp.json()
                prev_results = prev_data.get("results", [])
                if prev_results:
                    prev_close = prev_results[0].get("c")
                    last_price = prev_close
                    logger.debug(f"{symbol}: got previous close: {prev_close}")

            # Return data in the format expected by the new schema
            symbol_data = {
                "symbol": symbol,
                "price": last_price,  # Use last_price as the current price
                "date": time.strftime('%Y-%m-%d'),  # Current date
                "beta": None,
                "delta": None
            }
            result.append(symbol_data)
            logger.debug(f"{symbol}: market data prepared")
        except Exception as e:
            symbol_data = {
                "symbol": symbol,
                "price": None,
                "date": time.strftime('%Y-%m-%d'),
                "beta": None,
                "delta": None
            }
            result.append(symbol_data)
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
            return []

        logger.info(f"Getting portfolio summary for user: {user_id}")

        # Get positions filtered by user ID
        positions = model_manager.get_positions(user_id)
        # Load symbol data for market prices
        symbols = [pos["symbol"] for pos in positions]
        symbol_data = {}
        for symbol in symbols:
            data = get_current_symbol_data(symbol)
            if data:
                symbol_data[symbol] = data

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

            # Log only if there's an issue with data
            if market_value is None:
                logger.warning(f"{symbol}: missing market data")

            # Format decimals to 0.00 precision
            todays_return = round(todays_return,
                                  2) if todays_return is not None else None
            total_return = round(total_return,
                                 2) if total_return is not None else None
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

        logger.info(
            f"Generated portfolio summary with {
                len(summary)} positions for user {user_id} from PocketBase")
        return summary
    except Exception as e:
        logger.error(f"Error generating portfolio summary: {e}")
        raise HTTPException(status_code=500,
                            detail="Failed to generate portfolio summary")
