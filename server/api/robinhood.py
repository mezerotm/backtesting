from fastapi import APIRouter, HTTPException
import os
import json
import robin_stocks.robinhood as r
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional

PORTFOLIO_PATH = os.path.join("public", "data", "portfolio.json")
POSITIONS_PATH = os.path.join("public", "data", "positions.json")
ORDERS_PATH = os.path.join("public", "data", "orders.json")
DIVIDENDS_PATH = os.path.join("public", "data", "dividends.json")
SYMBOLS_PATH = os.path.join("public", "data", "symbols.json")
POLYGON_API_KEY = os.environ.get("POLYGON_API_KEY")

router = APIRouter(prefix="/api/robinhood", tags=["robinhood"])

# Ensure data directory exists
os.makedirs(os.path.dirname(SYMBOLS_PATH), exist_ok=True)

# Persistent symbol cache
if os.path.exists(SYMBOLS_PATH):
    with open(SYMBOLS_PATH, "r", encoding="utf-8") as f:
        _symbol_cache = json.load(f)
else:
    _symbol_cache = {}
    with open(SYMBOLS_PATH, "w", encoding="utf-8") as f:
        json.dump(_symbol_cache, f, indent=2)

def save_symbol_cache():
    with open(SYMBOLS_PATH, "w", encoding="utf-8") as f:
        json.dump(_symbol_cache, f, indent=2)

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
    if not instrument_url:
        return None
    if instrument_url in _symbol_cache:
        return _symbol_cache[instrument_url]
    try:
        # Use the correct robin_stocks function to get instrument data by URL
        instrument_data = r.get_instrument_by_url(instrument_url)
        if instrument_data and 'symbol' in instrument_data:
            symbol = instrument_data['symbol']
            _symbol_cache[instrument_url] = symbol
            save_symbol_cache()
            print(f"[DEBUG] Cached symbol {symbol} for instrument {instrument_url}")
            return symbol
        print(f"[DEBUG] Could not resolve symbol for instrument {instrument_url}")
        return None
    except Exception as e:
        logging.error(f"[Robinhood] Error resolving symbol for {instrument_url}: {e}")
        return None

def map_dividends(raw_dividends):
    mapped = []
    for d in raw_dividends:
        symbol = resolve_symbol_from_instrument(d.get('instrument', '')) or ''
        mapped.append({
            'id': d.get('id'),
            'symbol': symbol,
            'amount': float(d.get('amount', 0)),
            'rate': float(d.get('rate', 0)),
            'position': float(d.get('position', 0)),
            'withholding': float(d.get('withholding', 0)),
            'record_date': d.get('record_date'),
            'payable_date': d.get('payable_date'),
            'state': d.get('state'),
            'source': 'robinhood'
        })
    print(f"[DEBUG] Mapped {len(mapped)} dividends.")
    return mapped

def map_positions(raw_positions):
    mapped = []
    for i, (symbol, pos) in enumerate(raw_positions.items(), 1):
        mapped.append({
            'id': i,
            'symbol': symbol,
            'quantity': float(pos.get('quantity', 0)),
            'buy_price': float(pos.get('average_buy_price', 0)),
            'notes': pos.get('name', ''),
            'source': 'robinhood'
        })
    print(f"[DEBUG] Mapped {len(mapped)} positions.")
    return mapped

def map_orders(raw_orders):
    orders = []
    order_id_counter = 1
    for order in raw_orders:
        try:
            if order.get('type') not in ('market', 'limit'):
                logging.info(f"[ORDERS] Skipping order {order.get('id', '')}: type {order.get('type')} not market/limit.")
                continue
            instrument_url = order.get('instrument')
            if not instrument_url:
                logging.warning(f"[ORDERS] Skipping order {order.get('id', '')}: missing instrument URL.")
                continue
            symbol = resolve_symbol_from_instrument(instrument_url)
            if not symbol:
                logging.warning(f"[ORDERS] Skipping order {order.get('id', '')}: could not resolve symbol for instrument {instrument_url}.")
                continue
            side = order.get('side', 'buy')
            order_id = order.get('id', '')
            executions = order.get('executions', [])
            if not executions:
                logging.info(f"[ORDERS] Skipping order {order_id}: no executions present.")
                continue
            for execution in executions:
                try:
                    mapped_order = {
                        'id': order_id_counter,
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
                        'notes': f'Robinhood order: {order_id}',
                        'source': 'robinhood'
                    }
                    orders.append(mapped_order)
                    logging.info(f"[ORDERS] Mapped order: {mapped_order}")
                    order_id_counter += 1
                except Exception as e:
                    logging.error(f"[ORDERS] Error mapping execution in order {order_id}: {e}")
                    continue
        except Exception as e:
            logging.error(f"[ORDERS] Error processing order: {e}")
            continue
    logging.info(f"[ORDERS] Mapped {len(orders)} orders in total.")
    return orders

@router.post("/pull")
def pull_robinhood_data():
    settings = get_robinhood_settings()
    if not settings["enabled"]:
        raise HTTPException(status_code=400, detail="Robinhood integration is not enabled.")
    if not settings["username"] or not settings["password"]:
        raise HTTPException(status_code=400, detail="Robinhood credentials are missing.")
    try:
        # Ensure all data files exist (create empty if missing)
        for path in [DIVIDENDS_PATH, POSITIONS_PATH, ORDERS_PATH]:
            if not os.path.exists(path):
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump([], f)
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
        raw_orders = r.orders.get_all_stock_orders()
        dividends = r.account.get_dividends()
        
        # Map and save data directly
        mapped_positions = map_positions(positions)
        mapped_orders = map_orders(raw_orders)
        mapped_dividends = map_dividends(dividends)
        
        # Save all data
        with open(POSITIONS_PATH, 'w', encoding='utf-8') as f:
            json.dump(mapped_positions, f, indent=2)
        with open(ORDERS_PATH, 'w', encoding='utf-8') as f:
            json.dump(mapped_orders, f, indent=2)
        with open(DIVIDENDS_PATH, 'w', encoding='utf-8') as f:
            json.dump(mapped_dividends, f, indent=2)
        
        # Refresh P/L cache with new data
        try:
            from server.api.profit_loss import calculate_all_periods
            calculate_all_periods()
            logging.info("[ROBINHOOD] P/L cache refreshed with new data")
        except Exception as e:
            logging.warning(f"[ROBINHOOD] Failed to refresh P/L cache: {e}")
        
        # Logout
        r.logout()
        return {
            "status": "success",
            "positions_count": len(mapped_positions),
            "orders_count": len(mapped_orders),
            "dividends_count": len(mapped_dividends),
            "message": f"Successfully pulled and mapped {len(mapped_positions)} positions, {len(mapped_orders)} orders, {len(mapped_dividends)} dividends"
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
            "orders_count": len(json.load(open(ORDERS_PATH, 'r')) if os.path.exists(ORDERS_PATH) else []),
            "dividends_count": len(json.load(open(DIVIDENDS_PATH, 'r')) if os.path.exists(DIVIDENDS_PATH) else []),
        }
        
    except Exception as e:
        logging.error(f"[Robinhood] Error getting status: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting status: {e}") 