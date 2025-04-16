import pandas as pd
from polygon import RESTClient
from datetime import datetime, timedelta
import sys
import os
import time
import json
import requests
import yfinance as yf
import logging
from dateutil.relativedelta import relativedelta

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import config

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('data_fetcher')

# Cache configuration
_CACHE_DURATION = 30 * 60  # 30 minutes in seconds
_CACHE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'public', 'data_cache.json')
_MAX_CACHE_ENTRIES = 100  # Maximum number of entries to keep in cache

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
        logger.error(f"Error loading cache file: {e}")
        return {}

def _save_cache(cache_data):
    """Save cache to file with cleanup of old entries if needed."""
    try:
        # Ensure public directory exists
        cache_dir = os.path.dirname(_CACHE_FILE)
        os.makedirs(cache_dir, exist_ok=True)
        
        # Convert DataFrame to dictionary for JSON serialization
        serializable_cache = {}
        for key, entry in cache_data.items():
            if 'data' in entry:
                if isinstance(entry['data'], pd.DataFrame):
                    # Convert DataFrame to JSON
                    serializable_cache[key] = {
                        'timestamp': entry['timestamp'],
                        'data': entry['data'].to_json(orient='split', date_format='iso'),
                        'parameters': entry.get('parameters', {})
                    }
                elif isinstance(entry['data'], str):
                    # Already JSON string
                    serializable_cache[key] = entry
                else:
                    # Convert other data types to JSON
                    serializable_cache[key] = {
                        'timestamp': entry['timestamp'],
                        'data': json.dumps(entry['data']),
                        'parameters': entry.get('parameters', {})
                    }
            else:
                serializable_cache[key] = entry
        
        # Clean up old entries if we have too many
        if len(serializable_cache) > _MAX_CACHE_ENTRIES:
            # Sort by timestamp (oldest first)
            sorted_keys = sorted(serializable_cache.keys(), 
                                key=lambda k: serializable_cache[k]['timestamp'])
            
            # Remove oldest entries
            entries_to_remove = len(serializable_cache) - _MAX_CACHE_ENTRIES
            for key in sorted_keys[:entries_to_remove]:
                del serializable_cache[key]
            
            logger.info(f"Cleaned up {entries_to_remove} old cache entries")
        
        with open(_CACHE_FILE, 'w') as f:
            json.dump(serializable_cache, f)
            
    except Exception as e:
        logger.error(f"Error saving cache to file: {e}")

def _is_cache_valid(cache_data, cache_key):
    """Check if cache entry exists and is still valid."""
    if cache_key not in cache_data:
        return False
    
    cache_entry = cache_data[cache_key]
    cache_time = cache_entry['timestamp']
    current_time = time.time()
    
    # Check if cache is still valid (less than CACHE_DURATION old)
    return current_time - cache_time < _CACHE_DURATION

def _get_from_cache(cache_key, data_type="data"):
    """Generic function to get data from cache."""
    if config.ENV != 'development':
        return None
        
    cache_data = _load_cache()
    
    if _is_cache_valid(cache_data, cache_key):
        logger.info(f"Using cached {data_type} for {cache_key}")
        
        if data_type == "historical":
            # Convert cached JSON back to DataFrame
            cached_json = cache_data[cache_key]['data']
            return pd.read_json(cached_json, orient='split')
        else:
            # Return JSON data
            return json.loads(cache_data[cache_key]['data'])
    
    return None

def _save_to_cache(cache_key, data, parameters=None):
    """Generic function to save data to cache."""
    if config.ENV != 'development':
        return
        
    cache_data = _load_cache()
    
    # Update with new data
    cache_data[cache_key] = {
        'timestamp': time.time(),
        'data': data,
        'parameters': parameters or {}
    }
    
    # Save updated cache
    _save_cache(cache_data)
    logger.info(f"Cached data for {cache_key}")

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
    
    # Check cache first
    cached_data = _get_from_cache(cache_key, "historical")
    if cached_data is not None:
        return cached_data
    
    # If we reach here, we need to fetch data from the API
    try:
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
        
        # Store in cache
        _save_to_cache(cache_key, df, {
            'ticker': ticker,
            'start_date': start_date,
            'end_date': end_date,
            'timeframe': timeframe
        })
        
        return df
        
    except Exception as e:
        logger.error(f"Error fetching historical data for {ticker}: {e}")
        # Return empty DataFrame with correct columns
        return pd.DataFrame(columns=['Open', 'High', 'Low', 'Close', 'Volume'])

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

def fetch_interest_rates():
    """
    Fetch current interest rate data from FRED.
    
    Returns:
        dict: Dictionary containing interest rate data
    """
    # Generate cache key for interest rates
    cache_key = f"interest_rates_{datetime.now().strftime('%Y-%m-%d')}"
    
    # Check cache first
    cached_data = _get_from_cache(cache_key)
    if cached_data is not None:
        return cached_data
    
    try:
        # Use the API key from config
        api_key = config.FRED_API_KEY if hasattr(config.FRED_API_KEY, '__str__') else ''
        
        if not api_key:
            logger.warning("FRED API key not found. Using fallback data.")
            # Fallback data if API key is not available
            fallback_data = {
                'Federal Funds Rate': '5.50%',
                '10-Year Treasury': '4.25%',
                '30-Year Fixed Mortgage': '6.75%',
                'Last Updated': datetime.now().strftime('%Y-%m-%d')
            }
            _save_to_cache(cache_key, json.dumps(fallback_data))
            return fallback_data
        
        # Series IDs for different interest rates
        series = {
            'Federal Funds Rate': 'FEDFUNDS',
            '10-Year Treasury': 'DGS10',
            '30-Year Fixed Mortgage': 'MORTGAGE30US'
        }
        
        results = {}
        
        for name, series_id in series.items():
            url = f"https://api.stlouisfed.org/fred/series/observations"
            params = {
                'series_id': series_id,
                'api_key': api_key,
                'file_type': 'json',
                'sort_order': 'desc',
                'limit': 1
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            if 'observations' in data and len(data['observations']) > 0:
                value = data['observations'][0]['value']
                date = data['observations'][0]['date']
                results[name] = f"{float(value):.2f}%"
                results['Last Updated'] = date
            else:
                results[name] = 'N/A'
        
        # Cache the results
        _save_to_cache(cache_key, json.dumps(results))
        
        return results
    
    except Exception as e:
        logger.error(f"Error fetching interest rates: {e}")
        # Return fallback data on error
        fallback_data = {
            'Federal Funds Rate': '5.50%',
            '10-Year Treasury': '4.25%',
            '30-Year Fixed Mortgage': '6.75%',
            'Last Updated': datetime.now().strftime('%Y-%m-%d')
        }
        return fallback_data

def fetch_market_indices():
    """
    Fetch major market indices data using yfinance.
    
    Returns:
        dict: Dictionary containing market indices data
    """
    # Generate cache key for market indices - hourly cache
    cache_key = f"market_indices_{datetime.now().strftime('%Y-%m-%d_%H')}"
    
    # Check cache first
    cached_data = _get_from_cache(cache_key)
    if cached_data is not None:
        return cached_data
    
    try:
        # List of major indices to track
        indices = {
            'S&P 500': '^GSPC',
            'Dow Jones': '^DJI',
            'Nasdaq': '^IXIC',
            'Russell 2000': '^RUT',
            'VIX': '^VIX'
        }
        
        # Fetch data using yfinance
        # Add progress=False and interval='1d' for more reliable data
        data = yf.download(list(indices.values()), period='2d', interval='1d', progress=False)
        
        results = {}
        
        for name, ticker in indices.items():
            try:
                if 'Close' in data.columns:
                    # Handle single ticker case
                    if isinstance(data['Close'], pd.Series):
                        current = data['Close'].iloc[-1]
                        previous = data['Close'].iloc[-2]
                    # Handle multiple tickers case
                    else:
                        current = data['Close'][ticker].iloc[-1]
                        previous = data['Close'][ticker].iloc[-2]
                    
                    # Calculate change percentage
                    if pd.notna(current) and pd.notna(previous) and previous != 0:
                        change = ((current - previous) / previous) * 100
                        
                        results[name] = {
                            'value': f"{current:.2f}",
                            'change': f"{change:.2f}%",
                            'direction': 'up' if change >= 0 else 'down'
                        }
                    else:
                        results[name] = {
                            'value': 'N/A',
                            'change': 'N/A',
                            'direction': 'neutral'
                        }
                else:
                    results[name] = {
                        'value': 'N/A',
                        'change': 'N/A',
                        'direction': 'neutral'
                    }
            except Exception as e:
                logger.error(f"Error processing {name} ({ticker}): {e}")
                results[name] = {
                    'value': 'N/A',
                    'change': 'N/A',
                    'direction': 'neutral'
                }
        
        # Cache the results
        _save_to_cache(cache_key, json.dumps(results))
        
        return results
    
    except Exception as e:
        logger.error(f"Error fetching market indices: {e}")
        # Return fallback data on error
        return {
            'S&P 500': {'value': 'N/A', 'change': 'N/A', 'direction': 'neutral'},
            'Dow Jones': {'value': 'N/A', 'change': 'N/A', 'direction': 'neutral'},
            'Nasdaq': {'value': 'N/A', 'change': 'N/A', 'direction': 'neutral'},
            'Russell 2000': {'value': 'N/A', 'change': 'N/A', 'direction': 'neutral'},
            'VIX': {'value': 'N/A', 'change': 'N/A', 'direction': 'neutral'}
        }

def fetch_economic_indicators(force_refresh=False):
    """
    Fetch key economic indicators from various sources.
    
    Args:
        force_refresh (bool): If True, bypass cache and fetch fresh data
        
    Returns:
        dict: Dictionary containing economic indicators data
    """
    # Generate cache key for economic indicators - daily cache
    cache_key = f"economic_indicators_{datetime.now().strftime('%Y-%m-%d')}"
    
    # Check cache first (unless force_refresh is True)
    if not force_refresh:
        cached_data = _get_from_cache(cache_key)
        if cached_data is not None:
            return cached_data
    else:
        logger.info("Force refresh requested, bypassing cache")
    
    try:
        # Use the API key from config
        api_key = config.FRED_API_KEY if hasattr(config.FRED_API_KEY, '__str__') else ''
        
        # Debug FRED API key
        logger.info(f"FRED API Key available: {bool(api_key)}")
        
        if not api_key:
            logger.warning("FRED API key not found. Using N/A values for economic indicators.")
            # Use N/A data if API key is not available
            na_data = {
                'GDP Growth': {'value': 'N/A', 'period': 'N/A', 'direction': 'neutral'},
                'Inflation Rate': {'value': 'N/A', 'period': 'N/A', 'direction': 'neutral'},
                'Unemployment Rate': {'value': 'N/A', 'period': 'N/A', 'direction': 'neutral'},
                'US 10Y Bond': {'value': 'N/A', 'change': 'N/A', 'direction': 'neutral'},
                'Dollar Index (DXY)': {'value': 'N/A', 'change': 'N/A', 'direction': 'neutral'},
                'Money Supply M1': {'value': 'N/A', 'period': 'N/A', 'direction': 'neutral'},
                'S&P 500 ETF (SPY)': {'value': 'N/A', 'change': 'N/A', 'direction': 'neutral'},
                'Bitcoin/USD': {'value': 'N/A', 'change': 'N/A', 'direction': 'neutral'},
                'Last Updated': datetime.now().strftime('%Y-%m-%d')
            }
            _save_to_cache(cache_key, json.dumps(na_data))
            return na_data
        
        results = {}
        
        # Fetch GDP Growth (Real GDP Growth Rate)
        try:
            gdp_url = f"https://api.stlouisfed.org/fred/series/observations"
            gdp_params = {
                'series_id': 'A191RL1Q225SBEA',  # Real GDP Growth Rate
                'api_key': api_key,
                'file_type': 'json',
                'sort_order': 'desc',
                'limit': 1
            }
            
            gdp_response = requests.get(gdp_url, params=gdp_params)
            gdp_data = gdp_response.json()
            
            if 'observations' in gdp_data and len(gdp_data['observations']) > 0:
                gdp_value = float(gdp_data['observations'][0]['value'])
                gdp_date = gdp_data['observations'][0]['date']
                quarter = (datetime.strptime(gdp_date, '%Y-%m-%d').month-1)//3+1
                year = datetime.strptime(gdp_date, '%Y-%m-%d').year
                
                results['GDP Growth'] = {
                    'value': f"{gdp_value:.1f}%",
                    'period': f"Q{quarter} {year}",
                    'direction': 'up' if gdp_value > 0 else 'down' if gdp_value < 0 else 'neutral'
                }
            else:
                results['GDP Growth'] = {'value': 'N/A', 'period': 'N/A', 'direction': 'neutral'}
        except Exception as e:
            logger.error(f"Error fetching GDP data: {e}")
            results['GDP Growth'] = {'value': 'N/A', 'period': 'N/A', 'direction': 'neutral'}
        
        # Fetch Inflation Rate (CPI Year-over-Year) - with enhanced debugging
        try:
            # Use CPIAUCSL for CPI All Items
            cpi_url = f"https://api.stlouisfed.org/fred/series/observations"
            cpi_params = {
                'series_id': 'CPIAUCSL',
                'api_key': api_key,
                'file_type': 'json',
                'sort_order': 'desc',
                'limit': 13  # Need current month and same month last year
            }
            
            logger.info(f"Fetching inflation data with params: {cpi_params}")
            cpi_response = requests.get(cpi_url, params=cpi_params)
            
            # Debug response status
            logger.info(f"Inflation API response status: {cpi_response.status_code}")
            
            if cpi_response.status_code != 200:
                logger.error(f"FRED API error: {cpi_response.text}")
                results['Inflation Rate'] = {'value': 'N/A', 'period': 'N/A', 'direction': 'neutral'}
            else:
                cpi_data = cpi_response.json()
                
                # Debug the raw response
                logger.info(f"CPI data observations count: {len(cpi_data.get('observations', []))}")
                
                if 'observations' in cpi_data and len(cpi_data['observations']) >= 13:
                    current_cpi = float(cpi_data['observations'][0]['value'])
                    year_ago_cpi = float(cpi_data['observations'][12]['value'])
                    inflation_rate = ((current_cpi / year_ago_cpi) - 1) * 100
                    current_date = cpi_data['observations'][0]['date']
                    
                    logger.info(f"Calculated inflation rate: {inflation_rate:.2f}%")
                    
                    results['Inflation Rate'] = {
                        'value': f"{inflation_rate:.1f}%",
                        'period': f"{datetime.strptime(current_date, '%Y-%m-%d').strftime('%b %Y')}",
                        'direction': 'up' if inflation_rate > 2.0 else 'down' if inflation_rate < 0 else 'neutral'
                    }
                else:
                    # N/A if we don't have enough data
                    logger.warning("Not enough CPI data points for inflation calculation")
                    results['Inflation Rate'] = {'value': 'N/A', 'period': 'N/A', 'direction': 'neutral'}
        except Exception as e:
            logger.error(f"Error fetching inflation data: {e}", exc_info=True)
            results['Inflation Rate'] = {'value': 'N/A', 'period': 'N/A', 'direction': 'neutral'}
        
        # Fetch Unemployment Rate
        try:
            unemp_url = f"https://api.stlouisfed.org/fred/series/observations"
            unemp_params = {
                'series_id': 'UNRATE',
                'api_key': api_key,
                'file_type': 'json',
                'sort_order': 'desc',
                'limit': 2
            }
            
            unemp_response = requests.get(unemp_url, params=unemp_params)
            unemp_data = unemp_response.json()
            
            if 'observations' in unemp_data and len(unemp_data['observations']) > 0:
                current_unemp = float(unemp_data['observations'][0]['value'])
                current_date = unemp_data['observations'][0]['date']
                
                # Calculate change if we have previous data
                if len(unemp_data['observations']) > 1:
                    prev_unemp = float(unemp_data['observations'][1]['value'])
                    change = current_unemp - prev_unemp
                    
                    results['Unemployment Rate'] = {
                        'value': f"{current_unemp:.2f}%",
                        'period': f"{datetime.strptime(current_date, '%Y-%m-%d').strftime('%b %Y')}",
                        'change': f"{change:+.2f}%",
                        'direction': 'up' if change > 0 else 'down' if change < 0 else 'neutral'
                    }
                else:
                    results['Unemployment Rate'] = {
                        'value': f"{current_unemp:.2f}%",
                        'period': f"{datetime.strptime(current_date, '%Y-%m-%d').strftime('%b %Y')}",
                        'direction': 'neutral'
                    }
            else:
                results['Unemployment Rate'] = {'value': 'N/A', 'period': 'N/A', 'direction': 'neutral'}
        except Exception as e:
            logger.error(f"Error fetching unemployment data: {e}")
            results['Unemployment Rate'] = {'value': 'N/A', 'period': 'N/A', 'direction': 'neutral'}
        
        # Fetch 10-Year Treasury Rate
        try:
            treasury_url = f"https://api.stlouisfed.org/fred/series/observations"
            treasury_params = {
                'series_id': 'DGS10',
                'api_key': api_key,
                'file_type': 'json',
                'sort_order': 'desc',
                'limit': 2
            }
            
            treasury_response = requests.get(treasury_url, params=treasury_params)
            treasury_data = treasury_response.json()
            
            if 'observations' in treasury_data and len(treasury_data['observations']) > 0:
                current_rate = float(treasury_data['observations'][0]['value'])
                
                # Calculate change if we have previous data
                if len(treasury_data['observations']) > 1:
                    prev_rate = float(treasury_data['observations'][1]['value'])
                    change = current_rate - prev_rate
                    
                    results['US 10Y Bond'] = {
                        'value': f"{current_rate:.2f}%",
                        'change': f"{change:+.2f}%",
                        'direction': 'up' if change > 0 else 'down' if change < 0 else 'neutral'
                    }
                else:
                    results['US 10Y Bond'] = {
                        'value': f"{current_rate:.2f}%",
                        'direction': 'neutral'
                    }
            else:
                results['US 10Y Bond'] = {'value': 'N/A', 'change': 'N/A', 'direction': 'neutral'}
        except Exception as e:
            logger.error(f"Error fetching treasury data: {e}")
            results['US 10Y Bond'] = {'value': 'N/A', 'change': 'N/A', 'direction': 'neutral'}
        
        # Fetch Dollar Index (DXY)
        try:
            dxy_url = f"https://api.stlouisfed.org/fred/series/observations"
            dxy_params = {
                'series_id': 'DTWEXBGS',  # Broad Dollar Index
                'api_key': api_key,
                'file_type': 'json',
                'sort_order': 'desc',
                'limit': 2
            }
            
            dxy_response = requests.get(dxy_url, params=dxy_params)
            dxy_data = dxy_response.json()
            
            if 'observations' in dxy_data and len(dxy_data['observations']) > 0:
                current_dxy = float(dxy_data['observations'][0]['value'])
                
                # Calculate change if we have previous data
                if len(dxy_data['observations']) > 1:
                    prev_dxy = float(dxy_data['observations'][1]['value'])
                    change = ((current_dxy / prev_dxy) - 1) * 100
                    
                    results['Dollar Index (DXY)'] = {
                        'value': f"{current_dxy:.2f}",
                        'change': f"{change:+.2f}%",
                        'direction': 'up' if change > 0 else 'down' if change < 0 else 'neutral'
                    }
                else:
                    results['Dollar Index (DXY)'] = {
                        'value': f"{current_dxy:.2f}",
                        'direction': 'neutral'
                    }
            else:
                results['Dollar Index (DXY)'] = {'value': 'N/A', 'change': 'N/A', 'direction': 'neutral'}
        except Exception as e:
            logger.error(f"Error fetching DXY data: {e}")
            results['Dollar Index (DXY)'] = {'value': 'N/A', 'change': 'N/A', 'direction': 'neutral'}
        
        # Fetch Money Supply M1 - with enhanced debugging
        try:
            m1_url = f"https://api.stlouisfed.org/fred/series/observations"
            m1_params = {
                'series_id': 'M1SL',
                'api_key': api_key,
                'file_type': 'json',
                'sort_order': 'desc',
                'limit': 1
            }
            
            logger.info(f"Fetching M1 data with params: {m1_params}")
            m1_response = requests.get(m1_url, params=m1_params)
            
            # Debug response status
            logger.info(f"M1 API response status: {m1_response.status_code}")
            
            if m1_response.status_code != 200:
                logger.error(f"FRED API error for M1: {m1_response.text}")
                results['Money Supply M1'] = {'value': 'N/A', 'period': 'N/A', 'direction': 'neutral'}
            else:
                m1_data = m1_response.json()
                
                # Debug the raw response
                if 'observations' in m1_data:
                    logger.info(f"M1 data observations count: {len(m1_data['observations'])}")
                    if len(m1_data['observations']) > 0:
                        logger.info(f"M1 Raw Data: {m1_data['observations'][0]}")
                else:
                    logger.warning("No observations in M1 data response")
                
                if 'observations' in m1_data and len(m1_data['observations']) > 0:
                    current_m1_str = m1_data['observations'][0]['value']
                    current_date = m1_data['observations'][0]['date']
                    
                    logger.info(f"Raw M1 value: '{current_m1_str}', date: {current_date}")
                    
                    # Check if the value is valid
                    if current_m1_str and current_m1_str.strip() and current_m1_str.strip().lower() != 'null':
                        try:
                            current_m1 = float(current_m1_str)
                            logger.info(f"Parsed M1 value: {current_m1}")
                            
                            # Convert to trillions for display (M1SL is in billions)
                            m1_trillions = current_m1 / 1000.0  # Convert billions to trillions
                            logger.info(f"M1 in trillions: {m1_trillions:.1f}T")
                            
                            results['Money Supply M1'] = {
                                'value': f"${m1_trillions:.1f}T",
                                'period': f"{datetime.strptime(current_date, '%Y-%m-%d').strftime('%b %Y')}",
                                'direction': 'neutral'
                            }
                        except (ValueError, TypeError) as e:
                            logger.error(f"Error converting M1 value '{current_m1_str}' to float: {e}")
                            results['Money Supply M1'] = {'value': 'N/A', 'period': 'N/A', 'direction': 'neutral'}
                    else:
                        logger.warning(f"Invalid M1 value received: '{current_m1_str}'")
                        results['Money Supply M1'] = {'value': 'N/A', 'period': 'N/A', 'direction': 'neutral'}
                else:
                    logger.warning("No M1 data observations found")
                    results['Money Supply M1'] = {'value': 'N/A', 'period': 'N/A', 'direction': 'neutral'}
        except Exception as e:
            logger.error(f"Error fetching M1 data: {e}", exc_info=True)
            results['Money Supply M1'] = {'value': 'N/A', 'period': 'N/A', 'direction': 'neutral'}
        
        # Add SPY and Bitcoin data using yfinance
        try:
            crypto_forex_data = yf.download(['SPY', 'BTC-USD'], period='2d', progress=False)
            
            # Process SPY
            if 'Close' in crypto_forex_data and 'SPY' in crypto_forex_data['Close']:
                current = crypto_forex_data['Close']['SPY'].iloc[-1]
                previous = crypto_forex_data['Close']['SPY'].iloc[-2]
                change = ((current - previous) / previous) * 100
                
                results['S&P 500 ETF (SPY)'] = {
                    'value': f"${current:.2f}",
                    'change': f"{change:+.2f}%",
                    'direction': 'up' if change >= 0 else 'down'
                }
            else:
                results['S&P 500 ETF (SPY)'] = {'value': 'N/A', 'change': 'N/A', 'direction': 'neutral'}
            
            # Process Bitcoin
            if 'Close' in crypto_forex_data and 'BTC-USD' in crypto_forex_data['Close']:
                current = crypto_forex_data['Close']['BTC-USD'].iloc[-1]
                previous = crypto_forex_data['Close']['BTC-USD'].iloc[-2]
                change = ((current - previous) / previous) * 100
                
                results['Bitcoin/USD'] = {
                    'value': f"${current:.2f}",
                    'change': f"{change:+.2f}%",
                    'direction': 'up' if change >= 0 else 'down'
                }
            else:
                results['Bitcoin/USD'] = {'value': 'N/A', 'change': 'N/A', 'direction': 'neutral'}
        except Exception as e:
            logger.error(f"Error fetching SPY and Bitcoin data: {e}")
            results['S&P 500 ETF (SPY)'] = {'value': 'N/A', 'change': 'N/A', 'direction': 'neutral'}
            results['Bitcoin/USD'] = {'value': 'N/A', 'change': 'N/A', 'direction': 'neutral'}
        
        results['Last Updated'] = datetime.now().strftime('%Y-%m-%d')
        
        # Cache the results
        _save_to_cache(cache_key, json.dumps(results))
        
        return results
    
    except Exception as e:
        logger.error(f"Error fetching economic indicators: {e}", exc_info=True)
        # Return N/A data on error
        return {
            'GDP Growth': {'value': 'N/A', 'period': 'N/A', 'direction': 'neutral'},
            'Inflation Rate': {'value': 'N/A', 'period': 'N/A', 'direction': 'neutral'},
            'Unemployment Rate': {'value': 'N/A', 'period': 'N/A', 'direction': 'neutral'},
            'US 10Y Bond': {'value': 'N/A', 'change': 'N/A', 'direction': 'neutral'},
            'Dollar Index (DXY)': {'value': 'N/A', 'change': 'N/A', 'direction': 'neutral'},
            'Money Supply M1': {'value': 'N/A', 'period': 'N/A', 'direction': 'neutral'},
            'S&P 500 ETF (SPY)': {'value': 'N/A', 'change': 'N/A', 'direction': 'neutral'},
            'Bitcoin/USD': {'value': 'N/A', 'change': 'N/A', 'direction': 'neutral'},
            'Last Updated': datetime.now().strftime('%Y-%m-%d')
        }

def fetch_economic_history(indicator_id, limit=20, force_refresh=False):
    """Fetch historical data for economic indicators."""
    try:
        api_key = config.FRED_API_KEY
        if not api_key:
            return {'labels': [], 'values': [], 'title': 'API Key Error'}

        # For GDP, we want more historical data
        if indicator_id == 'A191RL1Q225SBEA':
            params = {
                'series_id': indicator_id,
                'api_key': api_key,
                'file_type': 'json',
                'sort_order': 'desc',
                'limit': 40  # Get more historical quarters
            }
        else:
            params = {
                'series_id': indicator_id,
                'api_key': api_key,
                'file_type': 'json',
                'sort_order': 'desc',
                'limit': limit
            }
        
        print(f"DEBUG - Fetching {indicator_id} data with params: {params}")
        response = requests.get("https://api.stlouisfed.org/fred/series/observations", params=params)
        
        if response.status_code != 200:
            print(f"API Error {response.status_code}: {response.text}")
            return {'labels': [], 'values': [], 'title': 'API Error'}
        
        data = response.json()
        observations = data.get('observations', [])
        
        if not observations:
            print(f"No data found for {indicator_id}")
            return {'labels': [], 'values': [], 'title': 'No Data'}

        labels = []
        values = []
        
        # Process the data based on indicator type
        if indicator_id == 'A191RL1Q225SBEA':  # GDP
            for obs in observations:
                if obs['value'] != '.':
                    date = datetime.strptime(obs['date'], '%Y-%m-%d')
                    quarter = (date.month - 1) // 3 + 1
                    label = f"Q{quarter} {date.year}"
                    try:
                        value = float(obs['value'])
                        labels.append(label)
                        values.append(value)
                    except ValueError:
                        print(f"Error converting GDP value: {obs['value']}")
                        continue
        elif indicator_id == 'CPIAUCSL':  # Inflation
            # Calculate year-over-year inflation rate
            for i in range(len(observations) - 12):  # Need 12 months for YoY calculation
                try:
                    current = float(observations[i]['value'])
                    year_ago = float(observations[i + 12]['value'])
                    # Calculate inflation rate as percentage with 2 decimal places
                    inflation_rate = ((current - year_ago) / year_ago) * 100
                    
                    date = datetime.strptime(observations[i]['date'], '%Y-%m-%d')
                    label = date.strftime('%Y-%m-%d')
                    labels.append(label)
                    values.append(round(inflation_rate, 2))  # Round to 2 decimal places
                except (ValueError, IndexError) as e:
                    print(f"Error calculating inflation: {e}")
                    continue
        else:
            # For other indicators, use monthly data
            for obs in observations:
                if obs['value'] != '.':
                    try:
                        value = float(obs['value'])
                        date = datetime.strptime(obs['date'], '%Y-%m-%d')
                        label = date.strftime('%Y-%m-%d')
                        labels.append(label)
                        values.append(value)
                    except ValueError:
                        continue

        # Reverse to get chronological order
        labels.reverse()
        values.reverse()
        
        # Limit to requested number of points
        labels = labels[-limit:]
        values = values[-limit:]

        print(f"DEBUG - Processed {len(labels)} data points for {indicator_id}")
        print(f"DEBUG - Sample data: {list(zip(labels[:3], values[:3]))}")
        
        return {
            'labels': labels,
            'values': values,
            'title': get_indicator_title(indicator_id)
        }
        
    except Exception as e:
        print(f"ERROR - Failed to fetch {indicator_id}: {e}")
        return {'labels': [], 'values': [], 'title': 'Error'}

def get_indicator_title(indicator_id):
    """Get the title for each indicator."""
    titles = {
        'A191RL1Q225SBEA': 'Real GDP Growth Rate',
        'CPIAUCSL': 'Inflation Rate',
        'UNRATE': 'Unemployment Rate',
        'DGS10': 'US 10Y Bond Yield'
    }
    return titles.get(indicator_id, 'Economic Data')