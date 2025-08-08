"""
Portfolio and Position models for portfolio management.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pydantic import BaseModel, Field, validator


class Position(BaseModel):
    """Position model for individual holdings."""

    id: str
    user: str  # Changed from user_id to match DB schema
    symbol: str
    quantity: Decimal
    buy_price: Decimal  # Changed from cost_basis to match DB schema
    market_value: Optional[Decimal] = None
    current_price: Optional[Decimal] = None
    total_return: Optional[Decimal] = None
    total_return_percent: Optional[Decimal] = None
    is_crypto: bool = False
    source: str = "manual"  # manual, robinhood, etc.
    notes: Optional[str] = None
    # Changed from created_at to match DB schema
    pulled_at: Optional[str] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

    def to_frontend_dict(self) -> Dict[str, Any]:
        """Convert model to frontend-friendly dictionary."""
        return {
            "id": self.id,
            "symbol": self.symbol,
            "amount": float(self.quantity),
            "avg_buy_price": float(self.buy_price),
            "market_value": float(self.market_value) if self.market_value else None,
            "percent_of_portfolio": 0,  # Will be calculated by frontend
            "todays_return": 0,  # Will be calculated by frontend
            "total_return": float(self.total_return) if self.total_return else 0,
            "total_return_percent": float(self.total_return_percent) if self.total_return_percent else 0,
            "beta": 0,  # Will be calculated by frontend
            "delta": 0,  # Will be calculated by frontend
            "is_crypto": self.is_crypto,
            "notes": self.notes,
            "source": self.source,
            "created_at": self.pulled_at,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    @classmethod
    def from_frontend_dict(cls, data: Dict[str, Any]) -> 'Position':
        """Create instance from frontend data."""
        # Map frontend field names to model field names
        field_mapping = {
            'amount': 'quantity',
            'avg_buy_price': 'buy_price',
            'market_value': 'market_value',
            'is_crypto': 'is_crypto',
            'notes': 'notes'
        }

        # Map frontend fields to model fields
        model_data = {}
        for frontend_field, model_field in field_mapping.items():
            if frontend_field in data:
                model_data[model_field] = data[frontend_field]

        # Add required fields with defaults if not provided
        if 'symbol' in data:
            model_data['symbol'] = data['symbol']
        if 'id' in data:
            model_data['id'] = data['id']
        else:
            model_data['id'] = 'temp_' + \
                str(hash(str(data)))  # Generate temporary ID
        if 'user' in data:
            model_data['user'] = data['user']
        else:
            model_data['user'] = 'unknown'  # Default user

        return cls(**model_data)


class Portfolio(BaseModel):
    """Portfolio model for user portfolio settings."""

    id: str
    user_id: str
    portfolio_cash: Decimal
    total_market_value: Optional[Decimal] = None
    total_cost_basis: Optional[Decimal] = None
    total_return: Optional[Decimal] = None
    total_return_percent: Optional[Decimal] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PortfolioSettings(BaseModel):
    """Portfolio settings and configuration."""
    id: Optional[str] = None
    user_id: str
    portfolio_cash: Decimal = Field(
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
    auto_sync: bool = Field(
        default=True,
        description="Whether to auto-sync portfolio data")
    sync_interval: int = Field(default=600,
                               description="Sync interval in seconds")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @validator('portfolio_cash', 'total_portfolio_btc',
               'btc_avg_buy_price', pre=True)
    def convert_to_decimal(cls, v):
        """Convert numeric values to Decimal."""
        if v is None:
            return Decimal('0')
        try:
            decimal_value = Decimal(str(v))
            if decimal_value < 0:
                raise ValueError('Value must be non-negative')
            return decimal_value
        except (TypeError, ValueError, InvalidOperation) as e:
            raise ValueError(f'Invalid numeric value: {v}. Error: {str(e)}')

    @validator('robinhood_username', 'robinhood_password',
               'robinhood_mfa', pre=True)
    def validate_robinhood_fields(cls, v):
        """Clean up Robinhood credential fields."""
        if v is None:
            return None
        cleaned = str(v).strip()
        return cleaned if cleaned else None

    @validator('robinhood_enabled', 'auto_sync', pre=True)
    def validate_boolean_fields(cls, v):
        """Convert and validate boolean fields."""
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.lower() in ('true', '1', 'yes', 'on')
        if isinstance(v, (int, float)):
            return bool(v)
        return False

    @validator('sync_interval', pre=True)
    def validate_sync_interval(cls, v):
        """Convert and validate sync interval."""
        try:
            interval = int(v)
            if interval < 60:  # Minimum 1 minute
                raise ValueError('Sync interval must be at least 60 seconds')
            if interval > 86400:  # Maximum 24 hours
                raise ValueError(
                    'Sync interval must be at most 86400 seconds (24 hours)')
            return interval
        except (TypeError, ValueError) as e:
            raise ValueError(f'Invalid sync interval: {v}. Error: {str(e)}')

    def to_frontend_dict(self) -> Dict[str, Any]:
        """Convert model to frontend-friendly dictionary."""
        return {
            "portfolio_cash": float(self.portfolio_cash),
            "total_portfolio_btc": float(self.total_portfolio_btc),
            "btc_avg_buy_price": float(self.btc_avg_buy_price),
            "robinhood_enabled": self.robinhood_enabled,
            "robinhood_username": self.robinhood_username,
            "auto_sync": self.auto_sync,
            "sync_interval": self.sync_interval,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    @classmethod
    def from_frontend_dict(cls, data: Dict[str, Any]) -> 'PortfolioSettings':
        """Create instance from frontend data."""
        # Convert frontend field names to model field names
        field_mapping = {
            'total_portfolio_cash': 'portfolio_cash',
            'total_portfolio_btc': 'total_portfolio_btc',
            'btc_avg_buy_price': 'btc_avg_buy_price',
            'robinhood_enabled': 'robinhood_enabled',
            'robinhood_username': 'robinhood_username',
            'robinhood_password': 'robinhood_password',
            'robinhood_mfa': 'robinhood_mfa'
        }

        # Map frontend fields to model fields
        model_data = {}
        for frontend_field, model_field in field_mapping.items():
            if frontend_field in data:
                model_data[model_field] = data[frontend_field]

        # Add required user_id field
        if 'user_id' in data:
            model_data['user_id'] = data['user_id']
        else:
            model_data['user_id'] = 'unknown'  # Default user_id

        return cls(**model_data)


class PositionCreate(BaseModel):
    """Model for creating a new position."""

    symbol: str
    quantity: Decimal
    buy_price: Decimal  # Changed from cost_basis to match DB schema
    is_crypto: bool = False
    source: str = "manual"
    notes: Optional[str] = None


class PositionUpdate(BaseModel):
    """Model for updating a position."""

    quantity: Optional[Decimal] = None
    # Changed from cost_basis to match DB schema
    buy_price: Optional[Decimal] = None
    market_value: Optional[Decimal] = None
    current_price: Optional[Decimal] = None
    notes: Optional[str] = None


class PortfolioSummary(BaseModel):
    """Portfolio summary for API responses."""

    portfolio_cash: Decimal
    total_market_value: Decimal
    total_cost_basis: Decimal
    total_return: Decimal
    total_return_percent: Decimal
    positions_count: int
    last_updated: datetime
