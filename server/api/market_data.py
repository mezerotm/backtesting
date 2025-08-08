"""
Market Data Service - Handles all external API calls for market data
"""
from fastapi import APIRouter
import time
import requests
from typing import Dict, List, Optional, Any
from fastapi import HTTPException
from config.backend.logger import get_api_logger
from config.backend.settings import POLYGON_API_KEY

logger = get_api_logger("market_data")

# API Keys
# POLYGON_API_KEY is imported from utils.config


class MarketDataService:
    """Service for fetching market data from external APIs with advanced rate limiting"""

    def __init__(self):
        # Rate limiting configuration based on CoinGecko research
        self.rate_limit_config = {
            'free_tier_calls_per_minute': 30,  # Conservative estimate for free tier
            'batch_size': 10,  # CoinGecko recommended batch size
            'delay_between_batches': 2.0,  # 2 seconds between batches
            'delay_between_requests': 1.0,  # 1 second between individual requests
            'max_retries': 3,  # Maximum retry attempts
            # Base for exponential backoff (3, 6, 12 seconds)
            'exponential_backoff_base': 3,
            'request_timeout': 15,  # Request timeout in seconds
        }

        # Request tracking for rate limiting
        self.request_history = []
        self.last_request_time = 0

        self.crypto_symbol_set = {
            'BTC',
            'ETH',
            'ADA',
            'DOGE',
            'XRP',
            'LTC',
            'BCH',
            'ETC',
            'LINK',
            'UNI',
            'AAVE',
            'COMP',
            'MKR',
            'YFI',
            'SUSHI',
            'CRV',
            'BAL',
            'REN',
            'ZRX',
            'BAT',
            'ZEC',
            'DASH',
            'XLM',
            'TRX',
            'VET',
            'ALGO',
            'ATOM',
            'DOT',
            'SOL',
            'AVAX',
            'MATIC',
            'FTM',
            'NEAR',
            'AR',
            'ICP',
            'FIL',
            'THETA',
            'XTZ',
            'EOS',
            'XMR',
            'NEO',
            'QTUM',
            'IOTA',
            'NANO',
            'BTT',
            'WIN',
            'BTTOLD',
            'WINOLD'}

        # CoinGecko ID mapping
        self.coin_id_map = {
            'BTC': 'bitcoin',
            'ETH': 'ethereum',
            'SOL': 'solana',
            'XRP': 'ripple',
            'DOGE': 'dogecoin',
            'ADA': 'cardano',
            'LTC': 'litecoin',
            'BCH': 'bitcoin-cash',
            'ETC': 'ethereum-classic',
            'LINK': 'chainlink',
            'UNI': 'uniswap',
            'AAVE': 'aave',
            'COMP': 'compound-governance-token',
            'MKR': 'maker',
            'YFI': 'yearn-finance',
            'SUSHI': 'sushi',
            'CRV': 'curve-dao-token',
            'BAL': 'balancer',
            'REN': 'republic-protocol',
            'ZRX': '0x',
            'BAT': 'basic-attention-token',
            'ZEC': 'zcash',
            'DASH': 'dash',
            'XLM': 'stellar',
            'TRX': 'tron',
            'VET': 'vechain',
            'ALGO': 'algorand',
            'ATOM': 'cosmos',
            'AVAX': 'avalanche-2',
            'MATIC': 'matic-network',
            'FTM': 'fantom',
            'NEAR': 'near',
            'AR': 'arweave',
            'ICP': 'internet-computer',
            'FIL': 'filecoin',
            'THETA': 'theta-token',
            'XTZ': 'tezos',
            'EOS': 'eos',
            'XMR': 'monero',
            'NEO': 'neo',
            'QTUM': 'qtum',
            'IOTA': 'iota',
            'NANO': 'nano'}

    def _clean_request_history(self):
        """Clean old requests from history (older than 1 minute)"""
        current_time = time.time()
        self.request_history = [
            req_time for req_time in self.request_history
            if current_time - req_time < 60
        ]

    def _check_rate_limit(self):
        """Check if we're within rate limits and wait if necessary"""
        self._clean_request_history()
        current_time = time.time()

        # Check if we've made too many requests in the last minute
        if len(
                self.request_history) >= self.rate_limit_config['free_tier_calls_per_minute']:
            # Wait until we can make another request
            oldest_request = min(self.request_history)
            wait_time = 60 - (current_time - oldest_request) + 1
            if wait_time > 0:
                logger.warning(
                    f"Rate limit reached, waiting {
                        wait_time:.1f} seconds...")
                time.sleep(wait_time)
                self._clean_request_history()

        # Ensure minimum delay between requests
        if current_time - \
                self.last_request_time < self.rate_limit_config['delay_between_requests']:
            sleep_time = self.rate_limit_config['delay_between_requests'] - (
                current_time - self.last_request_time)
            time.sleep(sleep_time)

        # Record this request
        self.request_history.append(time.time())
        self.last_request_time = time.time()

    def _make_rate_limited_request(
            self, url: str, params: dict = None) -> dict:
        """Make a rate-limited request with exponential backoff"""
        for attempt in range(self.rate_limit_config['max_retries']):
            try:
                # Check rate limits before making request
                self._check_rate_limit()

                # Make the request
                response = requests.get(
                    url,
                    params=params,
                    timeout=self.rate_limit_config['request_timeout']
                )

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:
                    # Rate limited - use exponential backoff
                    wait_time = (
                        self.rate_limit_config['exponential_backoff_base'] ** attempt) * 2
                    logger.warning(f"Rate limited (429), waiting {wait_time}s before retry {
                                   attempt + 1}/{self.rate_limit_config['max_retries']}")
                    time.sleep(wait_time)
                    if attempt == self.rate_limit_config['max_retries'] - 1:
                        logger.error(
                            f"Failed after {
                                self.rate_limit_config['max_retries']} attempts due to rate limiting")
                        return None
                else:
                    logger.warning(
                        f"API request failed with status {
                            response.status_code}")
                    return None

            except Exception as e:
                if attempt == self.rate_limit_config['max_retries'] - 1:
                    logger.error(
                        f"Request failed after {
                            self.rate_limit_config['max_retries']} attempts: {e}")
                    return None
                else:
                    wait_time = (
                        self.rate_limit_config['exponential_backoff_base'] ** attempt)
                    logger.warning(
                        f"Request failed, retrying in {wait_time}s: {e}")
                    time.sleep(wait_time)

        return None

    def is_crypto_symbol(self, symbol: str) -> bool:
        """Check if a symbol is a crypto symbol"""
        return symbol in self.crypto_symbol_set

    def separate_symbols(
            self, symbols: List[str]) -> tuple[List[str], List[str]]:
        """Separate crypto and stock symbols"""
        crypto_symbols = []
        stock_symbols = []

        for symbol in symbols:
            if self.is_crypto_symbol(symbol):
                crypto_symbols.append(symbol)
            else:
                stock_symbols.append(symbol)

        return crypto_symbols, stock_symbols

    def fetch_crypto_data_batch(
            self, crypto_symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """Fetch crypto data in batches to reduce CoinGecko API calls"""
        result = {}

        if not crypto_symbols:
            return result

        # Convert symbols to CoinGecko IDs
        coin_ids = []
        symbol_to_coin_id = {}
        for symbol in crypto_symbols:
            coin_id = self.coin_id_map.get(symbol, symbol.lower())
            coin_ids.append(coin_id)
            symbol_to_coin_id[symbol] = coin_id

        # Process in batches using configured batch size
        batch_size = self.rate_limit_config['batch_size']
        for i in range(0, len(coin_ids), batch_size):
            batch_ids = coin_ids[i:i + batch_size]
            batch_symbols = list(symbol_to_coin_id.keys())[i:i + batch_size]

            try:
                # Create batch request URL
                ids_param = ','.join(batch_ids)
                crypto_url = f"https://api.coingecko.com/api/v3/simple/price?ids={
                    ids_param}&vs_currencies=usd"

                logger.info(
                    f"Fetching batch crypto prices for {
                        len(batch_ids)} symbols: {batch_symbols}")

                # Add delay between batches to respect rate limits
                if i > 0:
                    time.sleep(self.rate_limit_config['delay_between_batches'])

                # Use rate-limited request method
                batch_data = self._make_rate_limited_request(crypto_url)

                # Process batch results
                if batch_data:
                    for symbol in batch_symbols:
                        coin_id = symbol_to_coin_id[symbol]
                        if coin_id in batch_data and 'usd' in batch_data[coin_id]:
                            last_price = float(batch_data[coin_id]['usd'])
                            prev_close = last_price  # For crypto, use current price as previous close

                            result[symbol] = {
                                'last_price': last_price,
                                'previous_close': prev_close,
                                'timestamp': time.time(),
                                'beta': None  # Crypto doesn't have beta
                            }
                            logger.info(
                                f"{symbol} (crypto): got price: ${last_price}")
                        else:
                            logger.warning(
                                f"{symbol} (crypto): no price data available for {coin_id}")
                            # Try cached data as fallback
                            try:
                                from server.api.portfolio import get_current_symbol_data
                                cached_data = get_current_symbol_data(symbol)
                                if cached_data and cached_data.get(
                                        'last_price'):
                                    result[symbol] = cached_data
                                    logger.info(
                                        f"{symbol} (crypto): using cached price: ${
                                            cached_data['last_price']}")
                            except Exception as cache_error:
                                logger.warning(
                                    f"{symbol} (crypto): failed to get cached data: {cache_error}")

            except Exception as batch_error:
                logger.warning(
                    f"Failed to process crypto batch: {batch_error}")
                # Fallback to individual requests for this batch
                for symbol in batch_symbols:
                    try:
                        from server.api.portfolio import get_current_symbol_data
                        cached_data = get_current_symbol_data(symbol)
                        if cached_data and cached_data.get('last_price'):
                            result[symbol] = cached_data
                            logger.info(
                                f"{symbol} (crypto): using cached price as fallback: ${
                                    cached_data['last_price']}")
                    except Exception as cache_error:
                        logger.warning(
                            f"{symbol} (crypto): no fallback data available: {cache_error}")

        return result

    def fetch_stock_data(
            self, stock_symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """Fetch stock data from Polygon.io"""
        result = {}

        if not stock_symbols:
            return result

        # Check if Polygon API key is available
        if not POLYGON_API_KEY:
            logger.warning(
                "POLYGON_API_KEY not set, skipping stock market data fetch")
            return result

        for symbol in stock_symbols:
            try:
                prev_url = f"https://api.polygon.io/v2/aggs/ticker/{
                    symbol}/prev"
                prev_params = {"adjusted": "true", "apiKey": POLYGON_API_KEY}
                prev_resp = requests.get(
                    prev_url, params=prev_params, timeout=10)
                prev_close = None
                last_price = None

                if prev_resp.status_code == 200:
                    prev_data = prev_resp.json()
                    prev_results = prev_data.get("results", [])
                    if prev_results:
                        prev_close = prev_results[0].get("c")
                        last_price = prev_close
                        logger.debug(
                            f"{symbol} (stock): got previous close: {prev_close}")

                # Return data in the format expected by the schema
                symbol_data = {
                    "last_price": last_price,
                    "previous_close": prev_close,
                    "timestamp": time.time(),
                    "beta": None
                }
                result[symbol] = symbol_data
                logger.debug(f"{symbol}: market data prepared")

            except Exception as e:
                logger.warning(f"Failed to fetch stock data for {symbol}: {e}")
                result[symbol] = {
                    "last_price": None,
                    "previous_close": None,
                    "timestamp": time.time(),
                    "beta": None
                }

        return result

    def fetch_symbol_data(
            self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """Fetch market data for a list of symbols (crypto and stocks)"""
        result = {}

        if not symbols:
            return result

        # Separate crypto and stock symbols
        crypto_symbols, stock_symbols = self.separate_symbols(symbols)

        # Process crypto symbols in batches
        if crypto_symbols:
            logger.info(
                f"Processing {
                    len(crypto_symbols)} crypto symbols in batches...")
            crypto_result = self.fetch_crypto_data_batch(crypto_symbols)
            result.update(crypto_result)

        # Process stock symbols individually
        if stock_symbols:
            logger.info(f"Processing {len(stock_symbols)} stock symbols...")
            stock_result = self.fetch_stock_data(stock_symbols)
            result.update(stock_result)

        return result

    def get_crypto_historical_price(
            self,
            symbol: str,
            date: str) -> Optional[float]:
        """Get historical crypto price from CoinGecko for a specific date with rate limiting"""
        try:
            # CoinGecko historical data endpoint
            url = f"https://api.coingecko.com/api/v3/coins/{
                symbol.lower()}/history"
            params = {
                'date': date,
                'localization': 'false'
            }

            logger.info(f"Fetching historical price for {symbol} on {date}")

            # Use rate-limited request method
            data = self._make_rate_limited_request(url, params)

            if data and 'market_data' in data and 'current_price' in data['market_data']:
                price = data['market_data']['current_price']['usd']
                logger.info(f"Historical price for {
                            symbol} on {date}: ${price}")
                return float(price)
            else:
                logger.warning(
                    f"No price data in CoinGecko response for {symbol} on {date}")
                return None

        except Exception as e:
            logger.error(f"Error getting historical price for {
                         symbol} on {date}: {e}")
            return None

    def calculate_betas(self, stock_symbols: List[str]) -> Dict[str, float]:
        """Calculate beta values for stock symbols (placeholder for now)"""
        # This is a placeholder - in a real implementation, you'd calculate betas
        # based on market data and correlation with market indices
        betas = {}
        for symbol in stock_symbols:
            betas[symbol] = 1.0  # Default beta of 1.0
        return betas

    def get_rate_limit_stats(self) -> Dict[str, Any]:
        """Get current rate limiting statistics"""
        self._clean_request_history()
        current_time = time.time()

        return {
            'requests_in_last_minute': len(
                self.request_history),
            'max_requests_per_minute': self.rate_limit_config['free_tier_calls_per_minute'],
            'time_since_last_request': current_time - self.last_request_time if self.last_request_time > 0 else 0,
            'rate_limit_config': self.rate_limit_config.copy()}

    def reset_rate_limit_tracking(self):
        """Reset rate limiting tracking (useful for testing)"""
        self.request_history = []
        self.last_request_time = 0
        logger.info("Rate limit tracking reset")


# Global instance
market_data_service = MarketDataService()

# Add FastAPI router for market data endpoints

router = APIRouter(prefix="/market-data", tags=["market-data"])


@router.get("/rate-limit-stats")
async def get_rate_limit_stats():
    """Get current rate limiting statistics for market data service"""
    return market_data_service.get_rate_limit_stats()


@router.post("/reset-rate-limit")
async def reset_rate_limit():
    """Reset rate limiting tracking (useful for testing)"""
    market_data_service.reset_rate_limit_tracking()
    return {"message": "Rate limit tracking reset successfully"}
