import asyncio
import requests
try:
    import robin_stocks.robinhood as r
    from robin_stocks.helper import request_get
    ROBIN_STOCKS_AVAILABLE = True
except ImportError as e:
    logger = get_api_logger("robinhood")
    logger.error(f"robin_stocks library not available: {e}")
    r = None
    ROBIN_STOCKS_AVAILABLE = False

from server.models import get_model_manager
from server.api.auth import get_current_user_id, security
from config.backend.logger import get_server_logger, get_data_validation_logger, get_api_logger
import os
import logging
from datetime import datetime
import time
from typing import List, Dict, Optional, Any
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.security import HTTPAuthorizationCredentials
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


async def get_robinhood_settings(
        credentials: HTTPAuthorizationCredentials) -> RobinhoodSettings:
    """Get Robinhood settings from PocketBase portfolio data."""
    try:
        logger.debug("Getting Robinhood settings from PocketBase...")
        model_manager = get_model_manager()

        # Get user ID from authenticated session
        user_id = await get_current_user_id(credentials)

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
            f"Retrieved Robinhood settings: enabled={settings.enabled}, has_credentials={bool(settings.username and settings.password)}")
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
            f"Positions data should be dict, got {type(raw_data)}")
        return False

    if data_type in ["orders", "dividends"] and not isinstance(raw_data, list):
        validation_logger.error(
            f"{data_type} data should be list, got {type(raw_data)}")
        return False

    # Log data size for monitoring
    if data_type == "positions":
        validation_logger.info(
            f"Positions data: {len(raw_data)} symbols found")
    else:
        validation_logger.info(
            f"{data_type} data: {len(raw_data)} records found")

    validation_logger.debug(
        f"Validated {data_type} data structure successfully")
    return True


def sanitize_symbol(symbol: str) -> Optional[str]:
    """Sanitize and validate symbol string."""
    if not symbol or not isinstance(symbol, str):
        validation_logger.warning(
            f"Invalid symbol type: {type(symbol)}, value: {symbol}")
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
        validation_logger.warning(
            f"Invalid symbol characters: '{cleaned}' (original: '{symbol}')")
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
                logger.debug(
                    f"Found cached symbol {symbol} for instrument {instrument_url}")
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
            logger.warning(
                f"Failed to fetch instrument data for {instrument_url}: {fetch_error}")

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
                    logger.debug(
                        f"Calculating P/L for {symbol}: current_price={current_price}, buy_price={buy_price}, quantity={quantity}, unrealized_pl={unrealized_pl}")

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
                    logger.debug(
                        f"No current price available for {symbol}, current_price={current_price}")
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
                    f"Invalid amount found for {record.get('symbol')}, setting to 0.01")
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
                        f"Could not convert amount to float for {record.get('symbol')}, setting to 0.01")

            validated_records.append(record)

        logger.info(
            f"Calculated {len(validated_records)} profit/loss records for user {user_id} from source {source}")

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
                    f"Error mapping dividend {d.get('id','unknown')}: {e}")
                continue

        logger.info(f"Successfully mapped {len(mapped)} dividends")
        return mapped
    except Exception as e:
        logger.error(f"Error mapping dividends: {e}")
        return []


def map_positions(raw_positions: Dict, user_id: str) -> List[Dict]:
    """Map raw stock positions to our data format."""
    try:
        validation_logger.info(
            f"Starting stock position mapping for {len(raw_positions)} raw positions...")
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
                        f"SKIPPED: Invalid quantity for {clean_symbol}: {pos.get('quantity')} - {e}")
                    skipped_count += 1
                    continue

                try:
                    buy_price = float(pos.get('average_buy_price', 0))
                except (ValueError, TypeError) as e:
                    validation_logger.warning(
                        f"SKIPPED: Invalid buy price for {clean_symbol}: {pos.get('average_buy_price')} - {e}")
                    skipped_count += 1
                    continue

                # Validate data ranges
                if quantity <= 0:
                    validation_logger.info(
                        f"SKIPPED: Zero/negative quantity for {clean_symbol}: {quantity}")
                    skipped_count += 1
                    continue

                # Ensure buy_price is valid
                if buy_price is None or buy_price != buy_price:  # Check for NaN
                    buy_price = 0.0

                if buy_price < 0:
                    validation_logger.warning(
                        f"ADJUSTED: Negative buy price for {clean_symbol}: {buy_price} -> 0.0")
                    buy_price = 0.0

                # Log suspicious data
                if quantity > 1000000:  # More than 1M shares
                    validation_logger.warning(
                        f"SUSPICIOUS: Very large quantity for {clean_symbol}: {quantity}")

                # For crypto, higher prices are normal (BTC, ETH, etc.)
                if buy_price > 10000 and not market_data_service.is_crypto_symbol(
                        clean_symbol):  # More than $10k per share for stocks only
                    validation_logger.warning(
                        f"SUSPICIOUS: Very high buy price for {clean_symbol}: ${buy_price}")

                # Final validation - ensure we have valid data
                if buy_price <= 0:
                    validation_logger.warning(
                        f"SKIPPED: Invalid buy price for {clean_symbol}: {buy_price}")
                    skipped_count += 1
                    continue

                # Calculate market value and percent of portfolio
                market_value = float(
                    pos.get(
                        'market_value',
                        quantity *
                        buy_price))
                total_equity = float(pos.get('equity', 0))
                percent_of_portfolio = (
                    market_value /
                    total_equity *
                    100) if total_equity > 0 else 0

                # Calculate returns if we have both buy price and current price
                current_price = float(pos.get('price', buy_price))
                total_return = 0.0
                total_return_percent = 0.0
                todays_return = 0.0  # TODO: Calculate from historical data
                if buy_price > 0 and current_price > 0:
                    total_return = (current_price - buy_price) * quantity
                    total_return_percent = (
                        (current_price - buy_price) / buy_price) * 100

                # Get beta from fundamentals if available
                beta = None
                try:
                    fundamentals = pos.get('fundamentals', {})
                    if isinstance(fundamentals, str):
                        # If fundamentals is a URL, fetch it
                        response = requests.get(fundamentals, timeout=5)
                        if response.ok:
                            fundamentals = response.json()
                    if fundamentals and 'beta' in fundamentals:
                        beta = float(fundamentals['beta'])
                except Exception as e:
                    validation_logger.warning(
                        f"Failed to get beta for {clean_symbol}: {e}")

                mapped_position = {
                    'symbol': clean_symbol,
                    'quantity': quantity,
                    'buy_price': buy_price,
                    'market_value': market_value,
                    'current_price': current_price,
                    'total_return': total_return,
                    'total_return_percent': total_return_percent,
                    'todays_return': todays_return,
                    'percent_of_portfolio': percent_of_portfolio,
                    'beta': beta,
                    'delta': None,  # Not available from Robinhood
                    'notes': pos.get('name', ''),
                    'source': 'robinhood',
                    'is_crypto': False,  # Stock positions are not crypto
                    'pulled_at': datetime.now().isoformat(),
                    'user': user_id
                }
                mapped.append(mapped_position)
                validation_logger.debug(
                    f"MAPPED: Stock Position {clean_symbol} - Qty: {quantity}, Price: ${buy_price}")

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

        validation_logger.info(
            f"Stock position mapping complete: {len(mapped)} mapped, {skipped_count} skipped, {error_count} errors")
        return mapped
    except Exception as e:
        validation_logger.error(
            f"CRITICAL: Error in stock position mapping: {e}")
        return []


def map_crypto_positions(
        raw_crypto_positions: List[Dict],
        user_id: str) -> List[Dict]:
    """Map raw crypto positions to our data format."""
    try:
        validation_logger.info(
            f"Starting crypto position mapping for {len(raw_crypto_positions)} raw crypto positions...")

        # Log the first crypto position structure for debugging
        if raw_crypto_positions:
            validation_logger.info(f"=== CRYPTO POSITION DATA STRUCTURE ===")
            validation_logger.info(
                f"First crypto position keys: {list(raw_crypto_positions[0].keys())}")
            validation_logger.info(
                f"First crypto position data: {raw_crypto_positions[0]}")
            validation_logger.info(
                f"=== END CRYPTO POSITION DATA STRUCTURE ===")

        mapped = []
        skipped_count = 0
        error_count = 0

        for i, crypto_pos in enumerate(raw_crypto_positions):
            try:
                validation_logger.info(
                    f"=== Processing crypto position {i + 1}/{len(raw_crypto_positions)} ===")
                validation_logger.info(
                    f"Raw crypto position data: {crypto_pos}")

                # Extract crypto symbol (e.g., "BTC", "ETH")
                crypto_symbol = crypto_pos.get('currency', {}).get('code', '')
                validation_logger.info(
                    f"Crypto symbol extracted: '{crypto_symbol}'")

                if not crypto_symbol:
                    validation_logger.warning(
                        f"SKIPPED: Missing crypto symbol in position data")
                    skipped_count += 1
                    continue

                # Sanitize symbol
                clean_symbol = sanitize_symbol(crypto_symbol)
                validation_logger.info(f"Sanitized symbol: '{clean_symbol}'")

                if not clean_symbol:
                    validation_logger.warning(
                        f"SKIPPED: Invalid crypto symbol '{crypto_symbol}' in position data")
                    skipped_count += 1
                    continue

                # Extract and validate position data
                raw_quantity = crypto_pos.get('quantity', 0)
                validation_logger.info(
                    f"Raw quantity: {raw_quantity} (type: {type(raw_quantity)})")

                try:
                    quantity = float(raw_quantity)
                    validation_logger.info(f"Parsed quantity: {quantity}")
                except (ValueError, TypeError) as e:
                    validation_logger.warning(
                        f"SKIPPED: Invalid quantity for {clean_symbol}: {raw_quantity} - {e}")
                    skipped_count += 1
                    continue

                # Log all available fields for cost basis calculation
                validation_logger.info(
                    f"Available fields for cost calculation:")
                validation_logger.info(
                    f"  - cost_basis: {crypto_pos.get('cost_basis')}")
                validation_logger.info(
                    f"  - average_buy_price: {crypto_pos.get('average_buy_price')}")
                validation_logger.info(
                    f"  - total_cost: {crypto_pos.get('total_cost')}")
                validation_logger.info(
                    f"  - equity: {crypto_pos.get('equity')}")
                validation_logger.info(
                    f"  - market_value: {crypto_pos.get('market_value')}")

                # Log cost_bases array details
                cost_bases = crypto_pos.get('cost_bases', [])
                validation_logger.info(
                    f"  - cost_bases array: {len(cost_bases)} items")
                if cost_bases:
                    validation_logger.info(
                        f"  - First cost_bases item: {cost_bases[0]}")

                # Log tax_lot_cost_bases array details
                tax_lot_cost_bases = crypto_pos.get('tax_lot_cost_bases', [])
                validation_logger.info(
                    f"  - tax_lot_cost_bases array: {len(tax_lot_cost_bases)} items")
                if tax_lot_cost_bases:
                    validation_logger.info(
                        f"  - First tax_lot_cost_bases item: {tax_lot_cost_bases[0]}")

                # Log all available date fields
                validation_logger.info(f"Available date fields:")
                validation_logger.info(
                    f"  - created_at: {crypto_pos.get('created_at')}")
                validation_logger.info(f"  - date: {crypto_pos.get('date')}")
                validation_logger.info(
                    f"  - purchase_date: {crypto_pos.get('purchase_date')}")
                validation_logger.info(
                    f"  - updated_at: {crypto_pos.get('updated_at')}")
                validation_logger.info(
                    f"  - last_transaction_at: {crypto_pos.get('last_transaction_at')}")

                try:
                    # For crypto, we need to calculate the average buy price
                    # First try to get cost basis from the cost_bases array
                    cost_basis = 0.0
                    buy_price = 0.0

                    # Check cost_bases array first (this is where Robinhood
                    # stores the actual cost data)
                    cost_bases = crypto_pos.get('cost_bases', [])
                    if cost_bases:
                        # Sum up all direct cost basis from the array
                        total_cost_basis = 0.0
                        total_quantity = 0.0

                        for cost_basis_item in cost_bases:
                            try:
                                direct_cost_basis = float(
                                    cost_basis_item.get('direct_cost_basis', 0))
                                direct_quantity = float(
                                    cost_basis_item.get('direct_quantity', 0))
                                total_cost_basis += direct_cost_basis
                                total_quantity += direct_quantity
                                validation_logger.info(
                                    f"Cost basis item: direct_cost_basis={direct_cost_basis}, direct_quantity={direct_quantity}")
                            except (ValueError, TypeError) as e:
                                validation_logger.warning(
                                    f"Failed to parse cost basis item: {e}")

                        if total_quantity > 0 and total_cost_basis > 0:
                            cost_basis = total_cost_basis
                            buy_price = total_cost_basis / total_quantity
                            validation_logger.info(
                                f"Calculated from cost_bases array: cost_basis={cost_basis}, buy_price={buy_price}")
                        else:
                            validation_logger.warning(
                                f"Invalid totals from cost_bases array: total_cost_basis={total_cost_basis}, total_quantity={total_quantity}")
                    else:
                        # Fallback to the old cost_basis field
                        cost_basis = float(crypto_pos.get('cost_basis', 0))
                        validation_logger.info(
                            f"Using fallback cost_basis: {cost_basis}")

                        if quantity > 0 and cost_basis > 0:
                            buy_price = cost_basis / quantity
                            validation_logger.info(
                                f"Calculated buy price from cost_basis: {buy_price}")

                    # If we still don't have a valid buy price, try alternative
                    # fields
                    if buy_price <= 0:
                        validation_logger.warning(
                            f"Cannot calculate buy price from cost_bases (quantity: {quantity}, cost_basis: {cost_basis})")

                        # Try alternative fields
                        alternative_buy_price = None

                        # Try average_buy_price if available
                        if crypto_pos.get('average_buy_price'):
                            try:
                                alternative_buy_price = float(
                                    crypto_pos.get('average_buy_price'))
                                validation_logger.info(
                                    f"Using average_buy_price: {alternative_buy_price}")
                            except (ValueError, TypeError):
                                validation_logger.warning(
                                    "Failed to parse average_buy_price")

                        # Try total_cost / quantity if available
                        elif crypto_pos.get('total_cost') and quantity > 0:
                            try:
                                total_cost = float(
                                    crypto_pos.get('total_cost'))
                                alternative_buy_price = total_cost / quantity
                                validation_logger.info(
                                    f"Calculated from total_cost: {alternative_buy_price}")
                            except (ValueError, TypeError):
                                validation_logger.warning(
                                    "Failed to calculate from total_cost")

                        if alternative_buy_price and alternative_buy_price > 0:
                            buy_price = alternative_buy_price
                            validation_logger.info(
                                f"Using alternative buy price: {buy_price}")
                        else:
                            # Check if we have a buy date to get historical
                            # price
                            buy_date = crypto_pos.get('created_at') or crypto_pos.get(
                                'date') or crypto_pos.get('purchase_date')
                            if buy_date:
                                validation_logger.info(
                                    f"Found buy date: {buy_date}, attempting to get historical price...")
                                try:
                                    # Convert date format if needed
                                    if 'T' in buy_date:
                                        # Extract YYYY-MM-DD from ISO format
                                        buy_date = buy_date.split('T')[0]

                                    from server.api.market_data import market_data_service
                                    historical_price = market_data_service.get_crypto_historical_price(
                                        clean_symbol, buy_date)
                                    if historical_price and historical_price > 0:
                                        buy_price = historical_price
                                        validation_logger.info(
                                            f"Using historical price from {buy_date}: {buy_price}")
                                    else:
                                        validation_logger.warning(
                                            f"Could not get historical price for {clean_symbol} on {buy_date}")
                                        buy_price = 0.0
                                except Exception as e:
                                    validation_logger.warning(
                                        f"Failed to get historical price: {e}")
                                    buy_price = 0.0
                            else:
                                validation_logger.info(
                                    "No buy date found, attempting to get current crypto price as fallback...")
                                try:
                                    crypto_quote = r.crypto.get_crypto_quote_from_symbol(
                                        clean_symbol)
                                    validation_logger.info(
                                        f"Crypto quote response: {crypto_quote}")

                                    if crypto_quote and 'mark_price' in crypto_quote:
                                        buy_price = float(
                                            crypto_quote['mark_price'])
                                        validation_logger.info(
                                            f"Using current market price as fallback: {buy_price}")
                                    else:
                                        buy_price = 0.0
                                        validation_logger.warning(
                                            "No mark_price in crypto quote")
                                except Exception as e:
                                    buy_price = 0.0
                                    validation_logger.warning(
                                        f"Failed to get crypto quote: {e}")
                except (ValueError, TypeError) as e:
                    validation_logger.warning(
                        f"SKIPPED: Invalid cost basis for {clean_symbol}: {crypto_pos.get('cost_basis')} - {e}")
                    skipped_count += 1
                    continue

                # Validate data ranges
                if quantity <= 0:
                    validation_logger.info(
                        f"SKIPPED: Zero/negative quantity for {clean_symbol}: {quantity}")
                    skipped_count += 1
                    continue

                # Ensure buy_price is valid
                if buy_price is None or buy_price != buy_price:  # Check for NaN
                    buy_price = 0.0

                if buy_price < 0:
                    validation_logger.warning(
                        f"ADJUSTED: Negative buy price for {clean_symbol}: {buy_price} -> 0.0")
                    buy_price = 0.0

                # Log suspicious data
                if quantity > 1000000:  # More than 1M units
                    validation_logger.warning(
                        f"SUSPICIOUS: Very large quantity for {clean_symbol}: {quantity}")

                if buy_price > 100000:  # More than $100k per unit (for crypto)
                    validation_logger.warning(
                        f"SUSPICIOUS: Very high buy price for {clean_symbol}: ${buy_price}")

                # Final validation - ensure we have valid data
                if buy_price <= 0:
                    validation_logger.warning(
                        f"SKIPPED: Invalid buy price for {clean_symbol}: {buy_price}")
                    skipped_count += 1
                    continue

                # Calculate market value and percent of portfolio
                market_value = float(
                    crypto_pos.get(
                        'market_value',
                        quantity * buy_price))
                total_equity = float(crypto_pos.get('equity', 0))
                percent_of_portfolio = (
                    market_value /
                    total_equity *
                    100) if total_equity > 0 else 0

                # Calculate returns if we have both buy price and current price
                current_price = float(crypto_pos.get('price', buy_price))
                total_return = 0.0
                total_return_percent = 0.0
                todays_return = 0.0  # TODO: Calculate from historical data
                if buy_price > 0 and current_price > 0:
                    total_return = (current_price - buy_price) * quantity
                    total_return_percent = (
                        (current_price - buy_price) / buy_price) * 100

                mapped_position = {
                    'symbol': clean_symbol,
                    'quantity': quantity,
                    'buy_price': buy_price,
                    'market_value': market_value,
                    'current_price': current_price,
                    'total_return': total_return,
                    'total_return_percent': total_return_percent,
                    'todays_return': todays_return,
                    'percent_of_portfolio': percent_of_portfolio,
                    'beta': None,  # Crypto doesn't have beta
                    'delta': None,  # Crypto doesn't have delta
                    'notes': crypto_pos.get('currency', {}).get('name', clean_symbol),
                    'source': 'robinhood',  # Changed from 'robinhood_crypto'
                    'is_crypto': True,  # Mark as crypto
                    'pulled_at': datetime.now().isoformat(),
                    'user': user_id
                }

                mapped.append(mapped_position)
                validation_logger.debug(
                    f"MAPPED: Crypto Position {clean_symbol} - Qty: {quantity}, Price: ${buy_price}")

            except (ValueError, TypeError) as e:
                validation_logger.error(
                    f"ERROR: Data conversion error for crypto position {crypto_pos.get('id', 'unknown')}: {e}")
                error_count += 1
                continue
            except Exception as e:
                validation_logger.error(
                    f"ERROR: Unexpected error mapping crypto position {crypto_pos.get('id', 'unknown')}: {e}")
                error_count += 1
                continue

        validation_logger.info(
            f"Crypto position mapping complete: {len(mapped)} mapped, {skipped_count} skipped, {error_count} errors")
        return mapped
    except Exception as e:
        validation_logger.error(
            f"CRITICAL: Error in crypto position mapping: {e}")
        return []


def map_orders(raw_orders: List[Dict], user_id: str) -> List[Dict]:
    """Map raw stock orders to our data format."""
    try:
        logger.debug(f"Mapping {len(raw_orders)} raw stock orders...")
        orders = []
        order_id_counter = 1

        for order in raw_orders:
            try:
                if order.get('type') not in ('market', 'limit'):
                    logger.debug(
                        f"Skipping stock order {order.get('id', 'unknown')}: type {order.get('type')} not market/limit")
                    continue

                instrument_url = order.get('instrument')
                if not instrument_url:
                    logger.debug(
                        f"Skipping stock order {order.get('id','unknown')}: missing instrument URL")
                    continue

                # Resolve symbol from instrument URL
                symbol = resolve_symbol_from_instrument(
                    instrument_url) or 'UNKNOWN'

                side = order.get('side', 'buy')
                order_id = order.get('id', '')
                executions = order.get('executions', [])

                if not executions:
                    logger.debug(
                        f"Skipping stock order {order_id}: no executions present")
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
                            f"Error mapping execution in stock order {order_id}: {e}")
                        continue
            except Exception as e:
                logger.error(
                    f"Error processing stock order {order.get('id', 'unknown')}: {e}")
                continue

        logger.info(f"Successfully mapped {len(orders)} stock orders")
        return orders
    except Exception as e:
        logger.error(f"Error mapping stock orders: {e}")
        return []


def map_crypto_orders(
        raw_crypto_orders: List[Dict],
        user_id: str) -> List[Dict]:
    """Map raw crypto orders to our data format."""
    try:
        logger.debug(f"Mapping {len(raw_crypto_orders)} raw crypto orders...")

        # Log the first crypto order structure for debugging
        if raw_crypto_orders:
            logger.info(f"=== CRYPTO ORDER DATA STRUCTURE ===")
            logger.info(
                f"First crypto order keys: {list(raw_crypto_orders[0].keys())}")
            logger.info(f"First crypto order data: {raw_crypto_orders[0]}")
            logger.info(f"=== END CRYPTO ORDER DATA STRUCTURE ===")

        orders = []
        order_id_counter = 1

        for i, order in enumerate(raw_crypto_orders):
            try:
                logger.info(
                    f"=== Processing crypto order {i + 1}/{len(raw_crypto_orders)} ===")
                logger.info(f"Raw crypto order data: {order}")

                if order.get('type') not in ('market', 'limit'):
                    logger.debug(
                        f"Skipping crypto order {order.get('id', 'unknown')}: type {order.get('type')} not market/limit")
                    continue

                # Extract crypto symbol
                crypto_symbol = order.get('currency_pair_id', '')
                logger.info(f"Crypto symbol extracted: '{crypto_symbol}'")

                if not crypto_symbol:
                    logger.debug(
                        f"Skipping crypto order {order.get('id','unknown')}: missing currency pair")
                    continue

                # Clean up crypto symbol (e.g., "BTC-USD" -> "BTC")
                symbol = crypto_symbol.split(
                    '-')[0] if '-' in crypto_symbol else crypto_symbol
                logger.info(f"Cleaned symbol: '{symbol}'")

                side = order.get('side', 'buy')
                order_id = order.get('id', '')
                executions = order.get('executions', [])

                logger.info(
                    f"Order side: {side}, ID: {order_id}, Executions count: {len(executions)}")

                if not executions:
                    logger.debug(
                        f"Skipping crypto order {order_id}: no executions present")
                    continue

                for j, execution in enumerate(executions):
                    try:
                        logger.info(
                            f"Processing execution {j + 1}/{len(executions)}: {execution}")

                        mapped_order = {
                            'symbol': symbol,
                            'type': side,
                            'quantity': float(execution.get('quantity') or 0),
                            'price': float(execution.get('price') or 0),
                            'date': execution.get('timestamp', ''),
                            'fees': float(execution.get('fees') or 0),
                            'pl': 0.0,
                            'source_id': order_id,
                            'notes': crypto_symbol,
                            'source': 'robinhood_crypto',
                            'pulled_at': datetime.now().isoformat(),
                            'user': user_id
                        }

                        logger.info(f"Mapped crypto order: {mapped_order}")
                        orders.append(mapped_order)
                        order_id_counter += 1
                    except Exception as e:
                        logger.error(
                            f"Error mapping execution in crypto order {order_id}: {e}")
                        continue
            except Exception as e:
                logger.error(
                    f"Error processing crypto order {order.get('id', 'unknown')}: {e}")
                continue

        logger.info(f"Successfully mapped {len(orders)} crypto orders")
        return orders
    except Exception as e:
        logger.error(f"Error mapping crypto orders: {e}")
        return []


async def _run_blocking(fn, timeout: int = 30):
    """Run a synchronous blocking function in a thread pool with a timeout."""
    return await asyncio.wait_for(asyncio.to_thread(fn), timeout=timeout)


async def pull_robinhood_data_internal(
        credentials: HTTPAuthorizationCredentials, total_timeout: int = 240) -> Dict[str, Any]:
    """Internal function to pull data from Robinhood - used by workflows

    Args:
        credentials: Auth credentials for user authentication.
        total_timeout: Max total seconds for the entire pull (default 240).
                       Returns partial results on timeout instead of crashing.
    """
    logger.info("Starting Robinhood data pull...")

    # Check if robin_stocks is available
    if not ROBIN_STOCKS_AVAILABLE:
        logger.error("robin_stocks library not available")
        return {
            "success": False,
            "error": "robin_stocks library not available"}

    try:
        return await asyncio.wait_for(
            _exec_robinhood_pull(credentials),
            timeout=total_timeout
        )
    except asyncio.TimeoutError:
        logger.error(
            f"Robinhood data pull timed out after {total_timeout}s total")
        return {
            "success": True,
            "partial": True,
            "error": f"Sync timed out after {total_timeout}s \u2014 data may be incomplete. Try again for full sync."
        }


async def _exec_robinhood_pull(
        credentials: HTTPAuthorizationCredentials) -> Dict[str, Any]:
    """Execute the actual Robinhood data pull with per-section timeouts."""
    try:
        # Get user ID from authenticated session
        user_id = await get_current_user_id(credentials)
        if not user_id:
            return {"success": False, "error": "User not authenticated"}

        logger.info(f"Using user ID: {user_id}")

        settings = await get_robinhood_settings(credentials)
        if not settings.enabled:
            return {
                "success": False,
                "error": "Robinhood integration is not enabled"}

        # Validate credentials before attempting authentication
        if not settings.username or not settings.password:
            logger.error("Robinhood credentials are missing")
            return {
                "success": False,
                "error": "Robinhood credentials are missing"}

        logger.info(
            "Robinhood credentials validated, attempting authentication...")

        # Authenticate with Robinhood
        try:
            # Handle MFA properly - try different parameter approaches
            if settings.mfa:
                logger.info("Attempting Robinhood login with MFA...")
                try:
                    # Try with mfa_code parameter first
                    await _run_blocking(
                        lambda: r.login(
                            settings.username,
                            settings.password,
                            mfa_code=settings.mfa),
                        timeout=30)
                except Exception as mfa_error:
                    logger.warning(
                        f"MFA login with mfa_code failed: {mfa_error}")
                    # Try with the third positional parameter
                    await _run_blocking(
                        lambda: r.login(settings.username, settings.password, settings.mfa),
                        timeout=30)
            else:
                logger.info("Attempting Robinhood login without MFA...")
                await _run_blocking(
                    lambda: r.login(settings.username, settings.password),
                    timeout=30)

            logger.info("Successfully authenticated with Robinhood")
        except asyncio.TimeoutError:
            logger.error("Robinhood login timed out after 30 seconds")
            return {"success": False, "error": "Robinhood login timed out"}
        except Exception as e:
            logger.error(f"Failed to authenticate with Robinhood: {e}")
            # Update portfolio settings with error
            try:
                model_manager = get_model_manager()
                portfolio_data = model_manager.get_portfolio_data(user_id)
                portfolio_data['robinhood_last_error'] = f"Authentication failed: {e}"
                model_manager.update_portfolio_data(user_id, portfolio_data)
            except Exception as update_error:
                logger.error(f"Failed to update error status: {update_error}")

            return {
                "success": False,
                "error": f"Failed to authenticate with Robinhood: {e}"}

        # Pull data from Robinhood with individual error handling
        raw_positions = {}
        raw_orders = []
        raw_dividends = []

        try:
            logger.info("Pulling stock positions from Robinhood...")
            raw_positions = await _run_blocking(r.account.build_holdings, timeout=120)
            logger.info(
                f"Pulled {len(raw_positions)} stock positions from Robinhood")
        except asyncio.TimeoutError:
            logger.error(
                "Robinhood stock positions pull timed out after 120 seconds")
        except Exception as e:
            logger.error(f"Failed to pull stock positions from Robinhood: {e}")
            # Continue with other data pulls - don't fail completely

        try:
            logger.info("Pulling crypto positions from Robinhood...")
            raw_crypto_positions = await _run_blocking(r.crypto.get_crypto_positions, timeout=120)
            logger.info(
                f"Pulled {len(raw_crypto_positions)} crypto positions from Robinhood")

            # Log the raw crypto positions data structure
            if raw_crypto_positions:
                logger.info("=== RAW CRYPTO POSITIONS DATA ===")
                logger.info(
                    f"Number of crypto positions: {len(raw_crypto_positions)}")
                logger.info(
                    f"First crypto position sample: {raw_crypto_positions[0]}")
                logger.info("=== END RAW CRYPTO POSITIONS DATA ===")
            else:
                logger.info("No crypto positions found")

        except asyncio.TimeoutError:
            logger.error(
                "Robinhood crypto positions pull timed out after 120 seconds")
            raw_crypto_positions = []
        except Exception as e:
            logger.error(
                f"Failed to pull crypto positions from Robinhood: {e}")
            raw_crypto_positions = []
            # Continue with other data pulls

        try:
            logger.info("Pulling stock orders from Robinhood...")
            raw_orders = await _run_blocking(r.orders.get_all_stock_orders, timeout=120)
            logger.info(
                f"Pulled {len(raw_orders)} stock orders from Robinhood")
        except asyncio.TimeoutError:
            logger.error(
                "Robinhood stock orders pull timed out after 120 seconds")
        except Exception as e:
            logger.error(f"Failed to pull stock orders from Robinhood: {e}")
            # Continue with other data pulls

        try:
            logger.info("Pulling crypto orders from Robinhood...")
            raw_crypto_orders = []

            # Try get_crypto_orders first
            try:
                raw_crypto_orders = await _run_blocking(r.crypto.get_crypto_orders, timeout=60)
                logger.info(
                    f"Pulled {len(raw_crypto_orders)} crypto orders using get_crypto_orders")
            except asyncio.TimeoutError:
                logger.warning(
                    "get_crypto_orders timed out, trying alternatives...")
                raw_crypto_orders = []
            except AttributeError:
                logger.warning(
                    "get_crypto_orders not available, trying alternative methods...")

                # Try get_crypto_order_history
                try:
                    raw_crypto_orders = await _run_blocking(r.crypto.get_crypto_order_history, timeout=60)
                    logger.info(
                        f"Pulled {len(raw_crypto_orders)} crypto orders using get_crypto_order_history")
                except asyncio.TimeoutError:
                    logger.warning(
                        "get_crypto_order_history timed out, trying alternatives...")
                    raw_crypto_orders = []
                except AttributeError:
                    logger.warning(
                        "get_crypto_order_history not available, trying get_crypto_orders_by_id...")

                    # Try to get orders by getting account info first
                    try:
                        account = await _run_blocking(r.load_account_profile, timeout=30)
                        if account and 'crypto_account' in account:
                            crypto_account_id = account['crypto_account']
                            raw_crypto_orders = await _run_blocking(
                                lambda: r.crypto.get_crypto_orders_by_id(crypto_account_id), timeout=60)
                            logger.info(
                                f"Pulled {len(raw_crypto_orders)} crypto orders using get_crypto_orders_by_id")
                        else:
                            logger.warning(
                                "No crypto account found in account profile")
                    except asyncio.TimeoutError:
                        logger.warning("load_account_profile timed out")
                        raw_crypto_orders = []
                    except Exception as e:
                        logger.warning(
                            f"Failed to get crypto orders by account ID: {e}")

            # Log the raw crypto orders data structure
            if raw_crypto_orders:
                logger.info("=== RAW CRYPTO ORDERS DATA ===")
                logger.info(
                    f"Number of crypto orders: {len(raw_crypto_orders)}")
                logger.info(
                    f"First crypto order sample: {raw_crypto_orders[0]}")
                logger.info("=== END RAW CRYPTO ORDERS DATA ===")
            else:
                logger.info("No crypto orders found")

        except asyncio.TimeoutError:
            logger.error("Robinhood crypto orders pull timed out")
            raw_crypto_orders = []
        except Exception as e:
            logger.error(f"Failed to pull crypto orders from Robinhood: {e}")
            raw_crypto_orders = []
            # Continue with other data pulls

        try:
            logger.info("Pulling dividends from Robinhood...")
            raw_dividends = await _run_blocking(r.account.get_dividends, timeout=120)
            logger.info(
                f"Pulled {len(raw_dividends)} dividends from Robinhood")
        except asyncio.TimeoutError:
            logger.error(
                "Robinhood dividends pull timed out after 120 seconds")
        except Exception as e:
            logger.error(f"Failed to pull dividends from Robinhood: {e}")
            # Continue with other data pulls

        # Validate data structure
        validation_logger.info("=== Starting Robinhood data validation ===")

        if raw_positions and not validate_robinhood_data(
                raw_positions, "positions"):
            validation_logger.error(
                "CRITICAL: Invalid stock positions data structure, treating as empty")
            raw_positions = {}

        if raw_crypto_positions and not validate_robinhood_data(
                raw_crypto_positions, "crypto_positions"):
            validation_logger.error(
                "CRITICAL: Invalid crypto positions data structure, treating as empty")
            raw_crypto_positions = []

        if raw_orders and not validate_robinhood_data(raw_orders, "orders"):
            validation_logger.error(
                "CRITICAL: Invalid stock orders data structure, treating as empty")
            raw_orders = {}

        if raw_crypto_orders and not validate_robinhood_data(
                raw_crypto_orders, "crypto_orders"):
            validation_logger.error(
                "CRITICAL: Invalid crypto orders data structure, treating as empty")
            raw_crypto_orders = []

        if raw_dividends and not validate_robinhood_data(
                raw_dividends, "dividends"):
            validation_logger.error(
                "CRITICAL: Invalid dividends data structure, treating as empty")
            raw_dividends = {}

        validation_logger.info("=== Robinhood data validation complete ===")

        # Check if we got any data at all
        if not raw_positions and not raw_crypto_positions and not raw_orders and not raw_crypto_orders and not raw_dividends:
            error_msg = "Failed to pull any data from Robinhood"
            logger.error(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)

        # Map and save data to PocketBase
        try:
            logger.info("Mapping and saving stock positions...")
            mapped_stock_positions = map_positions(raw_positions, user_id)

            logger.info("Mapping and saving crypto positions...")
            mapped_crypto_positions = map_crypto_positions(
                raw_crypto_positions, user_id)

            # Combine all positions
            all_mapped_positions = mapped_stock_positions + mapped_crypto_positions
            model_manager = get_model_manager()
            position_results = model_manager.upsert_positions(
                all_mapped_positions, user_id)
            logger.info(
                f"Upserted positions: {position_results} (stocks: {len(mapped_stock_positions)}, crypto: {len(mapped_crypto_positions)})")

            logger.info("Mapping and saving stock orders...")
            mapped_stock_orders = map_orders(raw_orders, user_id)

            logger.info("Mapping and saving crypto orders...")
            mapped_crypto_orders = map_crypto_orders(
                raw_crypto_orders, user_id)

            # Combine all orders
            all_mapped_orders = mapped_stock_orders + mapped_crypto_orders
            order_results = model_manager.upsert_orders(
                all_mapped_orders, user_id)
            logger.info(
                f"Upserted orders: {order_results} (stocks: {len(mapped_stock_orders)}, crypto: {len(mapped_crypto_orders)})")

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
            f"Stock Positions: {len(mapped_stock_positions)} successfully mapped")
        validation_logger.info(
            f"Crypto Positions: {len(mapped_crypto_positions)} successfully mapped")
        validation_logger.info(
            f"Stock Orders: {len(mapped_stock_orders)} successfully mapped")
        validation_logger.info(
            f"Crypto Orders: {len(mapped_crypto_orders)} successfully mapped")
        validation_logger.info(
            f"Dividends: {len(mapped_dividends)} successfully mapped")
        validation_logger.info(
            f"Symbols updated: {len(all_symbols) if 'all_symbols' in locals() else 0} (stocks: {len(stock_symbols) if 'stock_symbols' in locals() else 0}, crypto: {len(crypto_symbols) if 'crypto_symbols' in locals() else 0})")
        validation_logger.info("=== End Validation Summary ===")

        logger.info("Robinhood data pull completed successfully")
        return {
            "success": True,
            "message": "Data pulled successfully",
            "positions": {
                "total": len(all_mapped_positions),
                "stocks": len(mapped_stock_positions),
                "crypto": len(mapped_crypto_positions),
                "mapped": all_mapped_positions
            },
            "orders": {
                "total": len(all_mapped_orders),
                "stocks": len(mapped_stock_orders),
                "crypto": len(mapped_crypto_orders),
                "mapped": all_mapped_orders
            },
            "dividends": {
                "total": len(mapped_dividends),
                "mapped": mapped_dividends
            },
            "pull_timestamp": datetime.now().isoformat()
        }

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

        return {"success": False, "error": str(e)}


@router.post("/pull")
async def pull_robinhood_data(
        credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Public endpoint to pull data from Robinhood - for backward compatibility"""
    try:
        result = await pull_robinhood_data_internal(credentials)

        if not result.get('success'):
            raise HTTPException(
                status_code=500, detail=result.get(
                    'error', 'Unknown error'))

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in pull_robinhood_data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", response_model=RobinhoodStatus)
async def get_robinhood_status(
        credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get Robinhood integration status."""
    try:
        settings = await get_robinhood_settings(credentials)
        model_manager = get_model_manager()

        # Get counts from database
        user_id = await get_current_user_id(credentials)
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
            user_id = await get_current_user_id(credentials)
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


RECURRING_SCHEDULES_URL = "https://bonfire.robinhood.com/recurring_schedules/"


async def _fetch_recurring_investments(credentials: HTTPAuthorizationCredentials) -> list:
    """Login to Robinhood and fetch recurring crypto investment schedules."""
    if not ROBIN_STOCKS_AVAILABLE:
        raise HTTPException(status_code=500, detail="robin_stocks library not available")

    settings = await get_robinhood_settings(credentials)
    if not settings.enabled:
        raise HTTPException(status_code=500, detail="Robinhood integration is not enabled")

    # Login (same pattern as pull_robinhood_data_internal)
    try:
        if settings.mfa:
            try:
                await _run_blocking(
                    lambda: r.login(settings.username, settings.password, mfa_code=settings.mfa),
                    timeout=30)
            except Exception:
                await _run_blocking(
                    lambda: r.login(settings.username, settings.password, settings.mfa),
                    timeout=30)
        else:
            await _run_blocking(
                lambda: r.login(settings.username, settings.password),
                timeout=30)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=500, detail="Robinhood login timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Robinhood login failed: {e}")

    # Fetch recurring schedules for crypto
    try:
        schedules = await _run_blocking(
            lambda: request_get(RECURRING_SCHEDULES_URL + "?asset_types=crypto"),
            timeout=30)
        logger.info(f"Fetched {len(schedules) if isinstance(schedules, list) else 'non-list'} recurring schedules")
        return schedules if isinstance(schedules, list) else []
    except asyncio.TimeoutError:
        logger.error("Recurring schedules fetch timed out")
        return []
    except Exception as e:
        logger.error(f"Failed to fetch recurring schedules: {e}")
        return []


@router.get("/recurring-investments")
async def get_recurring_investments(
        credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Fetch all crypto recurring investment schedules from Robinhood."""
    try:
        schedules = await _fetch_recurring_investments(credentials)
        return {"success": True, "data": schedules}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in recurring-investments: {e}")
        return {"success": False, "error": str(e)}


@router.get("/dca-buy")
async def get_dca_buy(
        credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Fetch the BTCI recurring buy amount from Robinhood."""
    try:
        schedules = await _fetch_recurring_investments(credentials)
        # Filter for BTCI schedules
        for s in schedules:
            currency_code = s.get("currency_code", "").upper()
            if currency_code == "BTCI":
                try:
                    amount = float(s.get("amount", 0))
                    schedule_id = s.get("id", "")
                    logger.info(f"Found BTCI recurring buy: amount={amount}, schedule_id={schedule_id}")
                    return {
                        "success": True,
                        "data": {
                            "amount": amount,
                            "schedule_id": schedule_id,
                            "frequency": s.get("frequency", ""),
                            "state": s.get("state", "")
                        }
                    }
                except (ValueError, TypeError) as e:
                    logger.error(f"Failed to parse BTCI amount: {e}")
                    break

        logger.info("No BTCI recurring buy found")
        return {"success": True, "data": {"amount": 0, "schedule_id": None}}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in dca-buy: {e}")
        return {"success": False, "error": str(e)}
