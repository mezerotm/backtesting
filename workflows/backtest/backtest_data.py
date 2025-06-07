import pandas as pd
from typing import Dict, Optional
from datetime import datetime, timedelta
import logging
from polygon import RESTClient
from ..base_fetcher import BaseFetcher
import time
from functools import wraps
from utils.config import POLYGON_API_KEY

logger = logging.getLogger(__name__)

def retry_on_failure(max_retries=3, delay_seconds=5):
    """Decorator to retry function on failure with exponential backoff"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries == max_retries:
                        logger.error(f"Failed after {max_retries} retries: {e}")
                        raise
                    wait_time = delay_seconds * (2 ** (retries - 1))
                    logger.warning(f"Attempt {retries} failed. Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
            return None
        return wrapper
    return decorator

class BacktestDataFetcher(BaseFetcher):
    """Fetcher for backtest workflow data"""
    
    def __init__(self, force_refresh: bool = False):
        super().__init__(force_refresh, cache_subdir='backtest')
        self.client = RESTClient(POLYGON_API_KEY)
    
    @retry_on_failure(max_retries=3, delay_seconds=5)
    def fetch_historical_data(self, symbol: str, start_date: str, end_date: Optional[str] = None) -> pd.DataFrame:
        """Fetch historical OHLCV data for backtesting
        
        Args:
            symbol: Stock symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD), defaults to today
            
        Returns:
            pd.DataFrame with columns: Open, High, Low, Close, Volume
        """
        try:
            # Generate cache key
            end = end_date or datetime.now().strftime('%Y-%m-%d')
            cache_key = f"historical_{symbol}_{start_date}_{end}"
            
            # Check cache unless force refresh
            if not self.force_refresh:
                cached_data = self._load_from_cache(cache_key)
                if cached_data is not None:
                    return pd.DataFrame.from_dict(cached_data)
            
            # Add delay to avoid rate limiting
            time.sleep(0.2)  # Polygon allows 5 requests per second
            
            # Convert dates to datetime
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end, '%Y-%m-%d') if end else datetime.now()
            
            # Fetch data from Polygon
            aggs = self.client.get_aggs(
                ticker=symbol,
                multiplier=1,
                timespan="day",
                from_=start_dt.strftime('%Y-%m-%d'),
                to=end_dt.strftime('%Y-%m-%d'),
                adjusted=True
            )
            
            # Convert to DataFrame
            df = pd.DataFrame([{
                'Open': agg.open,
                'High': agg.high,
                'Low': agg.low,
                'Close': agg.close,
                'Volume': agg.volume,
                'Date': datetime.fromtimestamp(agg.timestamp/1000).strftime('%Y-%m-%d')
            } for agg in aggs])
            
            if df.empty:
                logger.error(f"No data returned for {symbol}")
                return pd.DataFrame()
            
            # Set Date as index
            df.set_index('Date', inplace=True)
            df.index = pd.to_datetime(df.index)
            
            # Cache the data
            self._save_to_cache(cache_key, df.to_dict())
            
            return df
            
        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {e}")
            raise  # Re-raise for retry decorator 