import robin_stocks.robinhood as r
from server.models import get_model_manager
from server.api.auth import get_current_user_id
from utils.logger import get_server_logger, get_data_validation_logger, get_api_logger
import os
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# Suppress robin_stocks verbose logging
logging.getLogger('robin_stocks').setLevel(logging.ERROR)
logging.getLogger('urllib3').setLevel(logging.ERROR)
logging.getLogger('requests').setLevel(logging.ERROR)

# Initialize loggers
logger = get_api_logger("robinhood")
validation_logger = get_data_validation_logger("robinhood")

router = APIRouter(prefix="/api/robinhood", tags=["robinhood"])

# Pydantic models for request/response validation


class RobinhoodSettings(BaseModel):
    enabled: bool = False
    display: bool = False
    username: str = ""
    password: str = ""
    mfa: str = ""


class RobinhoodStatus(BaseModel):
    enabled: bool
    display: bool
    has_credentials: bool
    last_pull: Optional[str] = None
    positions_count: int = 0
    orders_count: int = 0
    dividends_count: int = 0
    connection_status: str = "unknown"


async def get_robinhood_settings(request: Request) -> RobinhoodSettings:
    """Get Robinhood settings from PocketBase portfolio data."""
    try:
        logger.debug("Getting Robinhood settings from PocketBase...")
        model_manager = get_model_manager()

        # Get user ID from authenticated session
        user_id = await get_current_user_id(request)

        if not user_id:
            logger.warning(
                "No authenticated user found, returning default settings")
            return RobinhoodSettings()

        portfolio_data = model_manager.get_portfolio_data(user_id)

        settings = RobinhoodSettings(
            enabled=portfolio_data.get("robinhood_enabled", False),
            display=portfolio_data.get("robinhood_display", False),
            username=portfolio_data.get("robinhood_username", ""),
            password=portfolio_data.get("robinhood_password", ""),
            mfa=portfolio_data.get("robinhood_mfa", "")
        )

        logger.debug(
            f"Retrieved Robinhood settings: enabled={
                settings.enabled}, has_credentials={
                bool(
                    settings.username and settings.password)}")
        return settings
    except Exception as e:
        logger.error(f"Error getting Robinhood settings: {e}")
        raise HTTPException(status_code=500,
                            detail="Failed to get Robinhood settings")


def validate_robinhood_data(raw_data: Dict, data_type: str) -> bool:
    """Validate that Robinhood data has expected structure."""
    validation_logger.info(f"Validating {data_type} data structure...")

    if not raw_data:
        validation_logger.warning(
            f"Empty {data_type} data received from Robinhood")
        return False

    if data_type == "positions" and not isinstance(raw_data, dict):
        validation_logger.error(
            f"Positions data should be dict, got {
                type(raw_data)}")
        return False

    if data_type in ["orders", "dividends"] and not isinstance(raw_data, list):
        validation_logger.error(
            f"{data_type} data should be list, got {
                type(raw_data)}")
        return False

    # Log data size for monitoring
    if data_type == "positions":
        validation_logger.info(
            f"Positions data: {
                len(raw_data)} symbols found")
    else:
        validation_logger.info(
            f"{data_type} data: {
                len(raw_data)} records found")

    validation_logger.debug(
        f"Validated {data_type} data structure successfully")
    return True


def sanitize_symbol(symbol: str) -> Optional[str]:
    """Sanitize and validate symbol string."""
    if not symbol or not isinstance(symbol, str):
        validation_logger.warning(
            f"Invalid symbol type: {
                type(symbol)}, value: {symbol}")
        return None

    # Remove any whitespace and convert to uppercase
    cleaned = symbol.strip().upper()

    # Basic validation - symbols should be 1-10 characters, alphanumeric
    if len(cleaned) == 0:
        validation_logger.warning(
            f"Empty symbol after cleaning: original='{symbol}'")
        return None

    if len(cleaned) > 10:
        validation_logger.warning(
            f"Symbol too long: '{cleaned}' (length: {len(cleaned)})")
        return None

    if not cleaned.replace('.', '').isalnum():
        validation_logger.warning(f"Invalid symbol characters: '{
                                  cleaned}' (original: '{symbol}')")
        return None

    # Log successful sanitization if symbol changed
    if cleaned != symbol:
        validation_logger.debug(f"Symbol sanitized: '{symbol}' -> '{cleaned}'")

    return cleaned


def resolve_symbol_from_instrument(instrument_url: str) -> Optional[str]:
    """Resolve symbol from instrument URL using PocketBase symbol cache."""
    if not instrument_url:
        logger.debug("No instrument URL provided")
        return None

    try:
        model_manager = get_model_manager()

        # Check if symbol is cached in PocketBase
        cached_records = model_manager.get_symbol_cache()
        for record in cached_records:
            if record.get("instrument_url") == instrument_url:
                symbol = record.get("symbol")
                logger.debug(f"Found cached symbol {
                             symbol} for instrument {instrument_url}")
                return symbol

        # If not cached, fetch from Robinhood and cache it
        logger.debug(
            f"Symbol not cached, fetching from Robinhood for {instrument_url}")
        try:
            instrument_data = r.get_instrument_by_url(instrument_url)
            if instrument_data and 'symbol' in instrument_data:
                symbol = instrument_data['symbol']

                # Cache the symbol with instrument URL
                cache_record = {
                    'symbol': symbol,
                    'instrument_url': instrument_url,
                    'name': instrument_data.get('name', ''),
                    'simple_name': instrument_data.get('simple_name', ''),
                    'country': instrument_data.get('country', ''),
                    'tradability': instrument_data.get('tradability', ''),
                    'tradeable': instrument_data.get('tradeable', False),
                    'margin_initial_ratio': instrument_data.get('margin_initial_ratio', ''),
                    'maintenance_ratio': instrument_data.get('maintenance_ratio', ''),
                    'type': instrument_data.get('type', ''),
                    'bloomberg_unique': instrument_data.get('bloomberg_unique', ''),
                    'state': instrument_data.get('state', ''),
                    'day_trade_ratio': instrument_data.get('day_trade_ratio', ''),
                    'fundamentals': instrument_data.get('fundamentals', ''),
                    'quote': instrument_data.get('quote', ''),
                    'splits': instrument_data.get('splits', ''),
                    'updated_at': datetime.now().isoformat()
                }

                try:
                    model_manager.create_symbol_cache_record(cache_record)
                    logger.debug(
                        f"Cached symbol {symbol} for instrument {instrument_url}")
                except Exception as cache_error:
                    logger.warning(
                        f"Failed to cache symbol {symbol}: {cache_error}")

                return symbol

        except Exception as fetch_error:
            logger.warning(f"Failed to fetch instrument data for {
                           instrument_url}: {fetch_error}")

        logger.warning(
            f"Could not resolve symbol for instrument {instrument_url}")
        return None
    except Exception as e:
        logger.error(f"Error resolving symbol for {instrument_url}: {e}")
        return None


def calculate_profit_loss_for_user(
        user_id: str, source: str = "manual") -> List[Dict[str, Any]]:
    """Calculate profit/loss data for a specific user and return records for PocketBase."""
    try:
        logger.info(
            f"Calculating profit/loss for user {user_id} from source {source}")
        model_manager = get_model_manager()

        # Get user's positions and orders
        positions = model_manager.get_positions(user_id)
        orders = model_manager.get_orders(user_id)

        profit_loss_records = []

        # Calculate unrealized P/L for current positions
        for position in positions:
            symbol = position.get('symbol')
            quantity = position.get('quantity', 0)
            buy_price = position.get('buy_price', 0)

            if symbol and quantity > 0 and buy_price > 0:
                # Get current price from symbol cache
                symbol_data = model_manager.get_symbol_cache()
                current_price = None
                for cache_record in symbol_data:
                    if cache_record.get('symbol') == symbol:
                        current_price = cache_record.get('price')
                        break

                if current_price and current_price > 0:
                    unrealized_pl = (current_price - buy_price) * quantity
                    logger.debug(f"Calculating P/L for {symbol}: current_price={current_price}, buy_price={
                                 buy_price}, quantity={quantity}, unrealized_pl={unrealized_pl}")

                    # Ensure amount is a valid number
                    if unrealized_pl is not None and not (
                        isinstance(
                            unrealized_pl, float) and (
                            unrealized_pl != unrealized_pl)):  # Check for NaN
                        amount = round(unrealized_pl, 2)
                    else:
                        amount = 0.01  # Use small positive value instead of 0.0
                        logger.warning(
                            f"Invalid unrealized_pl calculated for {symbol}: {unrealized_pl}")

                    record = {
                        'symbol': symbol,
                        'type': 'Unrealized',
                        'amount': amount,
                        'period': 'YTD',
                        'date': datetime.now().strftime('%Y-%m-%d'),
                        'calculated_at': datetime.now().isoformat(),
                        'source': source
                    }
                    logger.debug(f"Creating unrealized P/L record: {record}")
                    profit_loss_records.append(record)
                else:
                    # Create record with 0 amount when no current price
                    # available
                    logger.debug(f"No current price available for {
                                 symbol}, current_price={current_price}")
                    record = {
                        'symbol': symbol,
                        'type': 'Unrealized',
                        'amount': 0.01,  # Use small positive value instead of 0.0
                        'period': 'YTD',
                        'date': datetime.now().strftime('%Y-%m-%d'),
                        'calculated_at': datetime.now().isoformat(),
                        'source': source
                    }
                    logger.debug(
                        f"Creating unrealized P/L record (no price): {record}")
                    profit_loss_records.append(record)

        # Calculate realized P/L from orders (simplified)
        # This is a basic calculation - in a real system you'd need more
        # sophisticated logic
        for order in orders:
            symbol = order.get('symbol')
            if symbol and symbol != 'UNKNOWN':
                # For now, just add a placeholder realized P/L record
                # In a real system, you'd calculate actual realized
                # gains/losses
                record = {
                    'symbol': symbol,
                    'type': 'Realized',
                    'amount': 0.01,  # Use small positive value instead of 0.0
                    'period': 'YTD',
                    'date': order.get('date', datetime.now().strftime('%Y-%m-%d')),
                    'calculated_at': datetime.now().isoformat(),
                    'source': source
                }
                logger.debug(f"Creating realized P/L record: {record}")
                profit_loss_records.append(record)

        # Final validation - ensure all records have valid amounts
        validated_records = []
        for record in profit_loss_records:
            amount = record.get('amount')
            # More robust validation
            if (amount is None or (isinstance(amount, float) and (amount != amount or amount == float(
                    'inf') or amount == float('-inf'))) or not isinstance(amount, (int, float))):
                # Use small positive value instead of 0.0
                record['amount'] = 0.01
                logger.warning(
                    f"Invalid amount found for {
                        record.get('symbol')}, setting to 0.01")
            else:
                # Ensure it's a valid number
                try:
                    record['amount'] = float(amount)
                    # If amount is 0, use small positive value
                    if record['amount'] == 0.0:
                        record['amount'] = 0.01
                except (ValueError, TypeError):
                    # Use small positive value instead of 0.0
                    record['amount'] = 0.01
                    logger.warning(
                        f"Could not convert amount to float for {
                            record.get('symbol')}, setting to 0.01")

            validated_records.append(record)

        logger.info(
            f"Calculated {
                len(validated_records)} profit/loss records for user {user_id} from source {source}")

        return validated_records

    except Exception as e:
        logger.error(f"Error calculating profit/loss for user {user_id}: {e}")
        return []


def map_dividends(raw_dividends: List[Dict], user_id: str) -> List[Dict]:
    """Map raw dividends to our data format."""
    try:
        logger.debug(f"Mapping {len(raw_dividends)} raw dividends...")
        mapped = []
        for d in raw_dividends:
            try:
                # Resolve symbol from instrument URL
                symbol = resolve_symbol_from_instrument(
                    d.get('instrument', '')) or 'UNKNOWN'
                mapped_dividend = {
                    'symbol': symbol,
                    'amount': float(
                        d.get(
                            'amount',
                            0)),
                    'date': d.get('payable_date') or d.get('record_date') or datetime.now().isoformat(),
                    'record_date': d.get('record_date') or '',
                    'payable_date': d.get('payable_date') or '',
                    'source': 'robinhood',
                    'user': user_id}
                mapped.append(mapped_dividend)
            except Exception as e:
                logger.error(
                    f"Error mapping dividend {
                        d.get(
                            'id',
                            'unknown')}: {e}")
                continue

        logger.info(f"Successfully mapped {len(mapped)} dividends")
        return mapped
    except Exception as e:
        logger.error(f"Error mapping dividends: {e}")
        return []


def map_positions(raw_positions: Dict, user_id: str) -> List[Dict]:
    """Map raw positions to our data format."""
    try:
        validation_logger.info(
            f"Starting position mapping for {
                len(raw_positions)} raw positions...")
        mapped = []
        skipped_count = 0
        error_count = 0

        for symbol, pos in raw_positions.items():
            try:
                # Sanitize symbol
                clean_symbol = sanitize_symbol(symbol)
                if not clean_symbol:
                    validation_logger.warning(
                        f"SKIPPED: Invalid symbol '{symbol}' in position data")
                    skipped_count += 1
                    continue

                # Extract and validate position data
                try:
                    quantity = float(pos.get('quantity', 0))
                except (ValueError, TypeError) as e:
                    validation_logger.warning(
                        f"SKIPPED: Invalid quantity for {clean_symbol}: {
                            pos.get('quantity')} - {e}")
                    skipped_count += 1
                    continue

                try:
                    buy_price = float(pos.get('average_buy_price', 0))
                except (ValueError, TypeError) as e:
                    validation_logger.warning(
                        f"SKIPPED: Invalid buy price for {clean_symbol}: {
                            pos.get('average_buy_price')} - {e}")
                    skipped_count += 1
                    continue

                # Validate data ranges
                if quantity <= 0:
                    validation_logger.info(
                        f"SKIPPED: Zero/negative quantity for {clean_symbol}: {quantity}")
                    skipped_count += 1
                    continue

                if buy_price < 0:
                    validation_logger.warning(f"ADJUSTED: Negative buy price for {
                                              clean_symbol}: {buy_price} -> 0.0")
                    buy_price = 0.0

                # Log suspicious data
                if quantity > 1000000:  # More than 1M shares
                    validation_logger.warning(
                        f"SUSPICIOUS: Very large quantity for {clean_symbol}: {quantity}")

                if buy_price > 10000:  # More than $10k per share
                    validation_logger.warning(
                        f"SUSPICIOUS: Very high buy price for {clean_symbol}: ${buy_price}")

                mapped_position = {
                    'symbol': clean_symbol,
                    'quantity': quantity,
                    'buy_price': buy_price,
                    'notes': pos.get('name', ''),
                    'source': 'robinhood',
                    'pulled_at': datetime.now().isoformat(),
                    'user': user_id
                }
                mapped.append(mapped_position)
                validation_logger.debug(
                    f"MAPPED: Position {clean_symbol} - Qty: {quantity}, Price: ${buy_price}")

            except (ValueError, TypeError) as e:
                validation_logger.error(
                    f"ERROR: Data conversion error for position {symbol}: {e}")
                error_count += 1
                continue
            except Exception as e:
                validation_logger.error(
                    f"ERROR: Unexpected error mapping position {symbol}: {e}")
                error_count += 1
                continue

        validation_logger.info(f"Position mapping complete: {len(mapped)} mapped, {
                               skipped_count} skipped, {error_count} errors")
        return mapped
    except Exception as e:
        validation_logger.error(f"CRITICAL: Error in position mapping: {e}")
        return []


def map_orders(raw_orders: List[Dict], user_id: str) -> List[Dict]:
    """Map raw orders to our data format."""
    try:
        logger.debug(f"Mapping {len(raw_orders)} raw orders...")
        orders = []
        order_id_counter = 1

        for order in raw_orders:
            try:
                if order.get('type') not in ('market', 'limit'):
                    logger.debug(
                        f"Skipping order {
                            order.get(
                                'id', 'unknown')}: type {
                            order.get('type')} not market/limit")
                    continue

                instrument_url = order.get('instrument')
                if not instrument_url:
                    logger.debug(
                        f"Skipping order {
                            order.get(
                                'id',
                                'unknown')}: missing instrument URL")
                    continue

                # Resolve symbol from instrument URL
                symbol = resolve_symbol_from_instrument(
                    instrument_url) or 'UNKNOWN'

                side = order.get('side', 'buy')
                order_id = order.get('id', '')
                executions = order.get('executions', [])

                if not executions:
                    logger.debug(
                        f"Skipping order {order_id}: no executions present")
                    continue

                for execution in executions:
                    try:
                        mapped_order = {
                            'symbol': symbol,
                            'type': side,
                            'quantity': float(execution.get('quantity') or 0),
                            'price': float(execution.get('price') or 0),
                            'date': execution.get('timestamp', ''),
                            'fees': sum([
                                float(execution.get('fees') or 0),
                                float(execution.get('sec_fee') or 0),
                                float(execution.get('taf_fee') or 0),
                                float(execution.get('cat_fee') or 0)
                            ]),
                            'pl': 0.0,
                            'source_id': order_id,
                            'notes': '',
                            'source': 'robinhood',
                            'pulled_at': datetime.now().isoformat(),
                            'user': user_id
                        }
                        orders.append(mapped_order)
                        order_id_counter += 1
                    except Exception as e:
                        logger.error(
                            f"Error mapping execution in order {order_id}: {e}")
                        continue
            except Exception as e:
                logger.error(
                    f"Error processing order {
                        order.get(
                            'id', 'unknown')}: {e}")
                continue

        logger.info(f"Successfully mapped {len(orders)} orders")
        return orders
    except Exception as e:
        logger.error(f"Error mapping orders: {e}")
        return []


@router.post("/pull")
async def pull_robinhood_data(request: Request):
    """Pull data from Robinhood and save to PocketBase."""
    logger.info("Starting Robinhood data pull...")

    try:
        # Get user ID from authenticated session
        user_id = await get_current_user_id(request)
        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="User not authenticated.")
        logger.info(f"Using user ID: {user_id}")

        settings = await get_robinhood_settings(request)
        if not settings.enabled:
            raise HTTPException(status_code=400,
                                detail="Robinhood integration is not enabled.")

        # Validate credentials before attempting authentication
        if not settings.username or not settings.password:
            logger.error("Robinhood credentials are missing")
            raise HTTPException(
                status_code=400,
                detail="Robinhood credentials are missing. Please configure username and password in settings.")

        logger.info(
            "Robinhood credentials validated, attempting authentication...")

        # Authenticate with Robinhood
        try:
            # Handle MFA properly - try different parameter approaches
            if settings.mfa:
                logger.info("Attempting Robinhood login with MFA...")
                try:
                    # Try with mfa_code parameter first
                    r.login(
                        settings.username,
                        settings.password,
                        mfa_code=settings.mfa)
                except Exception as mfa_error:
                    logger.warning(
                        f"MFA login with mfa_code failed: {mfa_error}")
                    # Try with the third positional parameter
                    r.login(settings.username, settings.password, settings.mfa)
            else:
                logger.info("Attempting Robinhood login without MFA...")
                r.login(settings.username, settings.password)

            logger.info("Successfully authenticated with Robinhood")
        except Exception as e:
            logger.error(f"Failed to authenticate with Robinhood: {e}")
            # Update portfolio settings with error
            try:
                model_manager = get_model_manager()
                portfolio_data = model_manager.get_portfolio_data(user_id)
                portfolio_data['robinhood_last_error'] = f"Authentication failed: {
                    e}"
                model_manager.update_portfolio_data(user_id, portfolio_data)
            except Exception as update_error:
                logger.error(f"Failed to update error status: {update_error}")

            raise HTTPException(
                status_code=401,
                detail=f"Failed to authenticate with Robinhood: {e}")

        # Pull data from Robinhood with individual error handling
        raw_positions = {}
        raw_orders = []
        raw_dividends = []

        try:
            logger.info("Pulling positions from Robinhood...")
            raw_positions = r.account.build_holdings()
            logger.info(
                f"Pulled {
                    len(raw_positions)} positions from Robinhood")
        except Exception as e:
            logger.error(f"Failed to pull positions from Robinhood: {e}")
            # Continue with other data pulls - don't fail completely

        try:
            logger.info("Pulling orders from Robinhood...")
            raw_orders = r.orders.get_all_stock_orders()
            logger.info(f"Pulled {len(raw_orders)} orders from Robinhood")
        except Exception as e:
            logger.error(f"Failed to pull orders from Robinhood: {e}")
            # Continue with other data pulls

        try:
            logger.info("Pulling dividends from Robinhood...")
            raw_dividends = r.account.get_dividends()
            logger.info(
                f"Pulled {
                    len(raw_dividends)} dividends from Robinhood")
        except Exception as e:
            logger.error(f"Failed to pull dividends from Robinhood: {e}")
            # Continue with other data pulls

        # Validate data structure
        validation_logger.info("=== Starting Robinhood data validation ===")

        if raw_positions and not validate_robinhood_data(
                raw_positions, "positions"):
            validation_logger.error(
                "CRITICAL: Invalid positions data structure, treating as empty")
            raw_positions = {}

        if raw_orders and not validate_robinhood_data(raw_orders, "orders"):
            validation_logger.error(
                "CRITICAL: Invalid orders data structure, treating as empty")
            raw_orders = []

        if raw_dividends and not validate_robinhood_data(
                raw_dividends, "dividends"):
            validation_logger.error(
                "CRITICAL: Invalid dividends data structure, treating as empty")
            raw_dividends = []

        validation_logger.info("=== Robinhood data validation complete ===")

        # Check if we got any data at all
        if not raw_positions and not raw_orders and not raw_dividends:
            error_msg = "Failed to pull any data from Robinhood"
            logger.error(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)

        # FIRST: Populate symbol cache with current market data
        try:
            logger.info("Populating symbol cache with current market data...")
            from server.api.portfolio import get_portfolio_symbols, fetch_symbol_data, save_symbol_data, calculate_and_save_betas

            # Get all symbols from positions
            symbols = set()
            for symbol in raw_positions.keys():
                if symbol:
                    symbols.add(symbol)

            if symbols:
                logger.info(
                    f"Fetching market data for {
                        len(symbols)} symbols...")
                symbol_data = fetch_symbol_data(list(symbols))

                # Use the new upsert method to avoid duplicates
                if symbol_data:
                    model_manager = get_model_manager()
                    upsert_results = model_manager.upsert_symbol_cache_records(
                        symbol_data)
                    logger.info(
                        f"Symbol cache upsert results: {upsert_results}")
                else:
                    logger.warning(
                        "No symbol data fetched - this may be due to missing POLYGON_API_KEY")

                # Calculate betas
                calculate_and_save_betas(list(symbols))
                logger.info(
                    f"Market data and betas updated for {
                        len(symbols)} symbols")
            else:
                logger.info("No symbols to populate in symbol cache")
        except Exception as e:
            logger.error(f"Error populating symbol cache: {e}")

        # SECOND: Map and save data to PocketBase
        try:
            logger.info("Mapping and saving positions...")
            mapped_positions = map_positions(raw_positions, user_id)
            model_manager = get_model_manager()
            position_results = model_manager.upsert_positions(
                mapped_positions, user_id)
            logger.info(f"Upserted positions: {position_results}")

            logger.info("Mapping and saving orders...")
            mapped_orders = map_orders(raw_orders, user_id)
            order_results = model_manager.upsert_orders(mapped_orders, user_id)
            logger.info(f"Upserted orders: {order_results}")

            logger.info("Mapping and saving dividends...")
            mapped_dividends = map_dividends(raw_dividends, user_id)
            dividend_results = model_manager.upsert_dividends(
                mapped_dividends, user_id)
            logger.info(f"Upserted dividends: {dividend_results}")

            # THIRD: Calculate and save profit/loss data (now with populated
            # symbol cache)
            logger.info("Calculating profit/loss data...")
            try:
                profit_loss_records = calculate_profit_loss_for_user(
                    user_id, "robinhood")
                if profit_loss_records:
                    upsert_result = model_manager.upsert_profit_loss_records(
                        profit_loss_records, user_id)
                    logger.info(
                        f"Profit/loss upsert result: {upsert_result}")
                else:
                    logger.info("No profit/loss records to save")
            except Exception as pl_error:
                logger.error(f"Error calculating profit/loss: {pl_error}")

            # FOURTH: Calculate and save profit/loss cache for all periods
            logger.info("Calculating profit/loss cache for all periods...")
            try:
                # Calculate P/L for all periods directly
                periods = ['1W', '1M', '3M', 'YTD', 'MAX']
                cache_records = []

                for period in periods:
                    try:
                        # Get positions and orders for this user
                        positions = model_manager.get_positions(user_id)
                        orders = model_manager.get_orders(user_id)

                        # Calculate current unrealized P/L
                        current_unrealized = 0.0
                        for pos in positions:
                            symbol = pos["symbol"]
                            # Get latest price from symbol cache
                            symbol_cache = model_manager.get_symbol_cache()
                            symbol_data = [
                                r for r in symbol_cache if r.get("symbol") == symbol]
                            if symbol_data:
                                latest_price = symbol_data[0].get(
                                    "price", pos["buy_price"])
                                current_unrealized += (latest_price -
                                                       pos["buy_price"]) * pos["quantity"]

                        # Calculate realized P/L from orders
                        realized = 0.0
                        for order in orders:
                            if order.get('type') == 'sell':
                                # Simple P/L calculation for sell orders
                                buy_price = order.get('price', 0)
                                sell_price = order.get('price', 0)
                                quantity = order.get('quantity', 0)
                                pl = (sell_price - buy_price) * quantity
                                realized += pl

                        # Ensure we have valid numbers
                        if realized is None or realized != realized:  # Check for NaN
                            realized = 0.0
                        if current_unrealized is None or current_unrealized != current_unrealized:  # Check for NaN
                            current_unrealized = 0.0

                        total = realized + current_unrealized

                        cache_record = {
                            "user": user_id,
                            "period": period,
                            "total": float(round(total, 2)),
                            "unrealized": float(round(current_unrealized, 2)),
                            "realized": float(round(realized, 2)),
                            "calculated_at": datetime.now().isoformat(),
                            "last_updated": datetime.now().isoformat()
                        }
                        cache_records.append(cache_record)

                    except Exception as period_error:
                        logger.error(
                            f"Error calculating P/L for period {period}: {period_error}")
                        # Add default record for this period
                        cache_record = {
                            "user": user_id,
                            "period": period,
                            "total": 0.0,
                            "unrealized": 0.0,
                            "realized": 0.0,
                            "calculated_at": datetime.now().isoformat(),
                            "last_updated": datetime.now().isoformat()
                        }
                        cache_records.append(cache_record)

                if cache_records:
                    # Upsert cache records
                    cache_upsert_result = model_manager.upsert_profit_loss_cache_records(
                        cache_records, user_id)
                    logger.info(
                        f"Profit/loss cache upsert result: {cache_upsert_result}")
                else:
                    logger.info("No profit/loss cache data to save")
            except Exception as cache_error:
                logger.error(
                    f"Error calculating profit/loss cache: {cache_error}")

        except Exception as e:
            logger.error(f"Failed to save data to PocketBase: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to save data to PocketBase: {e}")

        # Update portfolio settings with last pull time
        try:
            portfolio_data = model_manager.get_portfolio_data(user_id)
            portfolio_data["last_robinhood_pull"] = datetime.now().isoformat()
            portfolio_data["robinhood_last_error"] = None
            model_manager.update_portfolio_data(user_id, portfolio_data)
            logger.info("Updated portfolio settings with last pull time")
        except Exception as e:
            logger.error(f"Failed to update portfolio settings: {e}")

        # Log validation summary
        validation_logger.info("=== Robinhood Pull Validation Summary ===")
        validation_logger.info(
            f"Positions: {
                len(mapped_positions)} successfully mapped")
        validation_logger.info(
            f"Orders: {
                len(mapped_orders)} successfully mapped")
        validation_logger.info(
            f"Dividends: {
                len(mapped_dividends)} successfully mapped")
        validation_logger.info(
            f"Symbols updated: {
                len(symbols) if 'symbols' in locals() else 0}")
        validation_logger.info("=== End Validation Summary ===")

        logger.info("Robinhood data pull completed successfully")
        return {
            "success": True,
            "message": "Data pulled successfully",
            "positions_count": len(mapped_positions),
            "orders_count": len(mapped_orders),
            "dividends_count": len(mapped_dividends),
            "symbols_updated": len(symbols) if 'symbols' in locals() else 0,
            "pull_timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during Robinhood pull: {e}")
        # Update portfolio settings with error
        try:
            model_manager = get_model_manager()
            portfolio_data = model_manager.get_portfolio_data(user_id)
            portfolio_data["robinhood_last_error"] = str(e)
            model_manager.update_portfolio_data(user_id, portfolio_data)
        except Exception as update_error:
            logger.error(f"Failed to update error status: {update_error}")

        raise HTTPException(status_code=500,
                            detail=f"Unexpected error: {e}")


@router.get("/status", response_model=RobinhoodStatus)
async def get_robinhood_status(request: Request):
    """Get Robinhood integration status."""
    try:
        settings = await get_robinhood_settings(request)
        model_manager = get_model_manager()

        # Get counts from database
        user_id = await get_current_user_id(request)
        if user_id:
            positions_count = len(model_manager.get_positions(user_id))
            orders_count = len(model_manager.get_orders(user_id))
            dividends_count = len(model_manager.get_dividends(user_id))
        else:
            positions_count = 0
            orders_count = 0
            dividends_count = 0

        # Get last pull info from portfolio data
        last_pull = None
        last_error = None
        try:
            user_id = await get_current_user_id(request)
            if user_id:
                portfolio_data = model_manager.get_portfolio_data(user_id)
                last_pull = portfolio_data.get("last_robinhood_pull")
                last_error = portfolio_data.get("robinhood_last_error")
        except Exception as e:
            logger.error(f"Error getting portfolio data: {e}")

        # Test connection
        connection_status = "unknown"
        if settings.enabled and settings.username and settings.password:
            try:
                # Handle MFA properly in status check
                if settings.mfa:
                    r.login(
                        settings.username,
                        settings.password,
                        mfa_code=settings.mfa)
                else:
                    r.login(settings.username, settings.password)
                connection_status = "success"
                r.logout()
            except Exception as e:
                connection_status = f"failed: {e}"

        return RobinhoodStatus(
            enabled=settings.enabled,
            display=settings.display,
            has_credentials=bool(settings.username and settings.password),
            last_pull=last_pull,
            positions_count=positions_count,
            orders_count=orders_count,
            dividends_count=dividends_count,
            connection_status=connection_status
        )
    except Exception as e:
        logger.error(f"Error getting Robinhood status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
