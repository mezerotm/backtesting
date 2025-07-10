from fastapi import APIRouter, Body, HTTPException
from typing import List, Dict
import os, json

router = APIRouter(prefix="/api/trades", tags=["trades"])
TRADES_PATH = os.path.join("public", "data", "trades.json")

# Helper: load/save trades
def load_trades():
    if not os.path.exists(TRADES_PATH):
        return []
    with open(TRADES_PATH, "r") as f:
        return json.load(f)

def save_trades(trades):
    with open(TRADES_PATH, "w") as f:
        json.dump(trades, f, indent=2)

@router.get("")
def get_trades() -> List[Dict]:
    return load_trades()

@router.post("")
def add_trade(trade: dict = Body(...)):
    trades = load_trades()
    trade["id"] = trade.get("id") or (max([t["id"] for t in trades], default=0) + 1)
    trades.append(trade)
    save_trades(trades)
    return {"status": "ok", "id": trade["id"]}

@router.put("/{trade_id}")
def edit_trade(trade_id: int, trade: dict = Body(...)):
    trades = load_trades()
    for i, t in enumerate(trades):
        if t["id"] == trade_id:
            trade["id"] = trade_id
            trades[i] = trade
            save_trades(trades)
            return {"status": "ok"}
    raise HTTPException(status_code=404, detail="Trade not found")

@router.delete("/{trade_id}")
def delete_trade(trade_id: int):
    trades = load_trades()
    new_trades = [t for t in trades if t["id"] != trade_id]
    if len(new_trades) == len(trades):
        raise HTTPException(status_code=404, detail="Trade not found")
    save_trades(new_trades)
    return {"status": "ok"} 