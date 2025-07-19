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