import pandas as pd
from polygon import RESTClient
from datetime import datetime
import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import config

def get_polygon_client():
    """Initialize and return a Polygon REST client."""
    return RESTClient(api_key=config.POLYGON_API_KEY)

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