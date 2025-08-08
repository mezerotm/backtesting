"""
Models package for consistent data management across the application.
Provides unified interfaces for reading, writing, and managing data using PocketBase.
"""

from .model_manager import ModelManager, get_model_manager, shutdown_model_manager
from .data_models import (
    # Base models
    BaseRecord,

    # Portfolio models
    PortfolioSettings, Position, PortfolioSummary,

    # Order models
    Order,

    # Dividend models
    Dividend,

    # Symbol cache models
    SymbolCache,

    # Profit/Loss models
    ProfitLoss, ProfitLossCache,

    # Market data models
    MarketData,

    # Validation functions
    validate_portfolio_data, validate_position_data, validate_order_data,
    validate_dividend_data, validate_symbol_cache_data, validate_profit_loss_data,
    validate_profit_loss_cache_data,

    # Transformation functions
    transform_pocketbase_record, transform_to_pocketbase_data,

    # Utility functions
    get_collection_schemas, get_model_class, validate_collection_data
)

__all__ = [
    # Model Manager
    'ModelManager',
    'get_model_manager',
    'shutdown_model_manager',

    # Data Models
    'BaseRecord',
    'PortfolioSettings',
    'Position',
    'PortfolioSummary',
    'Order',
    'Dividend',
    'SymbolCache',
    'ProfitLoss',
    'ProfitLossCache',
    'MarketData',

    # Validation Functions
    'validate_portfolio_data',
    'validate_position_data',
    'validate_order_data',
    'validate_dividend_data',
    'validate_symbol_cache_data',
    'validate_profit_loss_data',
    'validate_profit_loss_cache_data',

    # Transformation Functions
    'transform_pocketbase_record',
    'transform_to_pocketbase_data',

    # Utility Functions
    'get_collection_schemas',
    'get_model_class',
    'validate_collection_data'
]
