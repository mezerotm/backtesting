from fastapi import APIRouter, Body, HTTPException
from typing import List, Dict
from datetime import date, datetime, timedelta
import os, json, requests

router = APIRouter(prefix="/api/dividends", tags=["dividends"])

PORTFOLIO_PATH = os.path.join("public", "data", "positions.json")
DIVIDENDS_PATH = os.path.join("public", "data", "dividends.json")
UPCOMING_DIVIDENDS_PATH = os.path.join("public", "data", "upcoming-dividends.json")
POLYGON_API_KEY = os.environ.get("POLYGON_API_KEY")

# Helper: get all unique symbols in portfolio
def get_portfolio_symbols():
    if not os.path.exists(PORTFOLIO_PATH):
        return []
    with open(PORTFOLIO_PATH, "r") as f:
        positions = json.load(f)
    return list({p['symbol'] for p in positions if 'symbol' in p})

# Helper: fetch upcoming dividends from Polygon API and save to file
def update_upcoming_dividends():
    if not POLYGON_API_KEY:
        print("[DIVIDENDS] No Polygon API key found, skipping upcoming dividends update")
        return
    
    portfolio_symbols = get_portfolio_symbols()
    if not portfolio_symbols:
        print("[DIVIDENDS] No portfolio symbols found")
        return
    
    upcoming_dividends = []
    today = datetime.now()
    # Look back 30 days and forward 90 days to catch recently announced dividends
    start_date = today - timedelta(days=30)
    end_date = today + timedelta(days=90)
    
    print(f"[DIVIDENDS] Fetching recently announced dividends for {len(portfolio_symbols)} symbols...")
    print(f"[DIVIDENDS] Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    
    # Test with known dividend-paying stocks first
    test_symbols = ["JEPI", "JEPQ", "SPY", "VOO", "QQQ"] + portfolio_symbols
    test_symbols = list(dict.fromkeys(test_symbols))  # Remove duplicates while preserving order
    
    for symbol in test_symbols:
        try:
            # Polygon Dividends API endpoint - get recently announced dividends
            url = f"https://api.polygon.io/v3/reference/dividends"
            params = {
                "ticker": symbol,
                "ex_dividend_date.gte": start_date.strftime("%Y-%m-%d"),
                "ex_dividend_date.lte": end_date.strftime("%Y-%m-%d"),
                "apiKey": POLYGON_API_KEY
            }
            
            print(f"[DIVIDENDS] Fetching dividends for {symbol}...")
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('results'):
                    for dividend in data['results']:
                        # Only include dividends with future pay dates
                        pay_date = dividend.get('pay_date', '')
                        if pay_date and pay_date >= today.strftime("%Y-%m-%d"):
                            upcoming_dividends.append({
                                "symbol": symbol,
                                "record_date": dividend.get('ex_dividend_date', ''),
                                "payable_date": dividend.get('pay_date', ''),
                                "amount": dividend.get('cash_amount', 0.0),
                                "source": "robinhood"  # Source as robinhood to maintain correlation
                            })
                    print(f"[DIVIDENDS] Found {len(data['results'])} total dividends for {symbol}, {len([d for d in data['results'] if d.get('pay_date', '') >= today.strftime('%Y-%m-%d')])} upcoming")
                else:
                    print(f"[DIVIDENDS] No dividends found for {symbol}")
            else:
                print(f"[DIVIDENDS] Polygon API error for {symbol}: {response.status_code}")
                print(f"[DIVIDENDS] Error response: {response.text}")
                
        except Exception as e:
            print(f"[DIVIDENDS] Error fetching dividends for {symbol}: {e}")
            continue
    
    # Save to upcoming-dividends.json
    with open(UPCOMING_DIVIDENDS_PATH, 'w') as f:
        json.dump(upcoming_dividends, f, indent=2)
    
    print(f"[DIVIDENDS] Saved {len(upcoming_dividends)} upcoming dividends to {UPCOMING_DIVIDENDS_PATH}")
    print(f"[DIVIDENDS] Note: Polygon API only provides recently announced dividends, not future unannounced dividends")

@router.get("/upcoming")
def get_upcoming_dividends() -> List[Dict]:
    # First get Robinhood upcoming dividends (if any)
    robinhood_upcoming = []
    if os.path.exists(DIVIDENDS_PATH):
        with open(DIVIDENDS_PATH, "r") as f:
            dividends = json.load(f)
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        for d in dividends:
            # Only include dividends with future payable dates and valid states
            if (d.get('payable_date') and 
                d.get('payable_date') >= today and 
                d.get('state') in ['paid', 'reinvested']):
                robinhood_upcoming.append({
                    "symbol": d.get('symbol', ''),
                    "record_date": d.get('record_date', ''),
                    "payable_date": d.get('payable_date', ''),
                    "amount": d.get('amount', 0.0),
                    "source": d.get('source', 'robinhood')
                })
    
    # Then get saved upcoming dividends from file
    polygon_upcoming = []
    if os.path.exists(UPCOMING_DIVIDENDS_PATH):
        with open(UPCOMING_DIVIDENDS_PATH, "r") as f:
            polygon_upcoming = json.load(f)
    
    # Combine and deduplicate (prefer Robinhood data if available)
    all_upcoming = robinhood_upcoming + polygon_upcoming
    
    # Remove duplicates based on symbol and payable_date
    seen = set()
    unique_upcoming = []
    for dividend in all_upcoming:
        key = (dividend['symbol'], dividend['payable_date'])
        if key not in seen:
            seen.add(key)
            unique_upcoming.append(dividend)
    
    # Sort by payable date
    unique_upcoming.sort(key=lambda x: x.get('payable_date', ''))
    return unique_upcoming

@router.get("/past")
def get_past_dividends() -> List[Dict]:
    if not os.path.exists(DIVIDENDS_PATH):
        return []
    with open(DIVIDENDS_PATH, "r") as f:
        dividends = json.load(f)
    
    today = datetime.now().strftime("%Y-%m-%d")
    past = []
    
    for d in dividends:
        # Only include dividends with past payable dates and valid states
        if (d.get('payable_date') and 
            d.get('payable_date') < today and 
            d.get('state') in ['paid', 'reinvested']):
            past.append({
                "symbol": d.get('symbol', ''),
                "record_date": d.get('record_date', ''),
                "payable_date": d.get('payable_date', ''),
                "amount": d.get('amount', 0.0),
                "source": d.get('source', 'robinhood')
            })
    
    # Sort by payable date (newest first)
    past.sort(key=lambda x: x.get('payable_date', ''), reverse=True)
    return past

@router.get("/summary")
def get_dividends_summary() -> Dict:
    if not os.path.exists(DIVIDENDS_PATH):
        return {"total": 0.0}
    with open(DIVIDENDS_PATH, "r") as f:
        dividends = json.load(f)
    
    year = datetime.now().year
    total = sum(
        d.get('amount', 0.0) for d in dividends 
        if (d.get('payable_date') and 
            str(year) in d.get('payable_date', '') and
            d.get('state') in ['paid', 'reinvested'])
    )
    return {"total": total}

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