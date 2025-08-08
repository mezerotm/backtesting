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
from typing import List, Dict, Any, Optional, Union, ClassVar, Type
from datetime import datetime, date
from decimal import Decimal
import time
import logging

logger = logging.getLogger(__name__)

# =============================================================================
# BASE MODELS
# =============================================================================


class BaseModelWithFrontend(BaseModel):
    """Base model with frontend data conversion methods."""

    # Override this in child classes to define field mappings
    # Format: Dict[frontend_field_name, backend_field_name]
    frontend_field_map: ClassVar[Dict[str, str]] = {}

    def to_frontend_dict(self) -> dict:
        """Convert model to frontend-friendly dictionary with mapped field names."""
        data = self.model_dump()
        logger.debug(
            f"[{self.__class__.__name__}] Converting to frontend dict - Input: {data}")

        # Create a copy to avoid modifying the original
        converted_data = data.copy()

        # Map backend field names to frontend field names
        # Note: We need to reverse the mapping for to_frontend_dict
        backend_to_frontend = {v: k for k,
                               v in self.frontend_field_map.items()}
        for backend_field, frontend_field in backend_to_frontend.items():
            if backend_field in converted_data:
                converted_data[frontend_field] = converted_data.pop(
                    backend_field)

        logger.debug(
            f"[{self.__class__.__name__}] Converted to frontend dict - Output: {converted_data}")
        return converted_data

    @classmethod
    def from_frontend_dict(
            cls: Type['BaseModelWithFrontend'],
            data: dict) -> 'BaseModelWithFrontend':
        """Create instance from frontend data with mapped field names."""
        logger.debug(
            f"[{cls.__name__}] Converting from frontend dict - Input: {data}")
        logger.debug(f"[{cls.__name__}] Using field map: {
                     cls.frontend_field_map}")

        # Create a copy of the data to avoid modifying the original
        converted_data = data.copy()

        # Map frontend field names to backend field names
        for frontend_field, backend_field in cls.frontend_field_map.items():
            if frontend_field in converted_data:
                logger.debug(f"[{cls.__name__}] Mapping {
                             frontend_field} -> {backend_field}")
                converted_data[backend_field] = converted_data.pop(
                    frontend_field)

        logger.debug(f"[{cls.__name__}] Creating instance with data: {
                     converted_data}")
        try:
            instance = cls(**converted_data)
            logger.debug(
                f"[{cls.__name__}] Successfully created instance: {instance}")
            return instance
        except Exception as e:
            logger.error(f"[{cls.__name__}] Error creating instance: {str(e)}")
            raise


class BaseRecord(BaseModelWithFrontend):
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
    # Frontend field mapping (frontend_name: backend_name)
    frontend_field_map: ClassVar[Dict[str, str]] = {
        "total_portfolio_cash": "total_portfolio_cash",  # Same name
        "robinhood_enabled": "robinhood_enabled",       # Same name
        "total_portfolio_btc": "total_portfolio_btc",   # Same name
        "btc_avg_buy_price": "btc_avg_buy_price",      # Same name
        "robinhood_username": "robinhood_username",     # Same name
        "robinhood_password": "robinhood_password",     # Same name
        "robinhood_mfa": "robinhood_mfa"               # Same name
    }

    user: str = Field(..., description="User ID")
    total_portfolio_cash: Decimal = Field(
        default=Decimal('0'),
        description="Total cash in portfolio")
    total_portfolio_btc: Decimal = Field(
        default=Decimal('0'),
        description="Total BTC value in USD")
    btc_avg_buy_price: Decimal = Field(
        default=Decimal('0'),
        description="Average BTC buy price")
    robinhood_enabled: bool = Field(
        default=False,
        description="Whether Robinhood integration is enabled")
    robinhood_username: Optional[str] = Field(
        None, description="Robinhood username")
    robinhood_password: Optional[str] = Field(
        None, description="Robinhood password")
    robinhood_mfa: Optional[str] = Field(
        None, description="Robinhood MFA token")
    sync_interval: int = Field(default=600,
                               description="Sync interval in seconds")

    @validator('total_portfolio_cash',
               'total_portfolio_btc',
               'btc_avg_buy_price')
    def validate_non_negative(cls, v):
        """Ensure numeric values are non-negative."""
        if v < 0:
            raise ValueError('Value must be non-negative')
        return v

    @validator('robinhood_username', 'robinhood_password', 'robinhood_mfa')
    def validate_robinhood_fields(cls, v):
        """Clean up Robinhood credential fields."""
        if v is not None and len(str(v).strip()) == 0:
            return None
        return v

    @validator('sync_interval')
    def validate_sync_interval(cls, v):
        """Ensure sync interval is reasonable."""
        if v < 60:  # Minimum 1 minute
            raise ValueError('Sync interval must be at least 60 seconds')
        if v > 86400:  # Maximum 24 hours
            raise ValueError(
                'Sync interval must be at most 86400 seconds (24 hours)')
        return v


class Position(BaseRecord):
    """Position model for individual holdings."""
    # Frontend field mapping
    frontend_field_map: ClassVar[Dict[str, str]] = {
        "quantity": "amount",
        "buy_price": "avg_buy_price",
        "pulled_at": "created_at"
    }

    user: str  # Changed from user_id to match DB schema
    symbol: str
    quantity: Decimal
    buy_price: Decimal  # Changed from cost_basis to match DB schema
    market_value: Optional[Decimal] = None
    current_price: Optional[Decimal] = None
    total_return: Optional[Decimal] = None
    total_return_percent: Optional[Decimal] = None
    percent_of_portfolio: Optional[Decimal] = None
    beta: Optional[Decimal] = None
    delta: Optional[Decimal] = None
    is_crypto: bool = False
    source: str = "manual"  # manual, robinhood, etc.
    notes: Optional[str] = None
    pulled_at: Optional[str] = None
    updated_at: Optional[datetime] = None

    @validator('symbol')
    def validate_symbol(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Symbol cannot be empty')
        if len(v) > 10:  # Most symbols are 1-5 chars, allow up to 10 for crypto
            raise ValueError('Symbol too long')
        return v.strip().upper()

    @validator('quantity')
    def validate_quantity(cls, v):
        if v <= 0:
            raise ValueError('Quantity must be positive')
        if v > 1_000_000_000:  # Reasonable upper limit
            raise ValueError('Quantity exceeds maximum allowed')
        return round(v, 8)  # Allow 8 decimal places for crypto

    @validator('buy_price')
    def validate_buy_price(cls, v):
        if v <= 0:
            raise ValueError('Buy price must be positive')
        if v > 1_000_000:  # Reasonable upper limit
            raise ValueError('Buy price exceeds maximum allowed')
        return round(v, 8)  # Allow 8 decimal places for crypto

    @validator('market_value', 'current_price')
    def validate_prices(cls, v):
        if v is not None:
            if v < 0:
                raise ValueError('Price cannot be negative')
            if v > 1_000_000:
                raise ValueError('Price exceeds maximum allowed')
            return round(v, 2)
        return v

    @validator('total_return', 'total_return_percent', 'percent_of_portfolio')
    def validate_percentages(cls, v):
        if v is not None:
            if v < -100_000 or v > 100_000:  # Allow large gains but set reasonable limits
                raise ValueError('Percentage out of reasonable range')
            return round(v, 4)  # 4 decimal places for percentages
        return v

    @validator('beta', 'delta')
    def validate_metrics(cls, v):
        if v is not None:
            if abs(v) > 10:  # Most betas/deltas are between -3 and 3
                raise ValueError('Metric exceeds reasonable range')
            return round(v, 4)
        return v

    @validator('notes')
    def validate_notes(cls, v):
        if v is not None:
            if len(v) > 1000:  # Reasonable limit for notes
                raise ValueError('Notes too long')
        return v

    @validator('source')
    def validate_source(cls, v):
        valid_sources = {'manual', 'robinhood', 'api'}
        if v.lower() not in valid_sources:
            raise ValueError(
                f'Invalid source. Must be one of: {
                    ", ".join(valid_sources)}')
        return v.lower()


# =============================================================================
# ORDER MODELS
# =============================================================================

class Order(BaseRecord):
    """Trade order model."""
    # Frontend field mapping
    frontend_field_map: ClassVar[Dict[str, str]] = {
        "price": "execution_price",
        "pulled_at": "created_at",
        "pl": "profit_loss"
    }

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
    # Frontend field mapping
    frontend_field_map: ClassVar[Dict[str, str]] = {
        "pulled_at": "created_at",
        "date": "payment_date"
    }

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
    # Frontend field mapping
    frontend_field_map: ClassVar[Dict[str, str]] = {
        "amount": "value",
        "type": "pl_type",
        "calculated_at": "timestamp",
        "date": "trade_date"
    }

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
    # Frontend field mapping
    frontend_field_map: ClassVar[Dict[str, str]] = {
        "total": "total_pl",
        "unrealized": "unrealized_pl",
        "realized": "realized_pl",
        "calculated_at": "timestamp",
        "last_updated": "updated_timestamp"
    }

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
            "market_value": {"type": "number", "required": False},
            "current_price": {"type": "number", "required": False},
            "total_return": {"type": "number", "required": False},
            "total_return_percent": {"type": "number", "required": False},
            # Added
            "percent_of_portfolio": {"type": "number", "required": False},
            "beta": {"type": "number", "required": False},  # Added
            "delta": {"type": "number", "required": False},  # Added
            "is_crypto": {"type": "bool", "required": False},
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

    # Handle date format conversion for Order model
    if model_class.__name__ == 'Order' and 'date' in clean_data:
        date_value = clean_data['date']
        if isinstance(date_value, str) and 'T' in date_value:
            # Convert ISO timestamp to YYYY-MM-DD format
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(date_value.replace('Z', '+00:00'))
                clean_data['date'] = dt.strftime('%Y-%m-%d')
            except BaseException:
                # If conversion fails, keep original
                pass

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
