import json
import os
from server.api import robinhood

RAW_PATH = os.path.join('public', 'data', 'robinhood_raw.json')
DIVIDENDS_PATH = os.path.join('public', 'data', 'dividends.json')
TRADES_PATH = os.path.join('public', 'data', 'trades.json')
POSITIONS_PATH = os.path.join('public', 'data', 'positions.json')

# Helper to resolve symbol from instrument URL
resolve_symbol = robinhood.resolve_symbol_from_instrument

def map_dividends(raw_dividends):
    mapped = []
    for d in raw_dividends:
        symbol = resolve_symbol(d.get('instrument', '')) or ''
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
    return mapped

def map_positions(raw_positions):
    # raw_positions is a dict of symbol -> data
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
    return mapped

def map_trades(raw_orders):
    trades = []
    trade_id_counter = 1
    for order in raw_orders:
        try:
            if order.get('type') not in ('market', 'limit'):
                continue
            instrument_url = order.get('instrument')
            if not instrument_url:
                continue
            symbol = resolve_symbol(instrument_url)
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
                        'id': trade_id_counter,
                        'symbol': symbol,
                        'type': side,
                        'quantity': float(execution.get('quantity', 0)),
                        'price': float(execution.get('price', 0)),
                        'date': execution.get('timestamp', ''),
                        'fees': total_fees,
                        'pl': 0.0,
                        'notes': f'Robinhood order: {order_id}',
                        'source': 'robinhood'
                    }
                    trades.append(trade)
                    trade_id_counter += 1
                except Exception:
                    continue
        except Exception:
            continue
    return trades

def main():
    with open(RAW_PATH, 'r', encoding='utf-8') as f:
        raw = json.load(f)
    raw_dividends = raw.get('dividends', [])
    raw_positions = raw.get('positions', {})
    raw_orders = raw.get('orders', [])
    
    dividends = map_dividends(raw_dividends)
    positions = map_positions(raw_positions)
    trades = map_trades(raw_orders)
    
    with open(DIVIDENDS_PATH, 'w', encoding='utf-8') as f:
        json.dump(dividends, f, indent=2)
    with open(POSITIONS_PATH, 'w', encoding='utf-8') as f:
        json.dump(positions, f, indent=2)
    with open(TRADES_PATH, 'w', encoding='utf-8') as f:
        json.dump(trades, f, indent=2)
    print(f"Wrote {len(dividends)} dividends, {len(positions)} positions, {len(trades)} trades.")

if __name__ == '__main__':
    main() 