from fastapi import APIRouter, HTTPException, Body
from typing import List, Dict
import os, json, requests
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/dividends", tags=["dividends"])

DIVIDENDS_PATH = os.path.join("public", "data", "dividends.json")
POLYGON_API_KEY = os.environ.get("POLYGON_API_KEY")

# Helper: get all dividends
def get_dividends() -> List[Dict]:
    if not os.path.exists(DIVIDENDS_PATH):
        return []
    try:
        with open(DIVIDENDS_PATH, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading dividends: {e}")
        return []

@router.get("/")
def get_all_dividends() -> List[Dict]:
    """Get all dividends."""
    try:
        return get_dividends()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading dividends: {e}")

@router.get("/received")
def get_received_dividends() -> List[Dict]:
    """Get received dividends only."""
    try:
        dividends = get_dividends()
        # Simple filter for received dividends (state = 'paid')
        received = []
        for d in dividends:
            if d.get('state') == 'paid':
                received.append(d)
        return received
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error filtering dividends: {e}")

@router.get("/past")
def get_past_dividends() -> List[Dict]:
    """Get past dividends only."""
    try:
        dividends = get_dividends()
        today = datetime.now().strftime("%Y-%m-%d")
        
        past = []
        for d in dividends:
            payable_date = d.get('payable_date', '')
            if payable_date and payable_date < today:
                past.append(d)
        
        return past
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error filtering past dividends: {e}")

@router.get("/summary")
def get_dividends_summary() -> Dict:
    """Get dividends summary."""
    try:
        dividends = get_dividends()
        current_year = datetime.now().year
        
        total_this_year = 0.0
        for d in dividends:
            if d.get('state') == 'paid':
                payable_date = d.get('payable_date', '')
                if payable_date and payable_date.startswith(str(current_year)):
                    total_this_year += float(d.get('amount', 0))
        
        return {
            "total_this_year": total_this_year,
            "total_dividends": len(dividends),
            "received_dividends": len([d for d in dividends if d.get('state') == 'paid'])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating summary: {e}")

@router.post("/record")
def record_dividend(data: dict = Body(...)):
    # data: {symbol, payDate, amount}
    if not os.path.exists(DIVIDENDS_PATH):
        dividends = []
    else:
        with open(DIVIDENDS_PATH, 'r') as f:
            dividends = json.load(f)
    
    # Add new dividend to the list
    new_dividend = {
        "id": f"manual-{datetime.now().timestamp()}",
        "symbol": data.get('symbol', ''),
        "amount": data.get('amount', 0.0),
        "record_date": data.get('record_date', ''),
        "payable_date": data.get('payDate', ''),
        "state": "paid",
        "source": "manual"
    }
    dividends.append(new_dividend)
    
    with open(DIVIDENDS_PATH, 'w') as f:
        json.dump(dividends, f, indent=2)
    return {'status': 'ok'} 