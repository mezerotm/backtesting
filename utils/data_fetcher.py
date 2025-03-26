import pandas as pd
from polygon import RESTClient
from datetime import datetime, timedelta
import sys
import os
import time
import json

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import config

# Cache configuration
_CACHE_DURATION = 30 * 60  # 30 minutes in seconds
_CACHE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'public', 'data_cache.json')

def get_polygon_client():
    """Initialize and return a Polygon REST client."""
    return RESTClient(api_key=config.POLYGON_API_KEY)

def _get_cache_key(ticker, start_date, end_date, timeframe):
    """Generate a unique cache key based on request parameters."""
    return f"{ticker}_{start_date}_{end_date}_{timeframe}"

def _load_cache():
    """Load cache from file."""
    try:
        if os.path.exists(_CACHE_FILE):
            with open(_CACHE_FILE, 'r') as f:
                return json.load(f)
        else:
            return {}
    except Exception as e:
        print(f"Error loading cache file: {e}")
        return {}

def _save_cache(cache_data):
    """Save cache to file."""
    try:
        # Ensure public directory exists
        cache_dir = os.path.dirname(_CACHE_FILE)
        os.makedirs(cache_dir, exist_ok=True)
        
        # Convert DataFrame to dictionary for JSON serialization
        serializable_cache = {}
        for key, entry in cache_data.items():
            if 'data' in entry and isinstance(entry['data'], pd.DataFrame):
                # Convert DataFrame to JSON
                serializable_cache[key] = {
                    'timestamp': entry['timestamp'],
                    'data': entry['data'].to_json(orient='split', date_format='iso'),
                    'parameters': entry.get('parameters', {})
                }
            else:
                serializable_cache[key] = entry
        
        with open(_CACHE_FILE, 'w') as f:
            json.dump(serializable_cache, f)
    except Exception as e:
        print(f"Error saving cache to file: {e}")

def _is_cache_valid(cache_data, cache_key):
    """Check if cache entry exists and is still valid."""
    if cache_key not in cache_data:
        return False
    
    cache_entry = cache_data[cache_key]
    cache_time = cache_entry['timestamp']
    current_time = time.time()
    
    # Check if cache is still valid (less than CACHE_DURATION old)
    return current_time - cache_time < _CACHE_DURATION

def fetch_historical_data(ticker, start_date, end_date, timeframe="1d"):
    """
    Fetch historical OHLCV data from Polygon API.
    
    Parameters:
        ticker (str): Stock symbol
        start_date (str): Start date in YYYY-MM-DD format
        end_date (str): End date in YYYY-MM-DD format
        timeframe (str): Time interval (e.g., '1d' for daily)
        
    Returns:
        pandas.DataFrame: OHLCV data formatted for backtesting.py
    """
    # Generate cache key for this request
    cache_key = _get_cache_key(ticker, start_date, end_date, timeframe)
    
    # Use cache in development environment if available and valid
    if config.ENV == 'development':
        # Load cache from file
        cache_data = _load_cache()
        
        if _is_cache_valid(cache_data, cache_key):
            print(f"Using cached data for {ticker} from {start_date} to {end_date} ({timeframe})")
            # Convert cached JSON back to DataFrame
            cached_json = cache_data[cache_key]['data']
            return pd.read_json(cached_json, orient='split')
    
    # If we reach here, we need to fetch data from the API
    client = get_polygon_client()
    
    # Convert timeframe to Polygon format
    multiplier, timespan = parse_timeframe(timeframe)
    
    # Fetch data from Polygon
    aggs = client.get_aggs(
        ticker=ticker,
        multiplier=multiplier,
        timespan=timespan,
        from_=start_date,
        to=end_date,
        limit=50000
    )
    
    # Convert to DataFrame
    data = []
    for agg in aggs:
        data.append({
            'Date': datetime.fromtimestamp(agg.timestamp / 1000),
            'Open': agg.open,
            'High': agg.high,
            'Low': agg.low,
            'Close': agg.close,
            'Volume': agg.volume
        })
    
    df = pd.DataFrame(data)
    
    # Format for backtesting.py
    df.set_index('Date', inplace=True)
    df.index = pd.to_datetime(df.index)
    
    # Sort by date
    df.sort_index(inplace=True)
    
    # Store in cache if in development mode
    if config.ENV == 'development':
        # Load existing cache
        cache_data = _load_cache()
        
        # Update with new data
        cache_data[cache_key] = {
            'timestamp': time.time(),
            'data': df,
            'parameters': {
                'ticker': ticker,
                'start_date': start_date,
                'end_date': end_date,
                'timeframe': timeframe
            }
        }
        
        # Save updated cache
        _save_cache(cache_data)
        print(f"Cached data for {ticker} from {start_date} to {end_date} ({timeframe})")
    
    return df

def parse_timeframe(timeframe):
    """Parse timeframe string into multiplier and timespan for Polygon API."""
    if timeframe.endswith('m'):
        return int(timeframe[:-1]), 'minute'
    elif timeframe.endswith('h'):
        return int(timeframe[:-1]), 'hour'
    elif timeframe.endswith('d'):
        return int(timeframe[:-1]), 'day'
    else:
        raise ValueError(f"Unsupported timeframe: {timeframe}")