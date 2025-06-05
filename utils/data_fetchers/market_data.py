from typing import Dict
from datetime import datetime, timedelta
import logging
from polygon import RESTClient
import requests
from .base_fetcher import BaseFetcher
from utils.config import POLYGON_API_KEY, FRED_API_KEY
import pandas as pd

logger = logging.getLogger(__name__)

class MarketDataFetcher(BaseFetcher):
    """Fetcher for market check workflow data"""
    
    def __init__(self, force_refresh: bool = False):
        super().__init__(force_refresh, cache_subdir='market')
        self.client = RESTClient(POLYGON_API_KEY)
        self.fred_api_key = FRED_API_KEY
    
    def fetch_market_indices(self) -> Dict:
        """Fetch major market indices data"""
        cache_key = f"market_indices_{datetime.now().strftime('%Y-%m-%d_%H')}"
        
        if not self.force_refresh:
            cached_data = self._load_from_cache(cache_key, max_age_hours=1)
            if cached_data:
                return cached_data
        
        try:
            indices = {
                'S&P 500': 'SPY',
                'Dow Jones': 'DIA',
                'Nasdaq': 'QQQ',
                'Russell 2000': 'IWM',
                'VIX': 'VIX'
            }
            
            results = {}
            for name, ticker in indices.items():
                try:
                    # Get previous day's data
                    aggs = self.client.get_aggs(
                        ticker=ticker,
                        multiplier=1,
                        timespan="day",
                        from_=datetime.now().strftime('%Y-%m-%d'),
                        to=datetime.now().strftime('%Y-%m-%d'),
                        adjusted=True
                    )
                    
                    if aggs:
                        current = aggs[0].close
                        # Get previous day for comparison
                        prev_aggs = self.client.get_aggs(
                            ticker=ticker,
                            multiplier=1,
                            timespan="day",
                            from_=(datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'),
                            to=(datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'),
                            adjusted=True
                        )
                        previous = prev_aggs[0].close if prev_aggs else current
                        
                        change = ((current - previous) / previous) * 100
                        results[name] = {
                            'value': f"{current:.2f}",
                            'change': f"{change:.2f}%",
                            'direction': 'up' if change >= 0 else 'down'
                        }
                    else:
                        results[name] = {'value': 'N/A', 'change': 'N/A', 'direction': 'neutral'}
                        
                except Exception as e:
                    logger.error(f"Error processing {name}: {e}")
                    results[name] = {'value': 'N/A', 'change': 'N/A', 'direction': 'neutral'}
            
            self._save_to_cache(cache_key, results)
            return results
            
        except Exception as e:
            logger.error(f"Error fetching market indices: {e}")
            return {name: {'value': 'N/A', 'change': 'N/A', 'direction': 'neutral'} 
                    for name in indices.keys()}
    
    def fetch_interest_rates(self) -> Dict:
        """Fetch interest rate data"""
        cache_key = f"interest_rates_{datetime.now().strftime('%Y-%m-%d')}"
        
        if not self.force_refresh:
            cached_data = self._load_from_cache(cache_key)
            if cached_data:
                return cached_data
        
        try:
            if not self.fred_api_key:
                logger.warning("FRED API key not found")
                return {
                    'Federal Funds Rate': 'N/A',
                    '10-Year Treasury': 'N/A',
                    '30-Year Fixed Mortgage': 'N/A',
                    'Last Updated': datetime.now().strftime('%Y-%m-%d')
                }
            
            series = {
                'Federal Funds Rate': 'FEDFUNDS',
                '10-Year Treasury': 'DGS10',
                '30-Year Fixed Mortgage': 'MORTGAGE30US'
            }
            
            results = {}
            for name, series_id in series.items():
                response = requests.get(
                    "https://api.stlouisfed.org/fred/series/observations",
                    params={
                        'series_id': series_id,
                        'api_key': self.fred_api_key,
                        'file_type': 'json',
                        'sort_order': 'desc',
                        'limit': 1
                    }
                )
                data = response.json()
                
                if 'observations' in data and len(data['observations']) > 0:
                    value = data['observations'][0]['value']
                    date = data['observations'][0]['date']
                    results[name] = f"{float(value):.2f}%"
                    results['Last Updated'] = date
                else:
                    results[name] = 'N/A'
            
            self._save_to_cache(cache_key, results)
            return results
            
        except Exception as e:
            logger.error(f"Error fetching interest rates: {e}")
            return {
                'Federal Funds Rate': 'N/A',
                '10-Year Treasury': 'N/A',
                '30-Year Fixed Mortgage': 'N/A',
                'Last Updated': datetime.now().strftime('%Y-%m-%d')
            }
    
    def fetch_economic_indicators(self) -> Dict:
        """Fetch economic indicators"""
        cache_key = f"economic_indicators_{datetime.now().strftime('%Y-%m-%d')}"
        
        if not self.force_refresh:
            cached_data = self._load_from_cache(cache_key)
            if cached_data:
                return cached_data
        
        try:
            if not self.fred_api_key:
                logger.warning("FRED API key not found")
                return {
                    'GDP Growth': {'value': 'N/A', 'period': 'N/A', 'direction': 'neutral'},
                    'Inflation Rate': {'value': 'N/A', 'period': 'N/A', 'direction': 'neutral'},
                    'Unemployment': {'value': 'N/A', 'period': 'N/A', 'direction': 'neutral'}
                }
            
            indicators = {
                'GDP Growth': {
                    'series_id': 'GDP',
                    'transform': lambda x: f"{float(x):.1f}%"
                },
                'Inflation Rate': {
                    'series_id': 'CPIAUCSL',
                    'transform': lambda x: f"{float(x):.1f}%"
                },
                'Unemployment': {
                    'series_id': 'UNRATE',
                    'transform': lambda x: f"{float(x):.1f}%"
                }
            }
            
            results = {}
            for name, config in indicators.items():
                try:
                    response = requests.get(
                        "https://api.stlouisfed.org/fred/series/observations",
                        params={
                            'series_id': config['series_id'],
                            'api_key': self.fred_api_key,
                            'file_type': 'json',
                            'sort_order': 'desc',
                            'limit': 2
                        }
                    )
                    data = response.json()
                    
                    if 'observations' in data and len(data['observations']) > 0:
                        current = float(data['observations'][0]['value'])
                        previous = float(data['observations'][1]['value']) if len(data['observations']) > 1 else current
                        
                        direction = 'neutral'
                        if current > previous:
                            direction = 'up'
                        elif current < previous:
                            direction = 'down'
                        
                        results[name] = {
                            'value': config['transform'](current),
                            'period': data['observations'][0]['date'],
                            'direction': direction
                        }
                    else:
                        results[name] = {
                            'value': 'N/A',
                            'period': 'N/A',
                            'direction': 'neutral'
                        }
                    
                except Exception as e:
                    logger.error(f"Error fetching {name}: {e}")
                    results[name] = {
                        'value': 'N/A',
                        'period': 'N/A',
                        'direction': 'neutral'
                    }
            
            self._save_to_cache(cache_key, results)
            return results
            
        except Exception as e:
            logger.error(f"Error fetching economic indicators: {e}")
            return {
                'GDP Growth': {'value': 'N/A', 'period': 'N/A', 'direction': 'neutral'},
                'Inflation Rate': {'value': 'N/A', 'period': 'N/A', 'direction': 'neutral'},
                'Unemployment': {'value': 'N/A', 'period': 'N/A', 'direction': 'neutral'}
            }
    
    def fetch_economic_history(self, indicator_id: str, limit: int = 20) -> Dict:
        """Fetch historical economic data"""
        cache_key = f"economic_history_{indicator_id}_{limit}"
        
        if not self.force_refresh:
            cached_data = self._load_from_cache(cache_key)
            if cached_data:
                return cached_data
        
        try:
            if not self.fred_api_key:
                logger.warning("FRED API key not found")
                return {'labels': [], 'values': [], 'title': indicator_id}
            
            response = requests.get(
                "https://api.stlouisfed.org/fred/series/observations",
                params={
                    'series_id': indicator_id,
                    'api_key': self.fred_api_key,
                    'file_type': 'json',
                    'sort_order': 'desc',
                    'limit': limit
                }
            )
            data = response.json()
            
            if 'observations' in data and data['observations']:
                observations = list(reversed(data['observations']))
                valid_observations = [(obs['date'], float(obs['value'])) 
                                    for obs in observations 
                                    if obs['value'] != '.' and obs['value'].strip()]
                
                if valid_observations:
                    result = {
                        'labels': [date for date, _ in valid_observations],
                        'values': [value for _, value in valid_observations],
                        'title': indicator_id
                    }
                    self._save_to_cache(cache_key, result)
                    return result
            
            logger.warning(f"No valid data found for indicator {indicator_id}")
            return {'labels': [], 'values': [], 'title': indicator_id}
            
        except Exception as e:
            logger.error(f"Error fetching economic history for {indicator_id}: {e}")
            return {'labels': [], 'values': [], 'title': indicator_id} 