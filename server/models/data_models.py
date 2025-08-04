"""
Data Models and Schema Validation for Backtesting Application

This module defines the data structures and validation schemas for all collections
in the application. It ensures consistency between frontend, backend, and database
operations.

Key Features:
- Pydantic models for type safety and validation
- Schema definitions that match PocketBase collections
- Helper functions for data transformation
- Validation utilities for data integrity
"""

from pydantic import BaseModel, Field, validator, model_validator
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, date
from decimal import Decimal
import time


# =============================================================================
# BASE MODELS
# =============================================================================

class BaseRecord(BaseModel):
    """Base model for all database records."""
    id: Optional[str] = Field(None, description="Record ID")
    created: Optional[str] = Field(None, description="Creation timestamp")
    updated: Optional[str] = Field(None, description="Last update timestamp")

    class Config:
        # Allow extra fields for PocketBase metadata
        extra = "allow"
        # Use string for JSON serialization
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat()
        }


# =============================================================================
# PORTFOLIO MODELS
# =============================================================================

class PortfolioSettings(BaseRecord):
    """Portfolio settings and configuration."""
    user: str = Field(..., description="User ID")
    total_portfolio_cash: float = Field(
        0.0, description="Total cash in portfolio")
    total_portfolio_btc: float = Field(
        0.0, description="Total BTC value in USD")
    btc_avg_buy_price: float = Field(0.0, description="Average BTC buy price")
    robinhood_enabled: bool = Field(
        False, description="Whether Robinhood integration is enabled")
    robinhood_display: bool = Field(
        False, description="Whether to display Robinhood data")
    robinhood_username: Optional[str] = Field(
        None, description="Robinhood username")
    robinhood_password: Optional[str] = Field(
        None, description="Robinhood password (encrypted)")
    robinhood_mfa: Optional[str] = Field(
        None, description="Robinhood MFA token")
    last_robinhood_pull: Optional[str] = Field(
        None, description="Last Robinhood pull timestamp")
    robinhood_last_successful_pull: Optional[str] = Field(
        None, description="Last successful Robinhood pull")
    robinhood_last_error: Optional[str] = Field(
        None, description="Last Robinhood error message")

    @validator('total_portfolio_cash',
               'total_portfolio_btc',
               'btc_avg_buy_price')
    def validate_non_negative(cls, v):
        if v < 0:
            raise ValueError('Value must be non-negative')
        return round(v, 2)

    @validator('robinhood_username', 'robinhood_password', 'robinhood_mfa')
    def validate_robinhood_fields(cls, v):
        if v is not None and len(v.strip()) == 0:
            return None
        return v


class Position(BaseRecord):
    """Portfolio position model."""
    user: str = Field(..., description="User ID")
    symbol: str = Field(..., description="Stock/ETF symbol")
    quantity: float = Field(..., description="Number of shares")
    buy_price: float = Field(..., description="Average buy price per share")
    notes: Optional[str] = Field(None, description="Position notes")
    source: Optional[str] = Field(
        "manual", description="Data source (manual/robinhood)")
    pulled_at: Optional[str] = Field(None, description="Last pull timestamp")

    # Computed fields (not stored in DB)
    market_value: Optional[float] = Field(
        None, description="Current market value")
    todays_return: Optional[float] = Field(
        None, description="Today's return percentage")
    total_return: Optional[float] = Field(
        None, description="Total return percentage")
    beta: Optional[float] = Field(None, description="Stock beta")
    delta: Optional[float] = Field(None, description="Position delta")
    percent_of_portfolio: Optional[float] = Field(
        None, description="Percentage of total portfolio")

    @validator('symbol')
    def validate_symbol(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Symbol cannot be empty')
        return v.strip().upper()

    @validator('quantity', 'buy_price')
    def validate_positive(cls, v):
        if v <= 0:
            raise ValueError('Value must be positive')
        return round(v, 6) if isinstance(v, float) else v

    @validator('market_value', 'todays_return', 'total_return',
               'beta', 'delta', 'percent_of_portfolio')
    def validate_computed_fields(cls, v):
        if v is not None:
            return round(v, 2)
        return v


# =============================================================================
# ORDER MODELS
# =============================================================================

class Order(BaseRecord):
    """Trade order model."""
    user: str = Field(..., description="User ID")
    symbol: str = Field(..., description="Stock/ETF symbol")
    type: str = Field(..., description="Order type (buy/sell)")
    quantity: float = Field(..., description="Number of shares")
    price: float = Field(..., description="Price per share")
    date: str = Field(..., description="Order date (YYYY-MM-DD)")
    fees: Optional[float] = Field(0.0, description="Transaction fees")
    pl: Optional[float] = Field(None, description="Profit/Loss")
    source_id: Optional[str] = Field(None, description="External source ID")
    notes: Optional[str] = Field(None, description="Order notes")
    source: Optional[str] = Field(
        "manual", description="Data source (manual/robinhood)")
    pulled_at: Optional[str] = Field(None, description="Last pull timestamp")

    @validator('symbol')
    def validate_symbol(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Symbol cannot be empty')
        return v.strip().upper()

    @validator('type')
    def validate_type(cls, v):
        if v.lower() not in ['buy', 'sell']:
            raise ValueError('Type must be "buy" or "sell"')
        return v.lower()

    @validator('quantity', 'price')
    def validate_positive(cls, v):
        if v <= 0:
            raise ValueError('Value must be positive')
        return round(v, 6) if isinstance(v, float) else v

    @validator('fees')
    def validate_fees(cls, v):
        if v is None:
            return 0.0
        if v < 0:
            raise ValueError('Fees cannot be negative')
        return round(v, 2)

    @validator('date')
    def validate_date(cls, v):
        try:
            datetime.strptime(v, '%Y-%m-%d')
            return v
        except ValueError:
            raise ValueError('Date must be in YYYY-MM-DD format')


# =============================================================================
# DIVIDEND MODELS
# =============================================================================

class Dividend(BaseRecord):
    """Dividend payment model."""
    user: str = Field(..., description="User ID")
    symbol: str = Field(..., description="Stock/ETF symbol")
    amount: float = Field(..., description="Dividend amount")
    date: str = Field(..., description="Dividend date (YYYY-MM-DD)")
    record_date: Optional[str] = Field(
        None, description="Record date (YYYY-MM-DD)")
    payable_date: Optional[str] = Field(
        None, description="Payable date (YYYY-MM-DD)")
    state: Optional[str] = Field(
        None, description="Dividend state (paid/pending)")
    source: Optional[str] = Field(
        "manual", description="Data source (manual/robinhood)")
    pulled_at: Optional[str] = Field(None, description="Last pull timestamp")

    @validator('symbol')
    def validate_symbol(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Symbol cannot be empty')
        return v.strip().upper()

    @validator('amount')
    def validate_amount(cls, v):
        if v == 0:
            raise ValueError('Amount cannot be zero')
        return round(v, 2)

    @validator('date', 'record_date', 'payable_date')
    def validate_dates(cls, v):
        if v is None:
            return v
        try:
            datetime.strptime(v, '%Y-%m-%d')
            return v
        except ValueError:
            raise ValueError('Date must be in YYYY-MM-DD format')

    @validator('state')
    def validate_state(cls, v):
        if v is None:
            return v
        if v.lower() not in ['paid', 'pending']:
            raise ValueError('State must be "paid" or "pending"')
        return v.lower()


# =============================================================================
# SYMBOL CACHE MODELS
# =============================================================================

class SymbolCache(BaseRecord):
    """Symbol market data cache model."""
    symbol: str = Field(..., description="Stock/ETF symbol")
    price: Optional[float] = Field(None, description="Current price")
    date: str = Field(..., description="Cache date (YYYY-MM-DD)")
    beta: Optional[float] = Field(None, description="Stock beta")
    delta: Optional[float] = Field(None, description="Stock delta")

    @validator('symbol')
    def validate_symbol(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Symbol cannot be empty')
        return v.strip().upper()

    @validator('price')
    def validate_price(cls, v):
        if v is not None and v <= 0:
            raise ValueError('Price must be positive')
        return round(v, 2) if v is not None else v

    @validator('beta', 'delta')
    def validate_metrics(cls, v):
        if v is not None:
            return round(v, 4)
        return v

    @validator('date')
    def validate_date(cls, v):
        try:
            datetime.strptime(v, '%Y-%m-%d')
            return v
        except ValueError:
            raise ValueError('Date must be in YYYY-MM-DD format')

    def is_stale(self, max_age_hours: int = 24) -> bool:
        """Check if cache data is stale."""
        try:
            cache_date = datetime.strptime(self.date, '%Y-%m-%d')
            current_date = datetime.now().date()
            return cache_date.date() < current_date
        except (ValueError, TypeError):
            return True

    @classmethod
    def create_from_market_data(
            cls, symbol: str, market_data: Dict[str, Any]) -> 'SymbolCache':
        """Create SymbolCache from market data dictionary."""
        return cls(
            symbol=symbol,
            price=market_data.get('last_price'),
            date=time.strftime('%Y-%m-%d'),
            beta=market_data.get('beta'),
            delta=market_data.get('delta')
        )


# =============================================================================
# PROFIT/LOSS MODELS
# =============================================================================

class ProfitLoss(BaseRecord):
    """Profit/Loss record model."""
    user: str = Field(..., description="User ID")
    symbol: str = Field(..., description="Stock/ETF symbol")
    type: str = Field(..., description="P/L type (Unrealized/Realized)")
    amount: float = Field(..., description="P/L amount")
    period: Optional[str] = Field(
        None, description="Time period (1W/1M/3M/YTD/MAX)")
    date: Optional[str] = Field(None, description="Calculation date")
    calculated_at: Optional[str] = Field(
        None, description="Calculation timestamp")
    source: Optional[str] = Field("manual", description="Data source")

    @validator('symbol')
    def validate_symbol(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Symbol cannot be empty')
        return v.strip().upper()

    @validator('type')
    def validate_type(cls, v):
        if v.lower() not in ['unrealized', 'realized']:
            raise ValueError('Type must be "Unrealized" or "Realized"')
        return v.title()

    @validator('period')
    def validate_period(cls, v):
        if v is not None and v.upper() not in ['1W', '1M', '3M', 'YTD', 'MAX']:
            raise ValueError('Period must be one of: 1W, 1M, 3M, YTD, MAX')
        return v.upper() if v else v

    @validator('amount')
    def validate_amount(cls, v):
        return round(v, 2)


class ProfitLossCache(BaseRecord):
    """Profit/Loss summary cache model."""
    user: str = Field(..., description="User ID")
    period: str = Field(..., description="Time period (1W/1M/3M/YTD/MAX)")
    total: float = Field(..., description="Total P/L")
    unrealized: float = Field(..., description="Unrealized P/L")
    realized: float = Field(..., description="Realized P/L")
    calculated_at: str = Field(..., description="Calculation timestamp")
    last_updated: str = Field(..., description="Last update timestamp")

    @validator('period')
    def validate_period(cls, v):
        if v.upper() not in ['1W', '1M', '3M', 'YTD', 'MAX']:
            raise ValueError('Period must be one of: 1W, 1M, 3M, YTD, MAX')
        return v.upper()

    @validator('total', 'unrealized', 'realized')
    def validate_amounts(cls, v):
        return round(v, 2)

    @model_validator(mode='after')
    def validate_total_consistency(self):
        """Ensure total equals unrealized + realized."""
        total = self.total
        unrealized = self.unrealized
        realized = self.realized

        if abs(total - (unrealized + realized)
               ) > 0.01:  # Allow small rounding differences
            raise ValueError('Total must equal unrealized + realized')
        return self


# =============================================================================
# FRONTEND DATA MODELS
# =============================================================================

class PortfolioSummary(BaseModel):
    """Portfolio summary for frontend display."""
    positions: List[Position] = Field(
        default_factory=list,
        description="Portfolio positions")
    total_value: float = Field(0.0, description="Total portfolio value")
    total_cash: float = Field(0.0, description="Total cash")
    total_btc: float = Field(0.0, description="Total BTC value")
    btc_avg_price: float = Field(0.0, description="Average BTC buy price")


class MarketData(BaseModel):
    """Market data structure for API responses."""
    symbol: str = Field(..., description="Stock/ETF symbol")
    last_price: Optional[float] = Field(None, description="Current price")
    previous_close: Optional[float] = Field(
        None, description="Previous close price")
    change: Optional[float] = Field(None, description="Price change")
    change_percent: Optional[float] = Field(
        None, description="Price change percentage")
    volume: Optional[int] = Field(None, description="Trading volume")
    beta: Optional[float] = Field(None, description="Stock beta")
    timestamp: Optional[str] = Field(None, description="Data timestamp")

    @validator('last_price', 'previous_close', 'change', 'change_percent')
    def validate_prices(cls, v):
        if v is not None:
            return round(v, 2)
        return v

    @validator('beta')
    def validate_beta(cls, v):
        if v is not None:
            return round(v, 4)
        return v


# =============================================================================
# SCHEMA DEFINITIONS FOR DB_INIT
# =============================================================================

def get_collection_schemas() -> Dict[str, Dict[str, Any]]:
    """Get collection schemas for database initialization."""
    return {
        "portfolio": {
            "user": {"type": "relation", "required": True, "options": {"collectionId": "users"}},
            "total_portfolio_cash": {"type": "number", "required": False},
            "total_portfolio_btc": {"type": "number", "required": False},
            "btc_avg_buy_price": {"type": "number", "required": False},
            "robinhood_enabled": {"type": "bool", "required": False},
            "robinhood_display": {"type": "bool", "required": False},
            "robinhood_username": {"type": "text", "required": False},
            "robinhood_password": {"type": "text", "required": False},
            "robinhood_mfa": {"type": "text", "required": False},
            "last_robinhood_pull": {"type": "text", "required": False},
            "robinhood_last_successful_pull": {"type": "text", "required": False},
            "robinhood_last_error": {"type": "text", "required": False}
        },
        "positions": {
            "user": {"type": "relation", "required": True, "options": {"collectionId": "users"}},
            "symbol": {"type": "text", "required": True},
            "quantity": {"type": "number", "required": True},
            "buy_price": {"type": "number", "required": True},
            "notes": {"type": "text", "required": False},
            "source": {"type": "text", "required": False},
            "pulled_at": {"type": "text", "required": False}
        },
        "orders": {
            "user": {"type": "relation", "required": True, "options": {"collectionId": "users"}},
            "symbol": {"type": "text", "required": True},
            "type": {"type": "text", "required": True},
            "quantity": {"type": "number", "required": True},
            "price": {"type": "number", "required": True},
            "date": {"type": "text", "required": True},
            "fees": {"type": "number", "required": False},
            "pl": {"type": "number", "required": False},
            "source_id": {"type": "text", "required": False},
            "notes": {"type": "text", "required": False},
            "source": {"type": "text", "required": False},
            "pulled_at": {"type": "text", "required": False}
        },
        "dividends": {
            "user": {"type": "relation", "required": True, "options": {"collectionId": "users"}},
            "symbol": {"type": "text", "required": True},
            "amount": {"type": "number", "required": True},
            "date": {"type": "text", "required": True},
            "record_date": {"type": "text", "required": False},
            "payable_date": {"type": "text", "required": False},
            "state": {"type": "text", "required": False},
            "source": {"type": "text", "required": False},
            "pulled_at": {"type": "text", "required": False}
        },
        "symbol_cache": {
            "symbol": {"type": "text", "required": True},
            "price": {"type": "number", "required": False},
            "date": {"type": "text", "required": False},
            "beta": {"type": "number", "required": False},
            "delta": {"type": "number", "required": False}
        },
        "profit_loss": {
            "user": {"type": "relation", "required": True, "options": {"collectionId": "users"}},
            "symbol": {"type": "text", "required": True},
            "type": {"type": "text", "required": True},
            "amount": {"type": "number", "required": True, "options": {"nonZero": False}},
            "period": {"type": "text", "required": False},
            "date": {"type": "text", "required": False},
            "calculated_at": {"type": "text", "required": False},
            "source": {"type": "text", "required": False}
        },
        "profit_loss_cache": {
            "user": {"type": "relation", "required": True, "options": {"collectionId": "users"}},
            "period": {"type": "text", "required": True},
            "total": {"type": "number", "required": True},
            "unrealized": {"type": "number", "required": True},
            "realized": {"type": "number", "required": True},
            "calculated_at": {"type": "text", "required": True},
            "last_updated": {"type": "text", "required": True}
        }
    }


# =============================================================================
# VALIDATION UTILITIES
# =============================================================================

def validate_portfolio_data(data: Dict[str, Any]) -> PortfolioSettings:
    """Validate and create PortfolioSettings from dictionary."""
    return PortfolioSettings(**data)


def validate_position_data(data: Dict[str, Any]) -> Position:
    """Validate and create Position from dictionary."""
    return Position(**data)


def validate_order_data(data: Dict[str, Any]) -> Order:
    """Validate and create Order from dictionary."""
    return Order(**data)


def validate_dividend_data(data: Dict[str, Any]) -> Dividend:
    """Validate and create Dividend from dictionary."""
    return Dividend(**data)


def validate_symbol_cache_data(data: Dict[str, Any]) -> SymbolCache:
    """Validate and create SymbolCache from dictionary."""
    return SymbolCache(**data)


def validate_profit_loss_data(data: Dict[str, Any]) -> ProfitLoss:
    """Validate and create ProfitLoss from dictionary."""
    return ProfitLoss(**data)


def validate_profit_loss_cache_data(data: Dict[str, Any]) -> ProfitLossCache:
    """Validate and create ProfitLossCache from dictionary."""
    return ProfitLossCache(**data)


# =============================================================================
# DATA TRANSFORMATION UTILITIES
# =============================================================================

def transform_pocketbase_record(
        record: Dict[str, Any], model_class: type) -> BaseModel:
    """Transform PocketBase record to Pydantic model."""
    # Remove PocketBase metadata fields
    clean_data = {
        k: v for k,
        v in record.items() if k not in [
            'id',
            'created',
            'updated',
            'collectionId',
            'collectionName']}

    # Handle relation fields (expand user ID)
    if 'user' in clean_data and isinstance(clean_data['user'], dict):
        clean_data['user'] = clean_data['user'].get('id', clean_data['user'])

    return model_class(**clean_data)


def transform_to_pocketbase_data(model: BaseModel) -> Dict[str, Any]:
    """Transform Pydantic model to PocketBase data format."""
    data = model.dict(exclude={'id', 'created', 'updated'})

    # Remove None values for optional fields
    clean_data = {k: v for k, v in data.items() if v is not None}

    return clean_data


# =============================================================================
# MODEL REGISTRY
# =============================================================================

MODEL_REGISTRY = {
    'portfolio': PortfolioSettings,
    'positions': Position,
    'orders': Order,
    'dividends': Dividend,
    'symbol_cache': SymbolCache,
    'profit_loss': ProfitLoss,
    'profit_loss_cache': ProfitLossCache
}


def get_model_class(collection_name: str) -> Optional[type]:
    """Get the Pydantic model class for a collection."""
    return MODEL_REGISTRY.get(collection_name)


def validate_collection_data(
        collection_name: str, data: Dict[str, Any]) -> BaseModel:
    """Validate data for a specific collection."""
    model_class = get_model_class(collection_name)
    if not model_class:
        raise ValueError(f"No model found for collection: {collection_name}")

    return model_class(**data)
