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
from config.backend.settings import POLYGON_API_KEY, FRED_API_KEY, TRADING_ECON_API_KEY
from server.utils.most_recent import with_most_recent_data

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
        # Initialize Polygon client with API key
        self.client = RESTClient(POLYGON_API_KEY)
        self.fred_api_key = FRED_API_KEY

    def _yahoo_rate_limited(self):
        now = time.time()
        # Remove requests older than window
        self._yahoo_last_requests = [
            t for t in self._yahoo_last_requests if now -
            t < self._yahoo_window_seconds]
        if len(self._yahoo_last_requests) >= self._yahoo_max_requests:
            return True
        self._yahoo_last_requests.append(now)
        return False

    def _get_yahoo_price(self, ticker):
        if self._yahoo_rate_limited():
            logger.warning(
                f"Yahoo Finance rate limit reached, skipping {ticker}")
            return 'N/A', 'N/A', 'neutral'
        try:
            data = yf.Ticker(ticker)
            hist = data.history(period="2d")
            if len(hist) >= 2:
                current = hist['Close'][-1]
                previous = hist['Close'][-2]
                change = ((current - previous) / previous) * \
                    100 if previous != 0 else 0
                return f"{current:.2f}", f"{change:+.2f}%", 'up' if change > 0 else 'down' if change < 0 else 'neutral'
        except Exception as e:
            logger.error(f"Yahoo Finance error for {ticker}: {e}")
        return 'N/A', 'N/A', 'neutral'

    @with_most_recent_data(max_days=7)
    def get_polygon_agg(self, ticker, date=None):
        logger = logging.getLogger(__name__)
        logger.debug(f"get_polygon_agg: ticker={ticker}, date={date}")

        # Check if we're in after-hours
        et_time = datetime.now(pytz.timezone('US/Eastern'))
        is_after_hours = et_time.hour < 9 or et_time.hour >= 16
        is_weekend = et_time.weekday() >= 5

        try:
            aggs = self.client.get_aggs(
                ticker=ticker,
                multiplier=1,
                timespan="day",
                from_=date,
                to=date,
                adjusted=True
            )
            logger.debug(
                f"get_polygon_agg: aggs for {ticker} on {date}: {aggs}")
            return aggs[0] if aggs else None
        except Exception as e:
            error_str = str(e)

            # Handle after-hours authorization errors gracefully
            if "NOT_AUTHORIZED" in error_str and (
                    is_after_hours or is_weekend):
                logger.info(
                    f"After-hours data not available for {ticker} on {date} - this is expected outside market hours")

                # Try to get the most recent available data
                if not date:
                    # If no specific date requested, try to get the last
                    # available trading day
                    try:
                        # Get data from the last 5 days to find the most recent
                        for days_back in range(1, 6):
                            try_date = (
                                datetime.now() -
                                timedelta(
                                    days=days_back)).strftime('%Y-%m-%d')
                            try:
                                fallback_aggs = self.client.get_aggs(
                                    ticker=ticker,
                                    multiplier=1,
                                    timespan="day",
                                    from_=try_date,
                                    to=try_date,
                                    adjusted=True
                                )
                                if fallback_aggs:
                                    logger.info(
                                        f"Using fallback data for {ticker} from {try_date}")
                                    return fallback_aggs[0]
                            except BaseException:
                                continue
                    except Exception as fallback_error:
                        logger.warning(
                            f"Fallback data fetch failed for {ticker}: {fallback_error}")

                return None
            else:
                logger.error(
                    f"get_polygon_agg: Exception for {ticker} on {date}: {e}")
                return None

    def fetch_market_indices(self) -> Dict:
        """Fetch major market indices data: Polygon first, then FRED, then Yahoo Finance (rate-limited)."""
        now = datetime.now()
        et_time = datetime.now(pytz.timezone('US/Eastern'))
        is_market_hours = 9 <= et_time.hour < 16
        cache_key = (
            f"market_indices_{now.strftime('%Y-%m-%d_%H_%M')}" if is_market_hours else f"market_indices_{now.strftime('%Y-%m-%d_%H')}")
        if not self.force_refresh:
            max_age = 5 / 60 if is_market_hours else 1
            cached_data = self._load_from_cache(
                cache_key, max_age_hours=max_age)
            if cached_data:
                return cached_data
        try:
            if not self.fred_api_key:
                logger.warning("FRED API key not found")
                return {}
            # Index definitions: (Display Name, Polygon ticker, Description,
            # Group)
            indices = [
                ("S&P 500", "SPY", "SPDR S&P 500 ETF", "Large Cap"),
                ("Dow Jones", "DIA", "SPDR Dow Jones Industrial Avg", "Large Cap"),
                ("Nasdaq-100", "QQQ", "Invesco QQQ ETF", "Large Cap"),
                ("S&P 400 MidCap", "MDY", "SPDR S&P MidCap 400 ETF", "Mid Cap"),
                ("Russell 2000", "IWM", "iShares Russell 2000 ETF", "Small Cap"),
                ("S&P 500 Growth", "IVW", "iShares S&P 500 Growth ETF", "Growth"),
                ("S&P 500 Value", "IVE", "iShares S&P 500 Value ETF", "Value"),
                ("Dollar Index", "UUP", "US Dollar Index ETF (UUP)", "FX"),
                ("Oil (WTI)", "USO", "US Oil Fund ETF (USO)", "Commodities"),
                ("VIX", "VIXY", "Short-term VIX futures ETF", "Volatility"),
            ]
            results = {}
            for name, polygon_ticker, description, group in indices:
                value, change, direction = None, None, 'neutral'
                try:
                    # Get the most recent valid day for current
                    # Step 1: get current trading day data (uses @with_most_recent_data decorator)
                    current_agg, current_date = self.get_polygon_agg(
                        polygon_ticker)
                    prev_agg, prev_date = None, None

                    # Step 2: find previous trading day by querying Polygon
                    # directly (bypass the decorator which overrides date)
                    if current_date and current_agg:
                        current_dt = datetime.strptime(
                            current_date, '%Y-%m-%d')
                        attempted_prev_dates = []
                        for offset in range(1, 11):
                            prev_date_dt = current_dt - timedelta(days=offset)
                            try_date = prev_date_dt.strftime('%Y-%m-%d')
                            try:
                                prev_aggs = self.client.get_aggs(
                                    ticker=polygon_ticker,
                                    multiplier=1,
                                    timespan="day",
                                    from_=try_date,
                                    to=try_date,
                                    adjusted=True
                                )
                                agg = prev_aggs[0] if prev_aggs else None
                            except BaseException:
                                agg = None
                            # Determine actual trading date from Polygon's returned timestamp
                            agg_date = None
                            if agg and hasattr(agg, 'timestamp'):
                                ts = getattr(agg, 'timestamp', None)
                                if hasattr(ts, 'strftime'):
                                    agg_date = ts.strftime('%Y-%m-%d')
                                elif isinstance(ts, (int, float)):
                                    agg_date = datetime.fromtimestamp(
                                        ts / 1000).strftime('%Y-%m-%d')
                            attempted_prev_dates.append(
                                (try_date, agg_date, agg.close if agg else None))
                            # Only accept if agg_date is strictly before
                            # current_date
                            if agg and agg_date and agg_date < current_date:
                                prev_agg, prev_date = agg, agg_date
                                break
                        logger.info(
                            f"Index: {name} | Attempted previous dates: {attempted_prev_dates}")
                    # Logging for debugging
                    logger.info(
                        f"Index: {name} | Current date: {current_date}, Previous date: {prev_date}")
                    if current_agg and prev_agg and current_date != prev_date:
                        current = current_agg.close
                        previous = prev_agg.close
                        logger.info(
                            f"Index: {name} | Current value: {current}, Previous value: {previous}")
                        change_val = (
                            (current - previous) / previous) * 100 if previous != 0 else 0
                        value = f"{current:.2f}"
                        change = f"{change_val:+.2f}%"
                        direction = 'up' if change_val > 0 else 'down' if change_val < 0 else 'neutral'
                    elif current_agg:
                        current = current_agg.close
                        value = f"{current:.2f}"
                        change = 'N/A'
                        direction = 'neutral'
                        logger.warning(
                            f"Index: {name} | Only one valid trading day found or duplicate dates. Change set to N/A.")
                    else:
                        value = 'N/A'
                        change = 'N/A'
                        direction = 'neutral'
                        logger.warning(
                            f"Index: {name} | No valid trading data found.")
                except Exception as e:
                    value = 'N/A'
                    change = 'N/A'
                    direction = 'neutral'
                    logger.error(f"Index: {name} | Exception: {e}")
                if group not in results:
                    results[group] = []
                results[group].append({
                    'name': name,
                    'value': value,
                    'change': change,
                    'direction': direction,
                    'description': description,
                    'date': current_date if current_agg else None,
                    'previous_date': prev_date if prev_agg else None
                })
            self._save_to_cache(cache_key, results)

            # --- Add 10Y Treasury to indices (Rates group) using FRED ---
            try:
                fred_api_key = self.fred_api_key
                if fred_api_key:
                    response = requests.get(
                        "https://api.stlouisfed.org/fred/series/observations",
                        params={
                            'series_id': 'DGS10',
                            'api_key': fred_api_key,
                            'file_type': 'json',
                            'sort_order': 'desc',
                            'limit': 7
                        }
                    )
                    data = response.json()
                    obs = [
                        o for o in data.get(
                            'observations',
                            []) if o['value'] != '.']
                    if len(obs) >= 2:
                        current = float(obs[0]['value'])
                        previous = float(obs[1]['value'])
                        change_val = (
                            (current - previous) / previous) * 100 if previous != 0 else 0
                        value = f"{current:.2f}"
                        change = f"{change_val:+.2f}%"
                        direction = 'up' if change_val > 0 else 'down' if change_val < 0 else 'neutral'
                        ten_year_idx = {
                            'name': '10Y Treasury',
                            'value': value,
                            'change': change,
                            'direction': direction,
                            'description': '10-Year US Treasury Yield',
                            'date': obs[0]['date'],
                            'previous_date': obs[1]['date']
                        }
                    else:
                        ten_year_idx = {
                            'name': '10Y Treasury',
                            'value': 'N/A',
                            'change': 'N/A',
                            'direction': 'neutral',
                            'description': '10-Year US Treasury Yield',
                            'date': None,
                            'previous_date': None
                        }
                    if 'Rates' not in results:
                        results['Rates'] = []
                    # Remove any existing 10Y Treasury
                    results['Rates'] = [idx for idx in results['Rates']
                                        if idx.get('name') != '10Y Treasury']
                    results['Rates'].append(ten_year_idx)
            except Exception as e:
                logger.error(f"Error adding 10Y Treasury to indices: {e}")

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
            cached_data = self._load_from_cache(
                cache_key, max_age_hours=24)  # Daily refresh
            if cached_data:
                logger.info("Using cached economic indicators data")
                return cached_data

        try:
            if not self.fred_api_key:
                logger.warning("FRED API key not found")
                return {
                    'GDP': {
                        'value': 'N/A',
                        'previous': 'N/A',
                        'change_rate': 'N/A',
                        'trend': 'neutral',
                        'last_updated': 'N/A'},
                    'Inflation': {
                        'value': 'N/A',
                        'previous': 'N/A',
                        'change_rate': 'N/A',
                        'trend': 'neutral',
                        'last_updated': 'N/A'},
                    'Unemployment': {
                        'value': 'N/A',
                        'previous': 'N/A',
                        'change_rate': 'N/A',
                        'trend': 'neutral',
                        'last_updated': 'N/A'},
                    'Last Updated': datetime.now().strftime('%Y-%m-%d')}

            indicators = {
                'GDP': {
                    # Real GDP Growth Rate (Percent Change SAAR)
                    'series_id': 'A191RL1Q225SBEA',
                    # Already in percent
                    'transform': lambda x: f"{float(x):.1f}%",
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

                    if 'observations' in data and len(
                            data['observations']) >= 2:
                        # Filter out '.' values AND track the original indices
                        # so we can map indices back to actual dates
                        raw_obs = data['observations']
                        observations = [
                            float(obs['value']) for obs in raw_obs if obs['value'] != '.']
                        observation_dates = [
                            obs['date'] for obs in raw_obs if obs['value'] != '.']

                        if len(observations) >= 2:
                            if name == 'GDP':
                                # For GDP, we're now using the direct growth
                                # rate series
                                current = observations[0]
                                previous = observations[1]

                                logger.info(
                                    f"GDP Raw Values - Current: {current}, Previous: {previous}")

                                # Format dates for display
                                current_date = datetime.strptime(
                                    observation_dates[0], '%Y-%m-%d')
                                prev_date = datetime.strptime(
                                    observation_dates[1], '%Y-%m-%d')

                                # Determine trend
                                if abs(current - previous) < 0.1:
                                    trend = 'stable'
                                elif current > previous:
                                    trend = 'accelerating_up' if (
                                        current - previous) > 0.5 else 'up'
                                else:
                                    trend = 'accelerating_down' if (
                                        previous - current) > 0.5 else 'down'

                                results[name] = {
                                    'value': f"{current:.1f}%",
                                    'previous': f"{previous:.1f}%",
                                    'change_rate': f"{(current - previous):+.1f}%",
                                    'trend': trend,
                                    'last_updated': current_date.strftime('%m/%d/%y'),
                                    'previous_date': prev_date.strftime('%m/%d/%y'),
                                    'history': [
                                        {
                                            'date': datetime.strptime(observation_dates[i], '%Y-%m-%d').strftime('%m/%d/%y'),
                                            'value': f"{float(observations[i]):.1f}%",
                                            'change': f"{(float(observations[i]) - float(observations[i + 1 if i + 1 < len(observations) else i])):+.1f}%"
                                        }
                                        for i in range(min(4, len(observations)))
                                    ]
                                }

                                logger.info(f"GDP Results: {results[name]}")

                            elif config.get('yoy', False) and len(
                                    observations) >= 13:
                                # Calculate year-over-year change for inflation
                                # Use date-aware lookback to find the value ~12
                                # months prior
                                def _find_yoy_value(
                                        obs_idx, obs_list, date_list):
                                    """Find the value ~365 days before the observation at obs_idx."""
                                    target_date = datetime.strptime(
                                        date_list[obs_idx], '%Y-%m-%d')
                                    target_year_ago = target_date - \
                                        timedelta(days=365)

                                    best_idx = None
                                    best_diff = timedelta(days=365)
                                    for j in range(obs_idx + 1, len(date_list)):
                                        d = datetime.strptime(
                                            date_list[j], '%Y-%m-%d')
                                        diff = abs(
                                            target_year_ago - d)
                                        if diff < best_diff:
                                            best_diff = diff
                                            best_idx = j
                                    # Only accept if within 45 days of 12 months
                                    if best_idx is not None and best_diff.days < 45:
                                        return obs_list[best_idx]
                                    return None

                                current = observations[0]
                                year_ago = _find_yoy_value(
                                    0, observations, observation_dates)

                                current_date = datetime.strptime(
                                    observation_dates[0], '%Y-%m-%d')
                                # Determine approximate year-ago date for
                                # logging only
                                logger.info(
                                    f"Inflation Raw Values - Current: {current}, Year Ago: {year_ago}")
                                logger.info(
                                    f"Inflation Dates - Current: {observation_dates[0]}, Year Ago: year_ago_raw={year_ago}")

                                # Validate values before calculation
                                def _safe_yoy(curr_val, prev_val):
                                    if curr_val is None or prev_val is None:
                                        return 0
                                    if prev_val <= 0.001 or curr_val <= 0:
                                        logger.error(
                                            f"Invalid inflation values: current={curr_val}, year_ago={prev_val}")
                                        return 0
                                    try:
                                        result = (
                                            (curr_val / prev_val) - 1) * 100
                                        # Sanity check: CPI YoY should be
                                        # roughly -5% to 15%
                                        if result > 100 or result < -100:
                                            logger.error(
                                                f"Unrealistic YoY change {result:.1f}% for CPI values: current={curr_val}, prev={prev_val}")
                                            return 0
                                        return result
                                    except (ZeroDivisionError,
                                            ValueError):
                                        return 0

                                current_yoy = _safe_yoy(current, year_ago)

                                previous = observations[1]
                                prev_year_ago = _find_yoy_value(
                                    1, observations, observation_dates)
                                prev_yoy = _safe_yoy(previous, prev_year_ago)

                                # Calculate historical YoY values with
                                # date-aware lookback
                                historical_values = []
                                for i in range(
                                        min(12, len(observations) - 2)):
                                    curr_val = observations[i]
                                    prev_val = _find_yoy_value(
                                        i, observations, observation_dates)
                                    if curr_val is not None and prev_val is not None and curr_val > 0 and prev_val > 0.001:
                                        yoy = ((curr_val / prev_val) - 1) * 100
                                        if -100 < yoy < 100:
                                            prev_m1_val = _find_yoy_value(
                                                i + 1, observations, observation_dates) if i + 1 < len(observations) else prev_val
                                            prev_m1_yoy = ((observations[i + 1] / prev_m1_val) - 1) * \
                                                100 if prev_m1_val and prev_m1_val > 0.001 else 0
                                            if prev_m1_yoy < -100 or prev_m1_yoy > 100:
                                                prev_m1_yoy = 0
                                            historical_values.append({
                                                'date': datetime.strptime(observation_dates[i], '%Y-%m-%d').strftime('%m/%d/%y'),
                                                'value': f"{yoy:.1f}%",
                                                'change': f"{(yoy - prev_m1_yoy):+.1f}%"
                                            })

                                # Format dates for display
                                prev_date = datetime.strptime(
                                    observation_dates[1], '%Y-%m-%d')

                                # Determine trend with more granular thresholds
                                if abs(current_yoy - prev_yoy) < 0.1:
                                    trend = 'stable'
                                elif current_yoy > prev_yoy:
                                    trend = 'accelerating_up' if (
                                        current_yoy - prev_yoy) > 0.2 else 'up'
                                else:
                                    trend = 'accelerating_down' if (
                                        prev_yoy - current_yoy) > 0.2 else 'down'

                                results[name] = {
                                    'value': f"{current_yoy:.1f}%",
                                    'previous': f"{prev_yoy:.1f}%",
                                    'change_rate': f"{(current_yoy - prev_yoy):+.1f}%",
                                    'trend': trend,
                                    'last_updated': current_date.strftime('%m/%d/%y'),
                                    'previous_date': prev_date.strftime('%m/%d/%y'),
                                    'history': historical_values}

                                logger.info(
                                    f"Inflation Results: {results[name]}")

                            else:
                                current = observations[0]
                                previous = observations[1]

                                # Calculate rate of change with guard against
                                # near-zero denominator
                                if previous is not None and abs(previous) > 0.001:
                                    change = (
                                        (current - previous) / abs(previous)) * 100
                                else:
                                    change = 0.0

                                # Get historical values with zero-division
                                # guards
                                def _safe_pct_change(val, base):
                                    if base is None or val is None:
                                        return 0.0
                                    if abs(base) <= 0.001:
                                        return 0.0
                                    return ((val - base) / abs(base)) * 100

                                historical_values = [
                                    {
                                        'date': datetime.strptime(observation_dates[i], '%Y-%m-%d').strftime('%m/%d/%y'),
                                        'value': config['transform'](observations[i]),
                                        'change': config['change_transform'](
                                            _safe_pct_change(
                                                observations[i],
                                                observations[i + 1 if i + 1 < len(observations) else i]
                                            ))
                                    }
                                    for i in range(min(4, len(observations)))
                                ]

                                # Determine trend based on last 4 observations
                                if len(observations) >= 4:
                                    changes = [
                                        _safe_pct_change(observations[i], observations[i + 1])
                                        for i in range(len(observations) - 1)
                                    ]
                                    avg_change = sum(changes) / len(changes) if changes else 0

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
                                    'last_updated': datetime.strptime(
                                        observation_dates[0],
                                        '%Y-%m-%d').strftime('%m/%d/%y'),
                                    'history': historical_values}
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
                'GDP': {
                    'value': 'N/A',
                    'previous': 'N/A',
                    'change_rate': 'N/A',
                    'trend': 'neutral',
                    'last_updated': 'N/A'},
                'Inflation': {
                    'value': 'N/A',
                    'previous': 'N/A',
                    'change_rate': 'N/A',
                    'trend': 'neutral',
                    'last_updated': 'N/A'},
                'Unemployment': {
                    'value': 'N/A',
                    'previous': 'N/A',
                    'change_rate': 'N/A',
                    'trend': 'neutral',
                    'last_updated': 'N/A'},
                'Last Updated': datetime.now().strftime('%Y-%m-%d')}

    def fetch_economic_history(
            self,
            series_id: str,
            periods: int) -> Optional[Dict]:
        """Fetch economic data history from FRED."""
        try:
            # TODO: Implement FRED API call
            # For now, return mock data
            dates = pd.date_range(
                end=datetime.now(),
                periods=periods,
                freq='ME')
            values = [
                2.1,
                2.3,
                2.0,
                1.8,
                1.9,
                2.2,
                2.4,
                2.1,
                2.0,
                1.9,
                2.1,
                2.3]
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
            dates = pd.date_range(
                end=datetime.now(),
                periods=periods,
                freq='ME')
            values = [
                3.1,
                3.2,
                3.0,
                2.9,
                2.8,
                2.7,
                2.6,
                2.5,
                2.4,
                2.3,
                2.2,
                2.1]
            return {
                'labels': [d.strftime('%Y-%m') for d in dates],
                'values': values[:periods]
            }
        except Exception as e:
            print(f"Error fetching inflation history: {e}")
            return None

    def get_most_recent_trading_day(self) -> str:
        """Get the most recent trading day (excluding weekends and holidays)."""
        et_time = datetime.now(pytz.timezone('US/Eastern'))
        current_date = et_time.date()

        # If it's weekend, go back to Friday
        if et_time.weekday() >= 5:  # Saturday = 5, Sunday = 6
            days_back = et_time.weekday() - 4  # Friday = 4
            current_date = current_date - timedelta(days=days_back)

        # If it's before 9:30 AM ET, use previous day
        if et_time.hour < 9 or (et_time.hour == 9 and et_time.minute < 30):
            current_date = current_date - timedelta(days=1)
            # If previous day was weekend, go back to Friday
            if current_date.weekday() >= 5:
                days_back = current_date.weekday() - 4
                current_date = current_date - timedelta(days=days_back)

        return current_date.strftime('%Y-%m-%d')

    def fetch_market_status(self) -> Dict:
        """Fetch current market status with after-hours awareness"""
        cache_key = f"market_status_{datetime.now().strftime('%Y-%m-%d_%H')}"

        if not self.force_refresh:
            cached_data = self._load_from_cache(cache_key, max_age_hours=1)
            if cached_data:
                return cached_data

        try:
            # Get current time in ET
            et_time = datetime.now(pytz.timezone('US/Eastern'))
            current_time = et_time.strftime('%H:%M')
            is_weekend = et_time.weekday() >= 5

            # Define market hours
            pre_market_start = '04:00'
            market_open = '09:30'
            market_close = '16:00'
            after_hours_close = '20:00'

            # Determine market status
            if is_weekend:
                status = 'Closed'
                hours = 'Market Closed - Opens Monday at 4:00 AM ET'
                data_availability = 'delayed'
            elif current_time < pre_market_start:
                status = 'Closed'
                hours = 'Pre-Market Trading starts at 4:00 AM ET'
                data_availability = 'delayed'
            elif current_time < market_open:
                status = 'Pre-Market'
                hours = 'Regular Trading starts at 9:30 AM ET'
                data_availability = 'pre_market'
            elif current_time < market_close:
                status = 'Open'
                hours = 'Regular Trading Hours (9:30 AM - 4:00 PM ET)'
                data_availability = 'live'
            elif current_time < after_hours_close:
                status = 'After-Hours'
                hours = 'After-Hours Trading (until 8:00 PM ET)'
                data_availability = 'after_hours'
            else:
                status = 'Closed'
                hours = 'Market Closed - Opens at 4:00 AM ET'
                data_availability = 'delayed'

            # Get most recent trading day
            most_recent_trading_day = self.get_most_recent_trading_day()

            result = {
                'status': status,
                'hours': hours,
                'current_time_et': current_time,
                'last_updated': et_time.strftime('%Y-%m-%d %H:%M:%S %Z'),
                'is_weekend': is_weekend,
                'is_after_hours': status in ['Closed', 'After-Hours'],
                'most_recent_trading_day': most_recent_trading_day,
                'data_availability': data_availability
            }

            self._save_to_cache(cache_key, result)
            return result

        except Exception as e:
            logger.error(f"Error fetching market status: {e}")
            return {
                'status': 'Unknown',
                'hours': 'Status Unavailable',
                'current_time_et': datetime.now().strftime('%H:%M'),
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'is_weekend': True,
                'is_after_hours': True,
                'most_recent_trading_day': datetime.now().strftime('%Y-%m-%d'),
                'data_availability': 'delayed'
            }

    def fetch_economic_events(self) -> Dict:
        """Fetch top 5 most active tickers and their latest news as events for the dashboard."""
        logger.info(
            "Fetching Polygon market movers and news for events section")
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
                dates = [
                    datetime.strptime(
                        obs['date'],
                        '%Y-%m-%d') for obs in data['observations']]
                values = [float(obs['value'])
                          for obs in data['observations'] if obs['value'] != '.']

                # Format for chart
                data = {
                    'labels': [
                        f"Q{(i % 4) + 1} {d.year}" for i,
                        d in enumerate(dates)],
                    'values': values}
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
                # Filter out '.' values while tracking dates
                raw_obs = data['observations']
                dates = []
                values = []
                for obs in raw_obs:
                    if obs['value'] != '.':
                        dates.append(datetime.strptime(obs['date'], '%Y-%m-%d'))
                        values.append(float(obs['value']))

                # Calculate YoY change using date-aware lookback
                yoy_values = []
                for i in range(len(values)):
                    # Find value ~365 days before
                    target_date = dates[i]
                    target_year_ago = target_date - timedelta(days=365)
                    best_j = None
                    best_diff = timedelta(days=365)
                    for j in range(i + 1, len(dates)):
                        diff = abs(target_year_ago - dates[j])
                        if diff < best_diff:
                            best_diff = diff
                            best_j = j
                    if best_j is not None and best_diff.days < 45:
                        base = values[best_j]
                        # Guard against near-zero bases
                        if base > 0.001:
                            yoy = ((values[i] - base) / base) * 100
                        else:
                            yoy = 0.0
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
                dates = [
                    datetime.strptime(
                        obs['date'],
                        '%Y-%m-%d') for obs in data['observations']]
                values = [float(obs['value'])
                          for obs in data['observations'] if obs['value'] != '.']

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

    def get_bond_data(
            self,
            periods: int = 24,
            frequency: str = 'monthly') -> Dict:
        """Get bond yield data from FRED, with debugging and frequency control."""
        try:
            # Set FRED frequency
            freq_map = {'monthly': 'm', 'yearly': 'a'}
            freq_param = freq_map.get(frequency, 'm')
            print(
                f"[DEBUG] Fetching bond data: periods={periods}, frequency={frequency}, freq_param={freq_param}")
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
            if (
                'observations' in data_10y and len(
                    data_10y['observations']) > 0 and 'observations' in data_2y and len(
                    data_2y['observations']) > 0):
                dates = [
                    datetime.strptime(
                        obs['date'],
                        '%Y-%m-%d') for obs in data_10y['observations']]
                values_10y = [
                    float(
                        obs['value']) for obs in data_10y['observations'] if obs['value'] != '.']
                values_2y = [
                    float(
                        obs['value']) for obs in data_2y['observations'] if obs['value'] != '.']
                print(
                    f"[DEBUG] 10Y count: {len(values_10y)}, 2Y count: {len(values_2y)}")
                print(f"[DEBUG] 10Y dates: {dates}")
                print(f"[DEBUG] 10Y values: {values_10y}")
                print(f"[DEBUG] 2Y values: {values_2y}")
                # Format for chart
                data = {'labels': [d.strftime('%Y') if frequency == 'yearly' else d.strftime(
                    '%Y-%m') for d in dates], 'values': values_10y, 'values_2y': values_2y}
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

    def _is_quad_witching(self) -> bool:
        """Check if today is a Quad Witching day (3rd Friday of Mar/Jun/Sep/Dec)."""
        et_time = datetime.now(pytz.timezone('US/Eastern'))
        if et_time.weekday() != 4:  # Not Friday
            return False
        if et_time.month not in (3, 6, 9, 12):  # Not quarterly month
            return False
        # Check if it's the 3rd Friday
        day = et_time.day
        # 1st Friday = day 1-7; 2nd = day 8-14; 3rd = day 15-21
        return 15 <= day <= 21

    def _get_third_friday(self, year: int, month: int) -> datetime:
        """Return the date of the 3rd Friday in a given month."""
        from calendar import monthcalendar
        cal = monthcalendar(year, month)
        # monthcalendar returns weeks as lists of day numbers (0 = outside month)
        # Find all Fridays (day 4 = Friday where weekday=4)
        fridays = [week[4] for week in cal if week[4] != 0]
        return datetime(year, month, fridays[2])  # 3rd Friday (index 2)

    def fetch_macro_events(self) -> Dict:
        """Fetch relevant macro events for the daily market check.
        
        Returns events with relevance markup: High (Quad Witching, FOMC, NFP, CPI)
        and Medium (key tickers: BTCI, MU, NBIS).
        """
        et_now = datetime.now(pytz.timezone('US/Eastern'))
        et_today = et_now.date()
        events = []

        # 1. Quad Witching (quarterly)
        if self._is_quad_witching():
            quarter_names = {3: 'Q1', 6: 'Q2', 9: 'Q3', 12: 'Q4'}
            qname = quarter_names.get(et_now.month, '')
            events.append({
                'time': et_now.strftime('%H:%M'),
                'country': 'US',
                'description': f'⚠️ Quad Witching — {qname} options/futures expiration',
                'importance': 'High',
                'actual': f'{et_now.month}/{et_now.year}',
                'forecast': None,
                'previous': None,
                'relevance': 'macro'
            })
        else:
            # Show upcoming Quad Witching date if within 14 days
            for q_month in (3, 6, 9, 12):
                qw_date = self._get_third_friday(et_now.year, q_month)
                days_until = (qw_date.date() - et_today).days
                if 0 < days_until <= 14:
                    quarter_names = {3: 'Q1', 6: 'Q2', 9: 'Q3', 12: 'Q4'}
                    qname = quarter_names.get(q_month, '')
                    events.append({
                        'time': qw_date.strftime('%H:%M'),
                        'country': 'US',
                        'description': f'📅 Upcoming: Quad Witching — {qname} ({qw_date.strftime("%b %d")})',
                        'importance': 'Medium',
                        'actual': None,
                        'forecast': None,
                        'previous': None,
                        'relevance': 'macro'
                    })
                    break

        # 2. Recent NFP (Non-Farm Payrolls) — first Friday of current/previous month
        try:
            if self.fred_api_key:
                fr = requests.get(
                    "https://api.stlouisfed.org/fred/series/observations",
                    params={
                        'series_id': 'PAYEMS',
                        'api_key': self.fred_api_key,
                        'file_type': 'json',
                        'sort_order': 'desc',
                        'limit': 2
                    }
                )
                nfp_data = fr.json()
                if nfp_data.get('observations'):
                    latest = nfp_data['observations'][0]
                    prev = nfp_data['observations'][1] if len(nfp_data['observations']) > 1 else None
                    nfp_val = latest['value']
                    nfp_date = datetime.strptime(latest['date'], '%Y-%m-%d')
                    prev_val = prev['value'] if prev else None
                    change_val = int(nfp_val) - int(prev_val) if prev_val else 0
                    direction = '⬆️' if change_val > 0 else '⬇️' if change_val < 0 else '➡️'
                    events.append({
                        'time': nfp_date.strftime('%H:%M'),
                        'country': 'US',
                        'description': f'NFP: {nfp_val}K ({direction} {abs(change_val)}K from prev) — Employment Report',
                        'importance': 'High',
                        'actual': nfp_val,
                        'forecast': None,
                        'previous': prev_val,
                        'relevance': 'macro'
                    })
        except Exception as e:
            logger.warning(f"Could not fetch NFP data: {e}")

        # 3. Recent CPI
        try:
            if self.fred_api_key:
                cpi_resp = requests.get(
                    "https://api.stlouisfed.org/fred/series/observations",
                    params={
                        'series_id': 'CPIAUCSL',
                        'api_key': self.fred_api_key,
                        'file_type': 'json',
                        'sort_order': 'desc',
                        'limit': 13
                    }
                )
                cpi_data = cpi_resp.json()
                if cpi_data.get('observations'):
                    obs = [o for o in cpi_data['observations'] if o['value'] != '.']
                    if len(obs) >= 13:
                        current_cpi = float(obs[0]['value'])
                        year_ago_cpi = float(obs[12]['value'])
                        yoy_change = round((current_cpi - year_ago_cpi) / year_ago_cpi * 100, 1)
                        cpi_date = datetime.strptime(obs[0]['date'], '%Y-%m-%d')
                        events.append({
                            'time': cpi_date.strftime('%H:%M'),
                            'country': 'US',
                            'description': f'CPI YoY: {yoy_change}% (CPI: {current_cpi:.1f})',
                            'importance': 'High',
                            'actual': f'{yoy_change}%',
                            'forecast': None,
                            'previous': None,
                            'relevance': 'macro'
                        })
        except Exception as e:
            logger.warning(f"Could not fetch CPI data: {e}")

        # 4. Recent FOMC announcement (approximate: check if rate decision exists)
        try:
            if self.fred_api_key:
                fed_resp = requests.get(
                    "https://api.stlouisfed.org/fred/series/observations",
                    params={
                        'series_id': 'FEDFUNDS',
                        'api_key': self.fred_api_key,
                        'file_type': 'json',
                        'sort_order': 'desc',
                        'limit': 2
                    }
                )
                fed_data = fed_resp.json()
                if fed_data.get('observations'):
                    latest_fed = fed_data['observations'][0]
                    fed_val = latest_fed['value']
                    fed_date = datetime.strptime(latest_fed['date'], '%Y-%m-%d')
                    # Check if the rate was updated this month (recent FOMC)
                    if abs((et_today - fed_date.date()).days) <= 45:
                        events.append({
                            'time': fed_date.strftime('%H:%M'),
                            'country': 'US',
                            'description': f'Fed Funds Rate: {fed_val}% (latest FOMC decision)',
                            'importance': 'High',
                            'actual': fed_val,
                            'forecast': None,
                            'previous': None,
                            'relevance': 'macro'
                        })
        except Exception as e:
            logger.warning(f"Could not fetch FOMC data: {e}")

        # 5. Key ticker news: BTCI, MU, NBIS
        key_tickers = [
            ('BTCI', 'BTCI (Berkshire Crypto)'),
            ('MU', 'Micron Technology'),
            ('NBIS', 'Nebius Group'),
        ]
        for ticker, display_name in key_tickers:
            try:
                news_url = f"https://api.polygon.io/v2/reference/news?ticker={ticker}&limit=1&apiKey={POLYGON_API_KEY}"
                nr = requests.get(news_url)
                nd = nr.json()
                if nd.get('results'):
                    news = nd['results'][0]
                    pub_date = news.get('published_utc', '')[:10] if news.get('published_utc') else ''
                    events.append({
                        'time': pub_date,
                        'country': 'US',
                        'description': f'{display_name}: {news.get("title", "")}',
                        'importance': 'Medium',
                        'actual': None,
                        'forecast': None,
                        'previous': None,
                        'url': news.get('article_url', ''),
                        'relevance': 'ticker'
                    })
            except Exception as e:
                logger.warning(f"Could not fetch news for {ticker}: {e}")

        return {
            'events': events,
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }

    def fetch_index_history(
            self,
            ticker: str,
            periods: int = 60,
            interval: str = 'day') -> Optional[Dict]:
        """Fetch historical OHLC prices for a given index ticker using Polygon."""
        from datetime import datetime, timedelta
        try:
            end_date = datetime.now()
            # buffer for weekends/holidays
            start_date = end_date - timedelta(days=periods * 2)
            aggs = self.client.get_aggs(
                ticker=ticker,
                multiplier=1,
                timespan=interval,
                from_=start_date.strftime('%Y-%m-%d'),
                to=end_date.strftime('%Y-%m-%d'),
                adjusted=True
            )
            logger.debug(
                f"Polygon aggs type: {type(aggs)}; length: {len(aggs) if hasattr(aggs,'__len__') else 'N/A'}")
            if aggs and len(aggs) > 0:
                logger.debug(f"First agg: {aggs[0]}")
                logger.debug(
                    f"First agg.timestamp type: {type(getattr(aggs[0],'timestamp',None))}")
                for i, agg in enumerate(aggs[:3]):
                    logger.debug(f"Agg {i}: {agg}")
                    logger.debug(
                        f"Agg {i} timestamp: {getattr(agg,'timestamp',None)} type: {type(getattr(agg,'timestamp',None))}")
                # Only keep the most recent 'periods' data points
                aggs = aggs[-periods:]
                labels = []
                for agg in aggs:
                    ts = getattr(agg, 'timestamp', None)
                    if hasattr(ts, 'strftime'):
                        labels.append(ts.strftime('%Y-%m-%d'))
                    elif isinstance(ts, (int, float)):
                        labels.append(
                            datetime.fromtimestamp(
                                ts / 1000).strftime('%Y-%m-%d'))
                    else:
                        labels.append(str(ts))
                values = [agg.close for agg in aggs]
                ohlc = {
                    'open': [agg.open for agg in aggs],
                    'high': [agg.high for agg in aggs],
                    'low': [agg.low for agg in aggs],
                    'close': [agg.close for agg in aggs],
                }
                logger.info(
                    f"Fetched {len(values)} data points for {ticker} from Polygon.")
                return {'labels': labels, 'values': values, 'ohlc': ohlc}
            else:
                logger.warning(
                    f"No historical data returned for {ticker} from Polygon.")
                return {'labels': [], 'values': []}
        except Exception as e:
            logger.error(
                f"Error fetching index history for {ticker} from Polygon: {e}")
            return {'labels': [], 'values': []}

    def fetch_style_box_etf_data(self) -> Dict:
        """Fetch 1-day % change for style box ETFs (Value/Growth/Core x Large/Mid/Small) from Polygon using multi-day history."""
        import logging
        logger = logging.getLogger(__name__)
        from datetime import datetime, timedelta
        style_box = [
            ["IVE", "IVW", "SPY"],   # Large: Value, Growth, Core
            ["IJJ", "IJK", "MDY"],   # Mid: Value, Growth, Core
            ["IJS", "IJT", "IWM"]    # Small: Value, Growth, Core
        ]
        x_labels = ["Value", "Growth", "Core"]
        y_labels = ["Large", "Mid", "Small"]
        z = []
        for row_idx, row in enumerate(style_box):
            z_row = []
            for col_idx, ticker in enumerate(row):
                try:
                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=7)
                    aggs = self.client.get_aggs(
                        ticker=ticker,
                        multiplier=1,
                        timespan="day",
                        from_=start_date.strftime('%Y-%m-%d'),
                        to=end_date.strftime('%Y-%m-%d'),
                        adjusted=True
                    )
                    aggs = sorted(
                        aggs, key=lambda x: x.timestamp) if aggs else []
                    if aggs and len(aggs) >= 2:
                        prev = aggs[-2]
                        last = aggs[-1]
                        prev_close = getattr(
                            prev, 'adjusted_close', prev.close)
                        last_close = getattr(
                            last, 'adjusted_close', last.close)
                        change = ((last_close - prev_close) /
                                  prev_close) * 100 if prev_close != 0 else 0
                        z_row.append(round(change, 2))
                    else:
                        z_row.append(None)
                except Exception as e:
                    logger.error(
                        f"[StyleBox] Ticker: {ticker} | Exception: {e}")
                    z_row.append(None)
            z.append(z_row)
        return {"z": z, "x": x_labels, "y": y_labels}
