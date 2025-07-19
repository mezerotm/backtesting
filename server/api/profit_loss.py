from fastapi import APIRouter, Body, HTTPException
from typing import List, Dict
import os, json, requests

router = APIRouter(prefix="/api/profit_loss", tags=["profit_loss"])

PORTFOLIO_PATH = os.path.join("public", "data", "positions.json")
ORDERS_PATH = os.path.join("public", "data", "orders.json")
POLYGON_API_KEY = os.environ.get("POLYGON_API_KEY")

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

# Helper: fetch latest price from Polygon
def get_latest_price(symbol):
    if not POLYGON_API_KEY:
        return None
    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/prev"
    params = {"adjusted": "true", "apiKey": POLYGON_API_KEY}
    resp = requests.get(url, params=params)
    if resp.status_code != 200:
        return None
    data = resp.json()
    results = data.get("results", [])
    if not results:
        return None
    return results[0]["c"]

# Helper: calculate realized P/L from orders
def calculate_realized_pl(orders):
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

@router.get("/summary")
def get_profit_loss_summary() -> Dict:
    positions = get_positions()
    orders = get_orders()
    
    # Calculate unrealized P/L from current positions
    unrealized = 0.0
    for pos in positions:
        latest = get_latest_price(pos["symbol"])
        if latest is not None:
            unrealized += (latest - pos["buy_price"]) * pos["quantity"]
    
    # Calculate realized P/L from orders
    realized = calculate_realized_pl(orders)
    
    total = unrealized + realized
    return {"total": total, "unrealized": unrealized, "realized": realized}

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