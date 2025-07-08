from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import json
import os
from pydantic import BaseModel
from fastapi.responses import JSONResponse
import requests

PORTFOLIO_PATH = os.path.join("public", "portfolio", "positions.json")
POLYGON_API_KEY = os.environ.get("POLYGON_API_KEY")

class Position(BaseModel):
    id: int
    symbol: str
    quantity: float
    buy_price: float
    buy_date: str  # ISO date string
    notes: Optional[str] = None

def load_positions() -> List[dict]:
    if not os.path.exists(PORTFOLIO_PATH):
        return []
    with open(PORTFOLIO_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_positions(positions: List[dict]):
    with open(PORTFOLIO_PATH, "w", encoding="utf-8") as f:
        json.dump(positions, f, indent=2)

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