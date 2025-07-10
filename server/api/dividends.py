from fastapi import APIRouter, Body, HTTPException
from typing import List, Dict
from datetime import date, datetime
import os, json, requests

router = APIRouter(prefix="/api/dividends", tags=["dividends"])

PORTFOLIO_PATH = os.path.join("public", "data", "positions.json")
TRADES_PATH = os.path.join("public", "data", "trades.json")
POLYGON_API_KEY = os.environ.get("POLYGON_API_KEY")

# Helper: get all unique symbols in portfolio
def get_portfolio_symbols():
    if not os.path.exists(PORTFOLIO_PATH):
        return []
    with open(PORTFOLIO_PATH, "r") as f:
        positions = json.load(f)
    return list({p['symbol'] for p in positions if 'symbol' in p})

@router.get("/upcoming")
def get_upcoming_dividends() -> List[Dict]:
    if not POLYGON_API_KEY:
        raise HTTPException(status_code=500, detail="Polygon API key not set")
    symbols = get_portfolio_symbols()
    results = []
    for symbol in symbols:
        url = f"https://api.polygon.io/v3/reference/dividends"
        params = {"ticker": symbol, "apiKey": POLYGON_API_KEY, "limit": 3, "order": "desc"}
        resp = requests.get(url, params=params)
        if resp.status_code != 200:
            continue
        data = resp.json()
        for d in data.get("results", []):
            # Only include future pay dates
            pay_date = d.get("pay_date")
            if pay_date and pay_date >= datetime.now().strftime("%Y-%m-%d"):
                results.append({
                    "symbol": symbol,
                    "exDate": d.get("ex_dividend_date"),
                    "payDate": d.get("pay_date"),
                    "amount": d.get("cash_amount", 0.0)
                })
    return results

# Use trades.json for past dividends
@router.get("/past")
def get_past_dividends() -> List[Dict]:
    if not os.path.exists(TRADES_PATH):
        return []
    with open(TRADES_PATH, "r") as f:
        trades = json.load(f)
    return [t for t in trades if t.get("type") == "dividend"]

@router.get("/summary")
def get_dividends_summary() -> Dict:
    if not os.path.exists(TRADES_PATH):
        return {"total": 0.0}
    with open(TRADES_PATH, "r") as f:
        trades = json.load(f)
    year = datetime.now().year
    total = sum(t["amount"] for t in trades if t.get("type") == "dividend" and str(year) in t.get("payDate", ""))
    return {"total": total}

@router.post("/record")
def record_dividend(data: dict = Body(...)):
    # data: {symbol, payDate, amount}
    if not os.path.exists(TRADES_PATH):
        trades = []
    else:
        with open(TRADES_PATH, 'r') as f:
            trades = json.load(f)
    data["type"] = "dividend"
    trades.append(data)
    with open(TRADES_PATH, 'w') as f:
        json.dump(trades, f, indent=2)
    return {'status': 'ok'} 