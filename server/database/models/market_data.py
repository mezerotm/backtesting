"""
Market data models for storing price and symbol information.
"""

from typing import Optional, Dict, Any
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel


class MarketData(BaseModel):
    """Market data model for storing current prices."""

    id: str
    symbol: str
    current_price: Decimal
    previous_close: Optional[Decimal] = None
    change: Optional[Decimal] = None
    change_percent: Optional[Decimal] = None
    volume: Optional[int] = None
    market_cap: Optional[Decimal] = None
    source: str = "polygon"  # polygon, coingecko, etc.
    last_updated: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class SymbolCache(BaseModel):
    """Symbol cache model for storing symbol metadata."""

    id: str
    symbol: str
    name: str
    type: str = "stock"  # stock, crypto, etf, etc.
    exchange: Optional[str] = None
    currency: str = "USD"
    is_active: bool = True
    metadata: Optional[Dict[str, Any]] = None
    last_updated: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class HistoricalPrice(BaseModel):
    """Historical price data model."""

    id: str
    symbol: str
    date: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Optional[int] = None
    source: str = "polygon"
    created_at: datetime

    class Config:
        from_attributes = True


class MarketDataCreate(BaseModel):
    """Model for creating market data."""

    symbol: str
    current_price: Decimal
    previous_close: Optional[Decimal] = None
    change: Optional[Decimal] = None
    change_percent: Optional[Decimal] = None
    volume: Optional[int] = None
    market_cap: Optional[Decimal] = None
    source: str = "polygon"


class SymbolCacheCreate(BaseModel):
    """Model for creating symbol cache."""

    symbol: str
    name: str
    type: str = "stock"
    exchange: Optional[str] = None
    currency: str = "USD"
    is_active: bool = True
    metadata: Optional[Dict[str, Any]] = None
