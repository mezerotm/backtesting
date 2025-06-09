"""
Market data fetcher for economic indicators and market data.
"""

import os
import json
import logging
import requests
import pandas as pd
import pytz
import time
import yfinance as yf
from datetime import datetime, timedelta
from typing import Dict, Optional
from polygon import RESTClient
from polygon.rest.models import Timeframe, Sort, Order
from workflows.base_fetcher import BaseFetcher
from utils.config import POLYGON_API_KEY, FRED_API_KEY, TRADING_ECON_API_KEY
from utils.most_recent import with_most_recent_data

logger = logging.getLogger(__name__)

class MarketDataFetcher(BaseFetcher):
    """Fetches market data from various sources."""
    
    def __init__(self, force_refresh: bool = False):
        """Initialize the data fetcher.
        
        Args:
            force_refresh (bool): Whether to force refresh data from source
        """
        super().__init__(force_refresh=force_refresh, cache_subdir='market')
        self.force_refresh = force_refresh
        self.client = RESTClient(POLYGON_API_KEY)  # Initialize Polygon client with API key
        self.fred_api_key = FRED_API_KEY
    
    def _yahoo_rate_limited(self):
        now = time.time()
        # Remove requests older than window
        self._yahoo_last_requests = [t for t in self._yahoo_last_requests if now - t < self._yahoo_window_seconds]
        if len(self._yahoo_last_requests) >= self._yahoo_max_requests:
            return True
        self._yahoo_last_requests.append(now)
        return False

    def _get_yahoo_price(self, ticker):
        if self._yahoo_rate_limited():
            logger.warning(f"Yahoo Finance rate limit reached, skipping {ticker}")
            return 'N/A', 'N/A', 'neutral'
        try:
            data = yf.Ticker(ticker)
            hist = data.history(period="2d")
            if len(hist) >= 2:
                current = hist['Close'][-1]
                previous = hist['Close'][-2]
                change = ((current - previous) / previous) * 100 if previous != 0 else 0
                return f"{current:.2f}", f"{change:+.2f}%", 'up' if change > 0 else 'down' if change < 0 else 'neutral'
        except Exception as e:
            logger.error(f"Yahoo Finance error for {ticker}: {e}")
        return 'N/A', 'N/A', 'neutral'

    @with_most_recent_data(max_days=7)
    def get_polygon_agg(self, ticker, date=None):
        aggs = self.client.get_aggs(
            ticker=ticker,
            multiplier=1,
            timespan="day",
            from_=date,
            to=date,
            adjusted=True
        )
        return aggs[0] if aggs else None

    def fetch_market_indices(self) -> Dict:
        """Fetch major market indices data: Polygon first, then FRED, then Yahoo Finance (rate-limited)."""
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
                return {}
            # Index definitions: (Display Name, Polygon ticker, Description, Group)
            indices = [
                ("S&P 500", "SPY", "SPDR S&P 500 ETF", "Large Cap"),
                ("Dow Jones", "DIA", "SPDR Dow Jones Industrial Avg", "Large Cap"),
                ("Nasdaq-100", "QQQ", "Invesco QQQ ETF", "Large Cap"),
                ("Russell 2000", "IWM", "iShares Russell 2000 ETF", "Small Cap"),
                ("S&P 400 MidCap", "MDY", "SPDR S&P MidCap 400 ETF", "Mid Cap"),
                ("S&P 500 Growth", "IVW", "iShares S&P 500 Growth ETF", "Growth"),
                ("S&P 500 Value", "IVE", "iShares S&P 500 Value ETF", "Value"),
                ("VIX", "VIXY", "Short-term VIX futures ETF", "Volatility"),
            ]
            results = {}
            for name, polygon_ticker, description, group in indices:
                value, change, direction = None, None, 'neutral'
                try:
                    # Get most recent close (up to 7 days back)
                    current_agg, current_date = self.get_polygon_agg(polygon_ticker)
                    # Get previous close (the most recent day before current_date)
                    if current_date:
                        prev_date_dt = datetime.strptime(current_date, '%Y-%m-%d') - timedelta(days=1)
                        skip_days = (datetime.now() - prev_date_dt).days
                        prev_agg, prev_date = self.get_polygon_agg(polygon_ticker, date=prev_date_dt.strftime('%Y-%m-%d'))
                    else:
                        prev_agg, prev_date = None, None
                    if current_agg:
                        current = current_agg.close
                        previous = prev_agg.close if prev_agg else current
                        logger.debug(f"Current close for {polygon_ticker} ({current_date}): {current}")
                        logger.debug(f"Previous close for {polygon_ticker} ({prev_date}): {previous}")
                        change_val = ((current - previous) / previous) * 100 if previous != 0 else 0
                        value = f"{current:.2f}"
                        change = f"{change_val:+.2f}%"
                        direction = 'up' if change_val > 0 else 'down' if change_val < 0 else 'neutral'
                    else:
                        logger.warning(f"No aggregation data returned for {polygon_ticker} in last 7 days")
                except Exception as e:
                    logger.error(f"Polygon error for {name} ({polygon_ticker}): {e}", exc_info=True)
                    value = 'N/A'
                    change = 'N/A'
                    direction = 'neutral'
                if value is None:
                    logger.warning(f"Setting value to 'N/A' for {name} ({polygon_ticker}) due to missing data.")
                    value = 'N/A'
                    change = 'N/A'
                    direction = 'neutral'

                # Group results
                if group not in results:
                    results[group] = []
                results[group].append({
                    'name': name,
                    'value': value,
                    'change': change,
                    'direction': direction,
                    'description': description,
                    'date': current_date,
                    'previous_date': prev_date
                })
            logger.info(f"Market Indices Results: {results}")
            self._save_to_cache(cache_key, results)
            return results
        except Exception as e:
            logger.error(f"Error fetching market indices: {e}")
            return {}
    
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
    
    def fetch_economic_history(self, series_id: str, periods: int) -> Optional[Dict]:
        """Fetch economic data history from FRED."""
        try:
            # TODO: Implement FRED API call
            # For now, return mock data
            dates = pd.date_range(end=datetime.now(), periods=periods, freq='ME')
            values = [2.1, 2.3, 2.0, 1.8, 1.9, 2.2, 2.4, 2.1, 2.0, 1.9, 2.1, 2.3]
            return {
                'labels': [d.strftime('%Y-%m') for d in dates],
                'values': values[:periods]
            }
        except Exception as e:
            print(f"Error fetching economic history for {series_id}: {e}")
            return None
    
    def fetch_inflation_yoy_history(self, periods: int) -> Optional[Dict]:
        """Fetch year-over-year inflation history."""
        try:
            # TODO: Implement FRED API call
            # For now, return mock data
            dates = pd.date_range(end=datetime.now(), periods=periods, freq='ME')
            values = [3.1, 3.2, 3.0, 2.9, 2.8, 2.7, 2.6, 2.5, 2.4, 2.3, 2.2, 2.1]
            return {
                'labels': [d.strftime('%Y-%m') for d in dates],
                'values': values[:periods]
            }
        except Exception as e:
            print(f"Error fetching inflation history: {e}")
            return None
    
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
        """Fetch top 5 most active tickers and their latest news as events for the dashboard."""
        logger.info("Fetching Polygon market movers and news for events section")
        events = []
        try:
            # 1. Get top 5 most active tickers using requests
            url = f"https://api.polygon.io/v2/snapshot/locale/us/markets/stocks/most_active?apiKey={POLYGON_API_KEY}"
            resp = requests.get(url)
            resp.raise_for_status()
            movers = resp.json().get('tickers', [])[:5]
            tickers = [item['ticker'] for item in movers]

            for ticker in tickers:
                # 2. Get latest news for each ticker using the client
                news_items = self.client.list_ticker_news(ticker, limit=1)
                if news_items:
                    news = news_items[0]
                    event = {
                        'time': news.published_utc[11:16] if hasattr(news, 'published_utc') else '',
                        'country': 'US',
                        'description': f"{ticker}: {news.title}",
                        'importance': 'High',
                        'actual': None,
                        'forecast': None,
                        'previous': None,
                        'url': getattr(news, 'article_url', None)
                    }
                    events.append(event)
                    logger.debug(f"Added event for {ticker}: {news.title}")
        except Exception as e:
            logger.error(f"Error fetching Polygon events: {e}")

        if not events:
            logger.warning("No Polygon events found for today.")
            return None

        result = {
            'events': events,
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
        logger.info(f"Returning {len(events)} Polygon events for today")
        return result
    
    def get_gdp_data(self, periods: int = 8) -> Dict:
        """Get GDP growth rate data from FRED."""
        try:
            # Get GDP data from FRED
            response = requests.get(
                "https://api.stlouisfed.org/fred/series/observations",
                params={
                    'series_id': 'A191RL1Q225SBEA',  # Real GDP Growth Rate
                    'api_key': self.fred_api_key,
                    'file_type': 'json',
                    'sort_order': 'desc',
                    'limit': periods
                }
            )
            data = response.json()
            
            if 'observations' in data and len(data['observations']) > 0:
                dates = [datetime.strptime(obs['date'], '%Y-%m-%d') for obs in data['observations']]
                values = [float(obs['value']) for obs in data['observations'] if obs['value'] != '.']
                
                # Format for chart
                data = {
                    'labels': [f"Q{(i%4)+1} {d.year}" for i, d in enumerate(dates)],
                    'values': values
                }
                print(f"[DEBUG] Raw GDP data: {data}")
                return data
                
        except Exception as e:
            print(f"ERROR - Failed to get GDP data: {e}")
        return {'labels': [], 'values': []}
    
    def get_inflation_data(self, periods: int = 8) -> Dict:
        """Get inflation rate data from FRED."""
        try:
            # Get inflation data from FRED
            response = requests.get(
                "https://api.stlouisfed.org/fred/series/observations",
                params={
                    'series_id': 'CPIAUCSL',  # Consumer Price Index
                    'api_key': self.fred_api_key,
                    'file_type': 'json',
                    'sort_order': 'desc',
                    'limit': periods + 12  # Need extra months for YoY calculation
                }
            )
            data = response.json()
            
            if 'observations' in data and len(data['observations']) > 0:
                dates = [datetime.strptime(obs['date'], '%Y-%m-%d') for obs in data['observations']]
                values = [float(obs['value']) for obs in data['observations'] if obs['value'] != '.']
                
                # Calculate YoY change
                yoy_values = []
                for i in range(len(values)):
                    if i + 12 < len(values):  # Need 12 months of data for YoY
                        yoy = ((values[i] - values[i + 12]) / values[i + 12]) * 100
                        yoy_values.append(yoy)
                
                # Format for chart
                data = {
                    'labels': [d.strftime('%Y-%m') for d in dates[:len(yoy_values)]],
                    'values': yoy_values
                }
                print(f"[DEBUG] Raw inflation data: {data}")
                return data
                
        except Exception as e:
            print(f"ERROR - Failed to get inflation data: {e}")
        return {'labels': [], 'values': []}
    
    def get_unemployment_data(self, periods: int = 8) -> Dict:
        """Get unemployment rate data from FRED."""
        try:
            # Get unemployment data from FRED
            response = requests.get(
                "https://api.stlouisfed.org/fred/series/observations",
                params={
                    'series_id': 'UNRATE',  # Unemployment Rate
                    'api_key': self.fred_api_key,
                    'file_type': 'json',
                    'sort_order': 'desc',
                    'limit': periods
                }
            )
            data = response.json()
            
            if 'observations' in data and len(data['observations']) > 0:
                dates = [datetime.strptime(obs['date'], '%Y-%m-%d') for obs in data['observations']]
                values = [float(obs['value']) for obs in data['observations'] if obs['value'] != '.']
                
                # Format for chart
                data = {
                    'labels': [d.strftime('%Y-%m') for d in dates],
                    'values': values
                }
                print(f"[DEBUG] Raw unemployment data: {data}")
                return data
                
        except Exception as e:
            print(f"ERROR - Failed to get unemployment data: {e}")
        return {'labels': [], 'values': []}
    
    def get_bond_data(self, periods: int = 24, frequency: str = 'monthly') -> Dict:
        """Get bond yield data from FRED, with debugging and frequency control."""
        try:
            # Set FRED frequency
            freq_map = {'monthly': 'm', 'yearly': 'a'}
            freq_param = freq_map.get(frequency, 'm')
            print(f"[DEBUG] Fetching bond data: periods={periods}, frequency={frequency}, freq_param={freq_param}")
            # Get 10Y Treasury yield
            params_10y = {
                'series_id': 'DGS10',
                'api_key': self.fred_api_key,
                'file_type': 'json',
                'sort_order': 'desc',
                'limit': periods,
                'frequency': freq_param
            }
            response_10y = requests.get(
                "https://api.stlouisfed.org/fred/series/observations",
                params=params_10y
            )
            data_10y = response_10y.json()
            # Get 2Y Treasury yield
            params_2y = {
                'series_id': 'DGS2',
                'api_key': self.fred_api_key,
                'file_type': 'json',
                'sort_order': 'desc',
                'limit': periods,
                'frequency': freq_param
            }
            response_2y = requests.get(
                "https://api.stlouisfed.org/fred/series/observations",
                params=params_2y
            )
            data_2y = response_2y.json()
            if ('observations' in data_10y and len(data_10y['observations']) > 0 and
                'observations' in data_2y and len(data_2y['observations']) > 0):
                dates = [datetime.strptime(obs['date'], '%Y-%m-%d') for obs in data_10y['observations']]
                values_10y = [float(obs['value']) for obs in data_10y['observations'] if obs['value'] != '.']
                values_2y = [float(obs['value']) for obs in data_2y['observations'] if obs['value'] != '.']
                print(f"[DEBUG] 10Y count: {len(values_10y)}, 2Y count: {len(values_2y)}")
                print(f"[DEBUG] 10Y dates: {dates}")
                print(f"[DEBUG] 10Y values: {values_10y}")
                print(f"[DEBUG] 2Y values: {values_2y}")
                # Format for chart
                data = {
                    'labels': [d.strftime('%Y') if frequency == 'yearly' else d.strftime('%Y-%m') for d in dates],
                    'values': values_10y,
                    'values_2y': values_2y
                }
                print(f"[DEBUG] Final bond chart labels: {data['labels']}")
                return data
        except Exception as e:
            print(f"ERROR - Failed to get bond data: {e}")
        return {'labels': [], 'values': [], 'values_2y': []}
    
    def fetch_top_movers_and_news(self, limit: int = 5) -> list:
        """Fetch top market movers and their latest news from Polygon."""
        movers = []
        try:
            url = f"https://api.polygon.io/v2/snapshot/locale/us/markets/stocks/most_active?apiKey={POLYGON_API_KEY}"
            resp = requests.get(url)
            resp.raise_for_status()
            data = resp.json()
            tickers = data.get('tickers', [])[:limit]
            for item in tickers:
                ticker = item.get('ticker')
                name = item.get('name', ticker)
                # Fetch latest news for this ticker
                news_url = f"https://api.polygon.io/v2/reference/news?ticker={ticker}&limit=1&apiKey={POLYGON_API_KEY}"
                news_resp = requests.get(news_url)
                news_data = news_resp.json()
                if news_data.get('results'):
                    news = news_data['results'][0]
                    headline = news.get('title', '')
                    url = news.get('article_url', '')
                    published_utc = news.get('published_utc', '')
                else:
                    headline = ''
                    url = ''
                    published_utc = ''
                movers.append({
                    'ticker': ticker,
                    'name': name,
                    'headline': headline,
                    'url': url,
                    'published_utc': published_utc
                })
        except Exception as e:
            print(f"Error fetching top movers and news: {e}")
        return movers 