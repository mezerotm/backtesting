# Database Management

This project uses PocketBase as the database for portfolio and market data management.

## Quick Start

### 1. Start the Database
```bash
make db-start
```

### 2. Initialize Database Schema
```bash
make db-init
```

### 3. Start the Application Server
```bash
make server
```

## Database Commands

- `make db-start` - Start PocketBase server
- `make db-init` - Initialize database collections
- `make db-reset` - Reset database (⚠️ deletes all data)
- `make db-backup` - Create database backup
- `make db-restore` - Restore from backup

## Database Architecture

### Collections

1. **portfolio** - Portfolio settings and cash data (user-specific)
2. **positions** - Portfolio positions with deduplication
3. **orders** - Trading orders with source tracking (Robinhood ID in source_id field)
4. **dividends** - Dividend data with deduplication
5. **symbol_cache** - Market data cache (price, beta, delta) with deduplication
6. **profit_loss** - Pre-calculated profit/loss records (unrealized/realized)

### Key Features

- **User Isolation**: All collections support multi-user data isolation
- **Deduplication**: Automatic prevention of duplicate records during data pulls
- **Source Tracking**: Orders track their origin via source_id field
- **Data Validation**: Robust validation and sanitization of incoming data
- **Upsert Logic**: Efficient update-or-create operations for all collections

## PocketBase Admin Interface

When PocketBase is running, access the admin interface at:
- **URL**: http://127.0.0.1:8090/_/
- **Default Admin**: No default admin (create one on first access)

## File Structure

```
├── libs/
│   └── pocketbase          # PocketBase binary
├── pb_data/                # PocketBase data directory
├── server/models/          # Model definitions
├── utils/
│   ├── pocketbase_client.py # PocketBase client
│   └── db_init.py          # Database initialization
└── Makefile                # Database management commands
```

## Development Workflow

### Typical Development Session
```bash
# 1. Start database
make db-start

# 2. In another terminal, start application
make server

# 3. When done, stop database (Ctrl+C in db-start terminal)
```

### Testing Database Operations
```bash
# Initialize fresh database
make db-reset
make db-init
```

### Fresh Start Workflow
```bash
# 1. Clear database and start fresh
make db-reset

# 2. Initialize schema (must be run from project root)
make db-init

# 3. Start server
make server

# 4. Create admin account in PocketBase UI (http://127.0.0.1:8090/_/)

# 5. Login to dashboard and test APIs
```

### Logging During Fresh Starts
- **Expected Warnings**: Authentication failures during fresh starts are logged as warnings, not errors
- **Clean Logs**: No alarming error messages for expected behavior
- **Context**: Logs explain when failures are expected (e.g., "expected for fresh starts")

## Recent Improvements

### Beta Calculation Fix
The database system includes a fix for the beta calculation issue:
- **Cache Model**: Properly stores and retrieves beta values
- **Beta Persistence**: Beta values are now saved in the cache structure
- **Automatic Calculation**: Beta calculation is triggered during data refresh

### Data Integrity Improvements
- **Deduplication**: All collections now prevent duplicate records during data pulls
- **Symbol Cache**: Efficient bulk upsert with in-memory deduplication
- **Orders**: Source tracking with Robinhood ID in dedicated source_id field
- **Profit/Loss**: Pre-calculated records with upsert logic to prevent duplicates

### Authentication & Logging
- **Clean Logs**: Expected authentication failures logged as warnings, not errors
- **Fresh Start Handling**: Graceful handling of authentication during database resets
- **User Isolation**: All data properly isolated by user ID
- **Comprehensive Logging**: Separate log files for APIs, validation, and widgets

The beta values should now appear correctly in the portfolio table, and all data operations are more robust and user-friendly. 