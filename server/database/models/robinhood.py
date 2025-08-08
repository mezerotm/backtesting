"""
Robinhood credentials and data models.
"""

from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class RobinhoodCredentials(BaseModel):
    """Robinhood API credentials model."""

    id: str
    user_id: str
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_at: datetime
    scope: Optional[str] = None
    is_active: bool = True
    last_sync: Optional[datetime] = None
    sync_status: str = "idle"  # idle, syncing, error
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RobinhoodPosition(BaseModel):
    """Robinhood position data model."""

    id: str
    user_id: str
    robinhood_id: str
    symbol: str
    quantity: float
    cost_basis: float
    average_buy_price: float
    instrument_id: str
    instrument_url: str
    is_crypto: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RobinhoodOrder(BaseModel):
    """Robinhood order data model."""

    id: str
    user_id: str
    robinhood_id: str
    symbol: str
    side: str  # buy, sell
    quantity: float
    price: float
    state: str  # filled, cancelled, pending, etc.
    type: str  # market, limit, etc.
    time_in_force: str  # gfd, gtc, ioc, opg
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RobinhoodCredentialsCreate(BaseModel):
    """Model for creating Robinhood credentials."""

    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_at: datetime
    scope: Optional[str] = None


class RobinhoodCredentialsUpdate(BaseModel):
    """Model for updating Robinhood credentials."""

    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    is_active: Optional[bool] = None
    last_sync: Optional[datetime] = None
    sync_status: Optional[str] = None
    error_message: Optional[str] = None
