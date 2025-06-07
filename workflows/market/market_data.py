from typing import Dict
from datetime import datetime, timedelta
import logging
from polygon import RESTClient
import requests
from ..base_fetcher import BaseFetcher
from utils.config import POLYGON_API_KEY, FRED_API_KEY
import pandas as pd
import pytz

logger = logging.getLogger(__name__)

class MarketDataFetcher(BaseFetcher):
    """Fetcher for market check workflow data"""
    
    def __init__(self, force_refresh: bool = False):
        super().__init__(force_refresh, cache_subdir='market')
        self.client = RESTClient(POLYGON_API_KEY)
        self.fred_api_key = FRED_API_KEY
    
    def fetch_market_indices(self) -> Dict:
        """Fetch major market indices data from FRED"""
        now = datetime.now()
        et_time = datetime.now(pytz.timezone('US/Eastern'))
        is_market_hours = 9 <= et_time.hour < 16
        cache_key = (f"market_indices_{now.strftime('%Y-%m-%d_%H_%M')}" if is_market_hours 
                    else f"market_indices_{now.strftime('%Y-%m-%d_%H')}")
        if not self.force_refresh:
            max_age = 5/60 if is_market_hours else 1
            cached_data = self._load_from_cache(cache_key, max_age_hours=max_age)
            if cached_data:
                return cached_data
        try:
            if not self.fred_api_key:
                logger.warning("FRED API key not found")
                return {
                    'S&P 500': {'value': 'N/A', 'change': 'N/A', 'direction': 'neutral'},
                    'Dow Jones': {'value': 'N/A', 'change': 'N/A', 'direction': 'neutral'},
                    'Nasdaq': {'value': 'N/A', 'change': 'N/A', 'direction': 'neutral'},
                    'Russell 2000': {'value': 'N/A', 'change': 'N/A', 'direction': 'neutral'},
                    'VIX': {'value': 'N/A', 'change': 'N/A', 'direction': 'neutral'}
                }
            series = {
                'S&P 500': 'SP500',
                'Dow Jones': 'DJIA',
                'Nasdaq': 'NASDAQCOM',
                'Russell 2000': 'RUTCLS',
                'VIX': 'VIXCLS'
            }
            results = {}
            for name, series_id in series.items():
                try:
                    response = requests.get(
                        "https://api.stlouisfed.org/fred/series/observations",
                        params={
                            'series_id': series_id,
                            'api_key': self.fred_api_key,
                            'file_type': 'json',
                            'sort_order': 'desc',
                            'limit': 2
                        }
                    )
                    data = response.json()
                    if 'observations' in data and len(data['observations']) >= 2:
                        current = float(data['observations'][0]['value']) if data['observations'][0]['value'] != '.' else None
                        previous = float(data['observations'][1]['value']) if data['observations'][1]['value'] != '.' else None
                        if current is not None and previous is not None:
                            change = ((current - previous) / previous) * 100 if previous != 0 else 0
                            results[name] = {
                                'value': f"{current:.2f}",
                                'change': f"{change:+.2f}%",
                                'direction': 'up' if change > 0 else 'down' if change < 0 else 'neutral'
                            }
                        else:
                            results[name] = {'value': 'N/A', 'change': 'N/A', 'direction': 'neutral'}
                    else:
                        results[name] = {'value': 'N/A', 'change': 'N/A', 'direction': 'neutral'}
                        if name == 'VIX':
                            logger.warning(f"VIX data missing or N/A for {datetime.now().strftime('%Y-%m-%d')}")
                except Exception as e:
                    logger.error(f"Error processing {name}: {e}", exc_info=True)
                    results[name] = {'value': 'N/A', 'change': 'N/A', 'direction': 'neutral'}
                    if name == 'VIX':
                        logger.error(f"VIX error: {e}")
            logger.info(f"Market Indices Results: {results}")
            self._save_to_cache(cache_key, results)
            return results
        except Exception as e:
            logger.error(f"Error fetching market indices: {e}")
            return {name: {'value': 'N/A', 'change': 'N/A', 'direction': 'neutral'} 
                    for name in ['S&P 500', 'Dow Jones', 'Nasdaq', 'Russell 2000', 'VIX']}
    
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
        # Include timezone in cache key
        et_now = datetime.now(pytz.timezone('US/Eastern'))
        cache_key = f"economic_indicators_{et_now.strftime('%Y-%m-%d')}"
        
        if not self.force_refresh:
            cached_data = self._load_from_cache(cache_key, max_age_hours=24)  # Daily refresh
            if cached_data:
                logger.info("Using cached economic indicators data")
                return cached_data
        
        try:
            if not self.fred_api_key:
                logger.warning("FRED API key not found")
                return {
                    'GDP': {'value': 'N/A', 'previous': 'N/A', 'change_rate': 'N/A', 'trend': 'neutral', 'last_updated': 'N/A'},
                    'Inflation': {'value': 'N/A', 'previous': 'N/A', 'change_rate': 'N/A', 'trend': 'neutral', 'last_updated': 'N/A'},
                    'Unemployment': {'value': 'N/A', 'previous': 'N/A', 'change_rate': 'N/A', 'trend': 'neutral', 'last_updated': 'N/A'},
                    'Last Updated': datetime.now().strftime('%Y-%m-%d')
                }
            
            indicators = {
                'GDP': {
                    'series_id': 'A191RL1Q225SBEA',  # Real GDP Growth Rate (Percent Change SAAR)
                    'transform': lambda x: f"{float(x):.1f}%",  # Already in percent
                    'change_transform': lambda x: f"{x:.1f}%"
                },
                'CPI': {
                    'series_id': 'CPIAUCSL',
                    'transform': lambda x: f"{float(x):.1f}",
                    'change_transform': lambda x: f"{x:.1f}%"
                },
                'Inflation YoY': {
                    'series_id': 'CPIAUCSL',
                    'transform': lambda x: f"{float(x):.1f}%",
                    'change_transform': lambda x: f"{x:.1f}%",
                    'yoy': True  # Flag to calculate year-over-year change
                },
                'Unemployment': {
                    'series_id': 'UNRATE',
                    'transform': lambda x: f"{float(x):.1f}%",
                    'change_transform': lambda x: f"{x:.1f}%"
                }
            }
            
            results = {}
            for name, config in indicators.items():
                try:
                    # For GDP, we need quarterly data
                    limit = 17 if config.get('yoy', False) else 5
                    freq = 'q' if name == 'GDP' else None  # Use quarterly frequency for GDP
                    
                    params = {
                        'series_id': config['series_id'],
                        'api_key': self.fred_api_key,
                        'file_type': 'json',
                        'sort_order': 'desc',
                        'limit': limit
                    }
                    if freq:
                        params['frequency'] = freq
                    
                    response = requests.get(
                        "https://api.stlouisfed.org/fred/series/observations",
                        params=params
                    )
                    data = response.json()
                    
                    if 'observations' in data and len(data['observations']) >= 2:
                        observations = [float(obs['value']) for obs in data['observations'] if obs['value'] != '.']
                        
                        if len(observations) >= 2:
                            if name == 'GDP':
                                # For GDP, we're now using the direct growth rate series
                                current = observations[0]
                                previous = observations[1]
                                
                                logger.info(f"GDP Raw Values - Current: {current}, Previous: {previous}")
                                
                                # Format dates for display
                                current_date = datetime.strptime(data['observations'][0]['date'], '%Y-%m-%d')
                                prev_date = datetime.strptime(data['observations'][1]['date'], '%Y-%m-%d')
                                
                                # Determine trend
                                if abs(current - previous) < 0.1:
                                    trend = 'stable'
                                elif current > previous:
                                    trend = 'accelerating_up' if (current - previous) > 0.5 else 'up'
                                else:
                                    trend = 'accelerating_down' if (previous - current) > 0.5 else 'down'
                                
                                results[name] = {
                                    'value': f"{current:.1f}%",
                                    'previous': f"{previous:.1f}%",
                                    'change_rate': f"{(current - previous):+.1f}%",
                                    'trend': trend,
                                    'last_updated': current_date.strftime('%m/%d/%y'),
                                    'previous_date': prev_date.strftime('%m/%d/%y'),
                                    'history': [
                                        {
                                            'date': datetime.strptime(data['observations'][i]['date'], '%Y-%m-%d').strftime('%m/%d/%y'),
                                            'value': f"{float(observations[i]):.1f}%",
                                            'change': f"{(float(observations[i]) - float(observations[i+1 if i+1 < len(observations) else i])):+.1f}%"
                                        }
                                        for i in range(min(4, len(observations)))
                                    ]
                                }
                                
                                logger.info(f"GDP Results: {results[name]}")
                                
                            elif config.get('yoy', False) and len(observations) >= 13:
                                # Calculate year-over-year change for inflation
                                current = observations[0]
                                year_ago = observations[12]  # 12 months ago
                                
                                logger.info(f"Inflation Raw Values - Current: {current}, Year Ago: {year_ago}")
                                logger.info(f"Inflation Dates - Current: {data['observations'][0]['date']}, Year Ago: {data['observations'][12]['date']}")
                                
                                # Validate values before calculation
                                if current <= 0 or year_ago <= 0:
                                    logger.error(f"Invalid inflation values: current={current}, year_ago={year_ago}")
                                    current_yoy = 0
                                    prev_yoy = 0
                                else:
                                    current_yoy = ((current / year_ago) - 1) * 100
                                
                                previous = observations[1]
                                prev_year_ago = observations[13] if len(observations) > 13 else year_ago
                                
                                # Validate previous values
                                if previous <= 0 or prev_year_ago <= 0:
                                    logger.error(f"Invalid previous inflation values: previous={previous}, prev_year_ago={prev_year_ago}")
                                    prev_yoy = 0
                                else:
                                    prev_yoy = ((previous / prev_year_ago) - 1) * 100
                                
                                # Calculate historical YoY values with improved precision
                                historical_values = []
                                for i in range(min(12, len(observations) - 12)):  # Get up to 12 months of history
                                    if i + 12 < len(observations):
                                        curr = observations[i]
                                        prev = observations[i + 12]
                                        if curr > 0 and prev > 0:
                                            yoy = ((curr / prev) - 1) * 100
                                            historical_values.append({
                                                'date': datetime.strptime(data['observations'][i]['date'], '%Y-%m-%d').strftime('%m/%d/%y'),
                                                'value': f"{yoy:.1f}%",
                                                'change': f"{(yoy - ((observations[i+1] / observations[i+13] if i+13 < len(observations) else prev) - 1) * 100):+.1f}%"
                                            })
                                
                                # Format dates for display
                                current_date = datetime.strptime(data['observations'][0]['date'], '%Y-%m-%d')
                                prev_date = datetime.strptime(data['observations'][1]['date'], '%Y-%m-%d')
                                
                                # Determine trend with more granular thresholds
                                if abs(current_yoy - prev_yoy) < 0.1:
                                    trend = 'stable'
                                elif current_yoy > prev_yoy:
                                    trend = 'accelerating_up' if (current_yoy - prev_yoy) > 0.2 else 'up'
                                else:
                                    trend = 'accelerating_down' if (prev_yoy - current_yoy) > 0.2 else 'down'
                                
                                results[name] = {
                                    'value': f"{current_yoy:.1f}%",
                                    'previous': f"{prev_yoy:.1f}%",
                                    'change_rate': f"{(current_yoy - prev_yoy):+.1f}%",
                                    'trend': trend,
                                    'last_updated': current_date.strftime('%m/%d/%y'),
                                    'previous_date': prev_date.strftime('%m/%d/%y'),
                                    'history': historical_values
                                }
                                
                                logger.info(f"Inflation Results: {results[name]}")
                                
                            else:
                                current = observations[0]
                                previous = observations[1]
                                
                                # Calculate rate of change
                                change = ((current - previous) / abs(previous)) * 100 if previous != 0 else 0
                                
                                # Get historical values
                                historical_values = [
                                    {
                                        'date': datetime.strptime(data['observations'][i]['date'], '%Y-%m-%d').strftime('%m/%d/%y'),
                                        'value': config['transform'](observations[i]),
                                        'change': config['change_transform'](((observations[i] - observations[i+1 if i+1 < len(observations) else i]) / abs(observations[i+1 if i+1 < len(observations) else i])) * 100)
                                    }
                                    for i in range(min(4, len(observations)))
                                ]
                                
                                # Determine trend based on last 4 observations
                                if len(observations) >= 4:
                                    changes = [((observations[i] - observations[i+1]) / observations[i+1]) * 100 
                                             for i in range(len(observations)-1)]
                                    avg_change = sum(changes) / len(changes)
                                    
                                    if abs(avg_change) < 0.05:
                                        trend = 'stable'
                                    elif avg_change > 0:
                                        trend = 'accelerating_up' if changes[0] > avg_change else 'up'
                                    else:
                                        trend = 'accelerating_down' if changes[0] < avg_change else 'down'
                                else:
                                    trend = 'up' if change > 0 else 'down' if change < 0 else 'stable'
                                
                                results[name] = {
                                    'value': config['transform'](current),
                                    'previous': config['transform'](previous),
                                    'change_rate': config['change_transform'](change),
                                    'trend': trend,
                                    'last_updated': datetime.strptime(data['observations'][0]['date'], '%Y-%m-%d').strftime('%m/%d/%y'),
                                    'history': historical_values
                                }
                        else:
                            results[name] = {
                                'value': 'N/A',
                                'previous': 'N/A',
                                'change_rate': 'N/A',
                                'trend': 'neutral',
                                'last_updated': 'N/A'
                            }
                    else:
                        results[name] = {
                            'value': 'N/A',
                            'previous': 'N/A',
                            'change_rate': 'N/A',
                            'trend': 'neutral',
                            'last_updated': 'N/A'
                        }
                    
                except Exception as e:
                    logger.error(f"Error fetching {name}: {e}")
                    results[name] = {
                        'value': 'N/A',
                        'previous': 'N/A',
                        'change_rate': 'N/A',
                        'trend': 'neutral',
                        'last_updated': 'N/A'
                    }
            
            results['Last Updated'] = datetime.now().strftime('%Y-%m-%d')
            self._save_to_cache(cache_key, results)
            return results
            
        except Exception as e:
            logger.error(f"Error fetching economic indicators: {e}")
            return {
                'GDP': {'value': 'N/A', 'previous': 'N/A', 'change_rate': 'N/A', 'trend': 'neutral', 'last_updated': 'N/A'},
                'Inflation': {'value': 'N/A', 'previous': 'N/A', 'change_rate': 'N/A', 'trend': 'neutral', 'last_updated': 'N/A'},
                'Unemployment': {'value': 'N/A', 'previous': 'N/A', 'change_rate': 'N/A', 'trend': 'neutral', 'last_updated': 'N/A'},
                'Last Updated': datetime.now().strftime('%Y-%m-%d')
            }
    
    def fetch_economic_history(self, indicator_id: str, limit: int = 20) -> Dict:
        """Fetch historical economic data"""
        # Include date in cache key for daily refresh of economic data
        today = datetime.now().strftime('%Y-%m-%d')
        cache_key = f"economic_history_{indicator_id}_{limit}_{today}"
        
        if not self.force_refresh:
            cached_data = self._load_from_cache(cache_key, max_age_hours=24)  # Daily refresh
            if cached_data:
                return cached_data
        
        try:
            if not self.fred_api_key:
                logger.warning("FRED API key not found")
                return {'labels': [], 'values': [], 'title': indicator_id}
            
            # For bond yields, use weekly frequency
            frequency = 'w' if indicator_id in ['DGS10', 'DGS2'] else None
            params = {
                'series_id': indicator_id,
                'api_key': self.fred_api_key,
                'file_type': 'json',
                'sort_order': 'desc',
                'limit': limit * 5 if frequency == 'w' else limit,  # Fetch more data points for weekly aggregation
                'frequency': frequency
            }
            
            response = requests.get(
                "https://api.stlouisfed.org/fred/series/observations",
                params=params
            )
            data = response.json()
            
            if 'observations' in data and data['observations']:
                observations = list(reversed(data['observations']))
                valid_observations = [(obs['date'], float(obs['value'])) 
                                    for obs in observations 
                                    if obs['value'] != '.' and obs['value'].strip()]
                
                if valid_observations:
                    # For weekly data, take every 5th point to get weekly values
                    if frequency == 'w':
                        valid_observations = valid_observations[::5][:limit]
                    
                    result = {
                        'labels': [date for date, _ in valid_observations],
                        'values': [value for _, value in valid_observations],
                        'title': 'Treasury Yields and Spread Analysis' if indicator_id in ['DGS10', 'DGS2'] else indicator_id
                    }
                    self._save_to_cache(cache_key, result)
                    return result
            
            logger.warning(f"No valid data found for indicator {indicator_id}")
            return {'labels': [], 'values': [], 'title': indicator_id}
            
        except Exception as e:
            logger.error(f"Error fetching economic history for {indicator_id}: {e}")
            return {'labels': [], 'values': [], 'title': indicator_id}
    
    def fetch_market_status(self) -> Dict:
        """Fetch current market status"""
        cache_key = f"market_status_{datetime.now().strftime('%Y-%m-%d_%H')}"
        
        if not self.force_refresh:
            cached_data = self._load_from_cache(cache_key, max_age_hours=1)
            if cached_data:
                return cached_data
        
        try:
            # Get current time in ET
            et_time = datetime.now(pytz.timezone('US/Eastern'))
            current_time = et_time.strftime('%H:%M')
            
            # Define market hours
            pre_market_start = '04:00'
            market_open = '09:30'
            market_close = '16:00'
            after_hours_close = '20:00'
            
            # Determine market status
            if current_time < pre_market_start:
                status = 'Closed'
                hours = 'Pre-Market Trading starts at 4:00 AM ET'
            elif current_time < market_open:
                status = 'Pre-Market'
                hours = 'Regular Trading starts at 9:30 AM ET'
            elif current_time < market_close:
                status = 'Open'
                hours = 'Regular Trading Hours (9:30 AM - 4:00 PM ET)'
            elif current_time < after_hours_close:
                status = 'After-Hours'
                hours = 'After-Hours Trading (until 8:00 PM ET)'
            else:
                status = 'Closed'
                hours = 'Market Closed - Opens at 4:00 AM ET'
            
            result = {
                'status': status,
                'hours': hours,
                'current_time_et': current_time,
                'last_updated': et_time.strftime('%Y-%m-%d %H:%M:%S %Z')
            }
            
            self._save_to_cache(cache_key, result)
            return result
            
        except Exception as e:
            logger.error(f"Error fetching market status: {e}")
            return {
                'status': 'Unknown',
                'hours': 'Status Unavailable',
                'current_time_et': datetime.now().strftime('%H:%M'),
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
    
    def fetch_economic_events(self) -> Dict:
        """Fetch economic calendar events for today"""
        cache_key = f"economic_events_{datetime.now().strftime('%Y-%m-%d')}"
        
        if not self.force_refresh:
            cached_data = self._load_from_cache(cache_key)
            if cached_data:
                return cached_data
        
        try:
            # For now, return placeholder data
            # In a real implementation, this would fetch from an economic calendar API
            events = []
            
            # Add Fed events if available
            if self.fred_api_key:
                try:
                    response = requests.get(
                        "https://api.stlouisfed.org/fred/releases/dates",
                        params={
                            'api_key': self.fred_api_key,
                            'file_type': 'json',
                            'limit': 5,
                            'realtime_start': datetime.now().strftime('%Y-%m-%d')
                        }
                    )
                    data = response.json()
                    
                    if 'release_dates' in data:
                        for release in data['release_dates']:
                            events.append({
                                'time': release.get('hour', '00:00'),
                                'description': f"Fed: {release.get('name', 'Economic Release')}",
                                'importance': 'high'
                            })
                except Exception as e:
                    logger.error(f"Error fetching Fed events: {e}")
            
            result = {
                'events': events,
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            self._save_to_cache(cache_key, result)
            return result
            
        except Exception as e:
            logger.error(f"Error fetching economic events: {e}")
            return {
                'events': [],
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
    
    def fetch_inflation_yoy_history(self, limit: int = 24) -> Dict:
        """Fetch YoY inflation rates (CPI) for the last N months."""
        # Fetch more than limit to allow YoY calculation
        raw = self.fetch_economic_history('CPIAUCSL', limit + 12)
        labels = raw['labels']
        values = raw['values']
        yoy_labels = []
        yoy_values = []
        for i in range(len(values) - 12):
            current = values[i + 12]
            year_ago = values[i]
            if current > 0 and year_ago > 0:
                yoy = ((current / year_ago) - 1) * 100
                yoy_labels.append(labels[i + 12])
                yoy_values.append(round(yoy, 2))
        return {'labels': yoy_labels, 'values': yoy_values, 'title': 'Inflation YoY'} 