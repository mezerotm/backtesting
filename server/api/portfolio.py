from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import json
import os
from pydantic import BaseModel
from fastapi.responses import JSONResponse
import requests

# NOTE: This file is backend-only. Do NOT mount public/data as a static folder unless browser access is required.
PORTFOLIO_PATH = os.path.join("public", "data", "positions.json")
PORTFOLIO_CASH_PATH = os.path.join("public", "data", "portfolio.json")
POLYGON_API_KEY = os.environ.get("POLYGON_API_KEY")

class Position(BaseModel):
    id: int
    symbol: str
    quantity: float
    buy_price: float
    notes: Optional[str] = None

def load_positions() -> List[dict]:
    if not os.path.exists(PORTFOLIO_PATH):
        return []
    with open(PORTFOLIO_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_positions(positions: List[dict]):
    with open(PORTFOLIO_PATH, "w", encoding="utf-8") as f:
        json.dump(positions, f, indent=2)

# --- Portfolio Cash, BTC, and BTC Avg Buy Price Logic ---
def load_portfolio_cash_btc() -> dict:
    if not os.path.exists(PORTFOLIO_CASH_PATH):
        return {
            "total_portfolio_cash": 0.0,
            "total_portfolio_btc": 0.0,
            "btc_avg_buy_price": 0.0,
            "robinhood_enabled": False,
            "robinhood_display": False,
            "robinhood_username": "",
            "robinhood_password": "",
            "robinhood_mfa": ""
        }
    with open(PORTFOLIO_CASH_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
        # Set defaults for new fields if missing
        if "total_portfolio_btc" not in data:
            data["total_portfolio_btc"] = 0.0
        if "btc_avg_buy_price" not in data:
            data["btc_avg_buy_price"] = 0.0
        if "robinhood_enabled" not in data:
            data["robinhood_enabled"] = False
        if "robinhood_display" not in data:
            data["robinhood_display"] = False
        if "robinhood_username" not in data:
            data["robinhood_username"] = ""
        if "robinhood_password" not in data:
            data["robinhood_password"] = ""
        if "robinhood_mfa" not in data:
            data["robinhood_mfa"] = ""
        return data

def save_portfolio_cash_btc(data: dict):
    # Always write all fields, including new Robinhood settings
    out = {
        "total_portfolio_cash": float(data.get("total_portfolio_cash", 0.0)),
        "total_portfolio_btc": float(data.get("total_portfolio_btc", 0.0)),
        "btc_avg_buy_price": float(data.get("btc_avg_buy_price", 0.0)),
        "robinhood_enabled": bool(data.get("robinhood_enabled", False)),
        "robinhood_display": bool(data.get("robinhood_display", False)),
        "robinhood_username": data.get("robinhood_username", ""),
        "robinhood_password": data.get("robinhood_password", ""),
        "robinhood_mfa": data.get("robinhood_mfa", "")
    }
    with open(PORTFOLIO_CASH_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])

@router.get("/", response_model=List[Position])
def get_positions():
    return load_positions()

@router.post("/", response_model=Position)
def add_position(pos: Position):
    positions = load_positions()
    if any(p["id"] == pos.id for p in positions):
        raise HTTPException(status_code=400, detail="ID already exists")
    positions.append(pos.dict())
    save_positions(positions)
    return pos

@router.put("/{pos_id}", response_model=Position)
def update_position(pos_id: int, pos: Position):
    positions = load_positions()
    for i, p in enumerate(positions):
        if p["id"] == pos_id:
            positions[i] = pos.dict()
            save_positions(positions)
            return pos
    raise HTTPException(status_code=404, detail="Position not found")

@router.delete("/{pos_id}")
def delete_position(pos_id: int):
    positions = load_positions()
    new_positions = [p for p in positions if p["id"] != pos_id]
    if len(new_positions) == len(positions):
        raise HTTPException(status_code=404, detail="Position not found")
    save_positions(new_positions)
    return JSONResponse(content={"detail": "Deleted"})

@router.get("/search-symbols")
def search_symbols(query: str = Query(..., min_length=1)):
    """Search for symbols using Polygon.io's ticker search API."""
    if not POLYGON_API_KEY:
        raise HTTPException(status_code=500, detail="Polygon API key not set")
    url = f"https://api.polygon.io/v3/reference/tickers"
    params = {
        "search": query,
        "active": "true",
        "apiKey": POLYGON_API_KEY,
        "limit": 10
    }
    resp = requests.get(url, params=params)
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Polygon API error: {resp.text}")
    data = resp.json()
    # Return a list of {symbol, name}
    results = [
        {"symbol": t["ticker"], "name": t.get("name", "")} for t in data.get("results", [])
    ]
    return results

@router.get("/latest-price/{symbol}")
def get_latest_price(symbol: str):
    """Fetch the latest close price for a symbol using Polygon.io aggregates."""
    if not POLYGON_API_KEY:
        raise HTTPException(status_code=500, detail="Polygon API key not set")
    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/prev"
    params = {"adjusted": "true", "apiKey": POLYGON_API_KEY}
    resp = requests.get(url, params=params)
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Polygon API error: {resp.text}")
    data = resp.json()
    results = data.get("results", [])
    if not results:
        raise HTTPException(status_code=404, detail="No price data found")
    return {"price": results[0]["c"]}

@router.get("/settings")
def get_portfolio_settings():
    """
    Get the total portfolio cash, BTC (dollar value), BTC avg buy price, and Robinhood settings from portfolio.json.
    Returns: {"total_portfolio_cash": float, "total_portfolio_btc": float, "btc_avg_buy_price": float, ...robinhood fields...}
    """
    return load_portfolio_cash_btc()

@router.post("/settings")
def set_portfolio_settings(data: dict):
    """
    Set the total portfolio cash, BTC (dollar value), BTC avg buy price, and Robinhood settings in portfolio.json.
    Accepts any of: {"total_portfolio_cash": float, "total_portfolio_btc": float, "btc_avg_buy_price": float, ...robinhood fields...}
    """
    current = load_portfolio_cash_btc()
    if "total_portfolio_cash" in data:
        try:
            current["total_portfolio_cash"] = float(data["total_portfolio_cash"] or 0)
        except (ValueError, TypeError):
            current["total_portfolio_cash"] = 0.0
    if "total_portfolio_btc" in data:
        try:
            current["total_portfolio_btc"] = float(data["total_portfolio_btc"] or 0)
        except (ValueError, TypeError):
            current["total_portfolio_btc"] = 0.0
    if "btc_avg_buy_price" in data:
        try:
            current["btc_avg_buy_price"] = float(data["btc_avg_buy_price"] or 0)
        except (ValueError, TypeError):
            current["btc_avg_buy_price"] = 0.0
    # Robinhood settings
    if "robinhood_enabled" in data:
        current["robinhood_enabled"] = bool(data["robinhood_enabled"])
    if "robinhood_display" in data:
        current["robinhood_display"] = bool(data["robinhood_display"])
    if "robinhood_username" in data:
        current["robinhood_username"] = data["robinhood_username"] or ""
    if "robinhood_password" in data:
        current["robinhood_password"] = data["robinhood_password"] or ""
    if "robinhood_mfa" in data:
        current["robinhood_mfa"] = data["robinhood_mfa"] or ""
    save_portfolio_cash_btc(current)
    return {"status": "ok"}

@router.get("/cash")
def get_portfolio_cash():
    """
    Get the total portfolio cash, BTC (dollar value), and BTC avg buy price from portfolio.json.
    Returns: {"total_portfolio_cash": float, "total_portfolio_btc": float, "btc_avg_buy_price": float}
    """
    return load_portfolio_cash_btc()

@router.post("/cash")
def set_portfolio_cash(data: dict):
    """
    Set the total portfolio cash, BTC (dollar value), and/or BTC avg buy price in portfolio.json.
    Accepts any of: {"total_portfolio_cash": float, "total_portfolio_btc": float, "btc_avg_buy_price": float}
    """
    # Load current, update only provided fields
    current = load_portfolio_cash_btc()
    if "total_portfolio_cash" in data:
        current["total_portfolio_cash"] = float(data["total_portfolio_cash"])
    if "total_portfolio_btc" in data:
        current["total_portfolio_btc"] = float(data["total_portfolio_btc"])
    if "btc_avg_buy_price" in data:
        current["btc_avg_buy_price"] = float(data["btc_avg_buy_price"])
    save_portfolio_cash_btc(current)
    return {"status": "ok"}

@router.get("/btc")
def get_portfolio_btc():
    """Get the total portfolio BTC value from portfolio.json."""
    return {"total_portfolio_btc": load_portfolio_cash_btc().get("total_portfolio_btc", 0.0)}

@router.post("/btc")
def set_portfolio_btc(data: dict):
    """Set the total portfolio BTC value in portfolio.json. Accepts {"total_portfolio_btc": float}."""
    if "total_portfolio_btc" not in data:
        raise HTTPException(status_code=400, detail="Missing total_portfolio_btc field")
    current = load_portfolio_cash_btc()
    current["total_portfolio_btc"] = float(data["total_portfolio_btc"])
    save_portfolio_cash_btc(current)
    return {"status": "ok"} 