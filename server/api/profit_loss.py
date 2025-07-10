from fastapi import APIRouter, Body, HTTPException
from typing import List, Dict
import os, json, requests

router = APIRouter(prefix="/api/profit_loss", tags=["profit_loss"])

PORTFOLIO_PATH = os.path.join("public", "data", "positions.json")
TRADES_PATH = os.path.join("public", "data", "trades.json")
POLYGON_API_KEY = os.environ.get("POLYGON_API_KEY")

# Helper: get all positions
def get_positions():
    if not os.path.exists(PORTFOLIO_PATH):
        return []
    with open(PORTFOLIO_PATH, "r") as f:
        return json.load(f)

# Helper: get all trades
def get_trades():
    if not os.path.exists(TRADES_PATH):
        return []
    with open(TRADES_PATH, "r") as f:
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

@router.get("/summary")
def get_profit_loss_summary() -> Dict:
    positions = get_positions()
    trades = get_trades()
    unrealized = 0.0
    for pos in positions:
        latest = get_latest_price(pos["symbol"])
        if latest is not None:
            unrealized += (latest - pos["buy_price"]) * pos["quantity"]
    realized = sum(t["pl"] for t in trades if "pl" in t)
    total = unrealized + realized
    return {"total": total, "unrealized": unrealized, "realized": realized}

@router.get("/details")
def get_profit_loss_details() -> List[Dict]:
    positions = get_positions()
    trades = get_trades()
    details = []
    for pos in positions:
        latest = get_latest_price(pos["symbol"])
        if latest is not None:
            pl = (latest - pos["buy_price"]) * pos["quantity"]
            details.append({"symbol": pos["symbol"], "type": "Unrealized", "amount": pl})
    for t in trades:
        details.append({"symbol": t["symbol"], "type": "Realized", "amount": t.get("pl", 0.0)})
    return details

@router.post("/record_trade")
def record_trade(data: dict = Body(...)):
    # data: {symbol, quantity, buy_price, sell_price, pl}
    if not os.path.exists(TRADES_PATH):
        trades = []
    else:
        with open(TRADES_PATH, 'r') as f:
            trades = json.load(f)
    trades.append(data)
    with open(TRADES_PATH, 'w') as f:
        json.dump(trades, f, indent=2)
    return {'status': 'ok'} 