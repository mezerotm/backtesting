"""
Market data repository for database operations.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from server.database.models.market_data import (
    MarketData,
    SymbolCache,
    HistoricalPrice,
    MarketDataCreate,
    SymbolCacheCreate)
from server.database.connection import db_connection
from config.backend.logger import get_api_logger


class MarketDataRepository:
    """Repository for market data operations."""

    def __init__(self):
        self.logger = get_api_logger(__name__)
        self.pb_client = db_connection.get_pocketbase_client()

    # Market data operations
    async def create_market_data(
            self, market_data: MarketDataCreate) -> Optional[MarketData]:
        """Create new market data."""
        try:
            data = {
                "symbol": market_data.symbol,
                "current_price": str(
                    market_data.current_price),
                "previous_close": str(
                    market_data.previous_close) if market_data.previous_close else None,
                "change": str(
                    market_data.change) if market_data.change else None,
                "change_percent": str(
                    market_data.change_percent) if market_data.change_percent else None,
                "volume": market_data.volume,
                "market_cap": str(
                    market_data.market_cap) if market_data.market_cap else None,
                "source": market_data.source,
                "last_updated": datetime.now().isoformat(),
                "created_at": datetime.now().isoformat()}

            result = await self.pb_client.create_market_data(data)
            return MarketData(**result) if result else None
        except Exception as e:
            self.logger.error(f"Error creating market data: {e}")
            return None

    async def get_market_data_by_symbol(
            self, symbol: str) -> Optional[MarketData]:
        """Get market data by symbol."""
        try:
            result = await self.pb_client.get_market_data_by_symbol(symbol)
            return MarketData(**result) if result else None
        except Exception as e:
            self.logger.error(f"Error getting market data by symbol: {e}")
            return None

    async def update_market_data(
            self,
            symbol: str,
            market_data: MarketDataCreate) -> Optional[MarketData]:
        """Update market data for a symbol."""
        try:
            update_data = {
                "current_price": str(
                    market_data.current_price),
                "previous_close": str(
                    market_data.previous_close) if market_data.previous_close else None,
                "change": str(
                    market_data.change) if market_data.change else None,
                "change_percent": str(
                    market_data.change_percent) if market_data.change_percent else None,
                "volume": market_data.volume,
                "market_cap": str(
                    market_data.market_cap) if market_data.market_cap else None,
                "source": market_data.source,
                "last_updated": datetime.now().isoformat()}

            result = await self.pb_client.update_market_data(symbol, update_data)
            return MarketData(**result) if result else None
        except Exception as e:
            self.logger.error(f"Error updating market data: {e}")
            return None

    async def upsert_market_data(
            self, market_data: MarketDataCreate) -> Optional[MarketData]:
        """Create or update market data for a symbol."""
        try:
            existing = await self.get_market_data_by_symbol(market_data.symbol)
            if existing:
                return await self.update_market_data(market_data.symbol, market_data)
            else:
                return await self.create_market_data(market_data)
        except Exception as e:
            self.logger.error(f"Error upserting market data: {e}")
            return None

    def get_market_data_for_symbols(
            self, symbols: List[str]) -> List[MarketData]:
        """Get market data for multiple symbols."""
        try:
            if not symbols:
                return []
            # Build filter: symbol in ('SYM1','SYM2',...)
            quoted = "','".join(s.upper() for s in symbols)
            results = self.pb_client.get_records(
                "market_data", f"symbol IN ('{quoted}')")
            return [MarketData(**data) for data in results] if results else []
        except Exception as e:
            self.logger.error(f"Error getting market data for symbols: {e}")
            return []

    # Symbol cache operations
    async def create_symbol_cache(
            self, symbol_cache: SymbolCacheCreate) -> Optional[SymbolCache]:
        """Create new symbol cache entry."""
        try:
            data = {
                "symbol": symbol_cache.symbol,
                "name": symbol_cache.name,
                "type": symbol_cache.type,
                "exchange": symbol_cache.exchange,
                "currency": symbol_cache.currency,
                "is_active": symbol_cache.is_active,
                "metadata": symbol_cache.metadata,
                "last_updated": datetime.now().isoformat(),
                "created_at": datetime.now().isoformat()
            }

            result = await self.pb_client.create_symbol_cache(data)
            return SymbolCache(**result) if result else None
        except Exception as e:
            self.logger.error(f"Error creating symbol cache: {e}")
            return None

    async def get_symbol_cache_by_symbol(
            self, symbol: str) -> Optional[SymbolCache]:
        """Get symbol cache by symbol."""
        try:
            result = await self.pb_client.get_symbol_cache_by_symbol(symbol)
            return SymbolCache(**result) if result else None
        except Exception as e:
            self.logger.error(f"Error getting symbol cache by symbol: {e}")
            return None

    async def update_symbol_cache(
            self, symbol: str, metadata: Dict[str, Any]) -> Optional[SymbolCache]:
        """Update symbol cache metadata."""
        try:
            update_data = {
                "metadata": metadata,
                "last_updated": datetime.now().isoformat()
            }

            result = await self.pb_client.update_symbol_cache(symbol, update_data)
            return SymbolCache(**result) if result else None
        except Exception as e:
            self.logger.error(f"Error updating symbol cache: {e}")
            return None

    async def upsert_symbol_cache(
            self, symbol_cache: SymbolCacheCreate) -> Optional[SymbolCache]:
        """Create or update symbol cache."""
        try:
            existing = await self.get_symbol_cache_by_symbol(symbol_cache.symbol)
            if existing:
                return await self.update_symbol_cache(symbol_cache.symbol, symbol_cache.metadata or {})
            else:
                return await self.create_symbol_cache(symbol_cache)
        except Exception as e:
            self.logger.error(f"Error upserting symbol cache: {e}")
            return None
