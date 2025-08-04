# Data Models and Schema Validation

This directory contains the data models and validation system for the backtesting application. The system ensures consistency between frontend, backend, and database operations.

## Overview

The data model system provides:

- **Type Safety**: Pydantic models with validation
- **Schema Consistency**: Unified data structures across the application
- **Data Transformation**: Utilities for converting between PocketBase records and Pydantic models
- **Validation**: Automatic validation of data integrity
- **Computed Fields**: Methods for calculating derived values

## File Structure

```
server/models/
├── __init__.py          # Package exports
├── model_manager.py     # PocketBase integration
├── data_models.py       # Pydantic models and validation
└── README.md           # This file
```

## Core Models

### Base Models

- **BaseRecord**: Base class for all database records with PocketBase metadata

### Portfolio Models

- **PortfolioSettings**: User portfolio configuration and settings
- **Position**: Individual stock/ETF positions
- **PortfolioSummary**: Aggregated portfolio data for frontend display

### Transaction Models

- **Order**: Trade orders (buy/sell transactions)
- **Dividend**: Dividend payments

### Market Data Models

- **SymbolCache**: Cached market data for symbols
- **MarketData**: Real-time market data structure

### Profit/Loss Models

- **ProfitLoss**: Individual P/L records
- **ProfitLossCache**: Aggregated P/L summaries

## Usage Examples

### Creating and Validating Data

```python
from server.models import Position, validate_position_data

# Create a position with validation
position_data = {
    "user": "user_123",
    "symbol": "AAPL",
    "quantity": 10.5,
    "buy_price": 150.25,
    "notes": "Test position"
}

try:
    position = validate_position_data(position_data)
    print(f"Valid position: {position.symbol}")
except Exception as e:
    print(f"Validation failed: {e}")
```

### Working with PocketBase Records

```python
from server.models import transform_pocketbase_record, transform_to_pocketbase_data

# Transform PocketBase record to model
pb_record = {
    "id": "record_123",
    "created": "2025-01-03T10:00:00.000Z",
    "symbol": "AAPL",
    "quantity": 10.5,
    "buy_price": 150.25
}

position = transform_pocketbase_record(pb_record, Position)

# Transform model back to PocketBase data
pb_data = transform_to_pocketbase_data(position)
```

### Portfolio Calculations

```python
from server.api.portfolio import create_portfolio_summary

# Create portfolio summary with computed values
summary = create_portfolio_summary(
    positions=positions,
    total_cash=1000.0,
    total_btc=500.0,
    btc_avg_price=45000.0
)

# Access computed percentages
for position in summary.positions:
    print(f"{position.symbol}: {position.percent_of_portfolio}%")
```

### Position Calculations

```python
# Calculate position metrics
position = Position(
    user="user_123",
    symbol="AAPL",
    quantity=10.0,
    buy_price=150.0
)

# Calculate amount invested (in portfolio API)
from server.api.portfolio import calculate_position_amount
amount = calculate_position_amount(position)  # $1,500.00

# Calculate market value (in portfolio API)
from server.api.portfolio import calculate_position_market_value
market_value = calculate_position_market_value(position, 160.0)  # $1,600.00

# Calculate returns (in portfolio API)
from server.api.portfolio import calculate_position_total_return, calculate_position_todays_return
total_return = calculate_position_total_return(position, 160.0)  # 6.67%
todays_return = calculate_position_todays_return(position, 160.0, 155.0)  # 3.23%
```

## Validation Rules

### Position Validation

- **symbol**: Required, non-empty, auto-uppercase
- **quantity**: Required, positive number
- **buy_price**: Required, positive number
- **market_value**: Optional, calculated from quantity × current_price
- **todays_return**: Optional, calculated percentage
- **total_return**: Optional, calculated percentage

### Symbol Cache Validation

- **symbol**: Required, non-empty, auto-uppercase
- **price**: Optional, positive number if provided
- **date**: Required, YYYY-MM-DD format
- **beta**: Optional, rounded to 4 decimal places
- **delta**: Optional, rounded to 4 decimal places

### Order Validation

- **type**: Must be "buy" or "sell"
- **quantity**: Required, positive number
- **price**: Required, positive number
- **date**: Required, YYYY-MM-DD format
- **fees**: Optional, non-negative number

### Dividend Validation

- **amount**: Required, non-zero number
- **date**: Required, YYYY-MM-DD format
- **record_date**: Optional, YYYY-MM-DD format
- **payable_date**: Optional, YYYY-MM-DD format

## Database Schema Integration

The data models are integrated with the database initialization system:

```python
from server.models import get_collection_schemas

# Get schemas for database initialization
schemas = get_collection_schemas()

# Use in db_init.py
for collection_name, fields in schemas.items():
    pb.create_collection(collection_name, fields)
```

## Testing

Run the test script to verify the data models work correctly:

```bash
python test_data_models.py
```

This will test:
- Model validation
- Data transformations
- Portfolio calculations
- Error handling

## Benefits

1. **Consistency**: All data follows the same structure
2. **Type Safety**: Pydantic provides runtime type checking
3. **Validation**: Automatic validation of data integrity
4. **Documentation**: Models serve as living documentation
5. **Maintainability**: Changes to data structure are centralized
6. **Separation of Concerns**: Data models focus on structure, business logic is in APIs
7. **Testing**: Easy to test data transformations and calculations

## Migration Guide

When updating existing code to use the new data models:

1. **Import the models**:
   ```python
   from server.models import Position, validate_position_data
   ```

2. **Replace direct dictionary access**:
   ```python
   # Old way
   symbol = position["symbol"]
   
   # New way
   symbol = position.symbol
   ```

3. **Use validation functions**:
   ```python
   # Old way
   position = {"symbol": "AAPL", "quantity": 10}
   
   # New way
   position = validate_position_data({"symbol": "AAPL", "quantity": 10})
   ```

4. **Use transformation functions**:
   ```python
   # Old way
   pb_data = {k: v for k, v in position.items() if k not in ['id', 'created']}
   
   # New way
   pb_data = transform_to_pocketbase_data(position)
   ```

## Future Enhancements

- **API Response Models**: Dedicated models for API responses
- **Bulk Operations**: Optimized bulk validation and transformation
- **Caching**: Cache validation results for performance
- **Migration Tools**: Tools for migrating existing data to new schemas 