"""
Market data service for managing external API interactions and data fetching.
"""

from typing import Dict, Any, List, Optional
import asyncio
import time
from .base_service import BaseService


class MarketDataService(BaseService):
    """Service for market data operations."""

    def __init__(self):
        super().__init__()
        self.rate_limit_stats = {
            "coingecko_requests": 0,
            "polygon_requests": 0,
            "last_reset": time.time()
        }

    async def refresh_symbols(self, symbols: List[str]) -> Dict[str, Any]:
        """Refresh market data for a list of symbols."""
        try:
            self.log_operation(
                "refresh_symbols", {
                    "symbols": symbols, "count": len(symbols)})

            if not symbols:
                return {"success": True, "data": {"updated": 0}}

            # Separate crypto and stock symbols
            crypto_symbols = []
            stock_symbols = []

            for symbol in symbols:
                if symbol.upper() in ['BTC', 'ETH', 'SOL', 'XRP', 'DOGE']:
                    crypto_symbols.append(symbol)
                else:
                    stock_symbols.append(symbol)

            # Fetch data in parallel
            tasks = []
            if crypto_symbols:
                tasks.append(self._fetch_crypto_data(crypto_symbols))
            if stock_symbols:
                tasks.append(self._fetch_stock_data(stock_symbols))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            updated_count = 0
            for result in results:
                if isinstance(result, dict) and result.get("success"):
                    updated_count += result.get("data", {}).get("updated", 0)

            return {
                "success": True,
                "data": {
                    "updated": updated_count,
                    "crypto_count": len(crypto_symbols),
                    "stock_count": len(stock_symbols)
                }
            }
        except Exception as e:
            return self.handle_error(e, "refresh_symbols")

    async def get_rate_limit_stats(self) -> Dict[str, Any]:
        """Get current rate limit statistics."""
        try:
            current_time = time.time()
            time_since_reset = current_time - \
                self.rate_limit_stats["last_reset"]

            return {
                "success": True,
                "data": {
                    "coingecko_requests": self.rate_limit_stats["coingecko_requests"],
                    "polygon_requests": self.rate_limit_stats["polygon_requests"],
                    "time_since_reset": time_since_reset,
                    "last_reset": self.rate_limit_stats["last_reset"]}}
        except Exception as e:
            return self.handle_error(e, "get_rate_limit_stats")

    async def reset_rate_limits(self) -> Dict[str, Any]:
        """Reset rate limit counters."""
        try:
            self.log_operation("reset_rate_limits")

            self.rate_limit_stats = {
                "coingecko_requests": 0,
                "polygon_requests": 0,
                "last_reset": time.time()
            }

            return {
                "success": True,
                "data": {"message": "Rate limits reset successfully"}
            }
        except Exception as e:
            return self.handle_error(e, "reset_rate_limits")

    async def get_latest_price(self, symbol: str) -> Dict[str, Any]:
        """Get latest price for a symbol."""
        try:
            self.log_operation("get_latest_price", {"symbol": symbol})

            # For now, return mock data
            # This should be implemented with actual price fetching logic
            mock_prices = {
                "AAPL": 150.0,
                "GOOGL": 2800.0,
                "MSFT": 300.0,
                "TSLA": 250.0,
                "NVDA": 450.0,
                "BTC": 50000.0,
                "ETH": 3000.0,
                "SOL": 100.0,
                "XRP": 0.5,
                "DOGE": 0.1
            }

            price = mock_prices.get(symbol.upper(), 100.0)  # Default price

            return {
                "price": price,
                "timestamp": time.time()
            }
        except Exception as e:
            return self.handle_error(e, "get_latest_price")

    async def _fetch_crypto_data(self, symbols: List[str]) -> Dict[str, Any]:
        """Fetch crypto data from CoinGecko."""
        try:
            self.log_operation("fetch_crypto_data", {"symbols": symbols})

            # Implement crypto data fetching logic here
            # This would call the existing CoinGecko API logic

            self.rate_limit_stats["coingecko_requests"] += len(symbols)

            return {
                "success": True,
                "data": {"updated": len(symbols)}
            }
        except Exception as e:
            return self.handle_error(e, "fetch_crypto_data")

    async def _fetch_stock_data(self, symbols: List[str]) -> Dict[str, Any]:
        """Fetch stock data from Polygon.io."""
        try:
            self.log_operation("fetch_stock_data", {"symbols": symbols})

            # Implement stock data fetching logic here
            # This would call the existing Polygon.io API logic

            self.rate_limit_stats["polygon_requests"] += len(symbols)

            return {
                "success": True,
                "data": {"updated": len(symbols)}
            }
        except Exception as e:
            return self.handle_error(e, "fetch_stock_data")
