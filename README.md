# Trading Strategy Backtesting Framework

This framework provides tools for backtesting trading strategies using TA-Lib indicators and the Backtesting.py library. It allows for easy comparison between different strategies on historical data.

## ⚠️ Security Notice

**IMPORTANT**: This application serves static files from the `public/` directory only. Source code directories (`server/`, `utils/`, `strategies/`, `workflows/`, `libs/`, `logs/`) are never exposed to users.

When adding new static assets:
- Place files in `public/` directory
- Reference them as `/static/filename` in HTML/CSS/JS
- Never serve source code directories

## Features

- Multiple pre-built strategies:
  - Simple Moving Average (SMA) Crossover
  - Exponential Moving Average (EMA) Crossover
  - MACD + RSI + EMA Trend Filter
  - Bollinger Bands + RSI

- Easy strategy comparison:
  - Visual performance metrics comparison
  - Detailed statistics for each strategy
  - Export results to CSV

- Customizable backtesting parameters:
  - Initial capital
  - Commission rates
  - Date ranges
  - Symbols

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd backtesting-api
```

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

Note: TA-Lib requires separate installation steps for the C library depending on your operating system. See [TA-Lib Installation Instructions](https://github.com/mrjbq7/ta-lib#installation).

## Usage

### Quick Start

Run a comparison of all strategies on the S&P 500 ETF (SPY):

```bash
python run_comparisons.py
```

### Customizing the Comparison

You can customize your backtest with various command-line arguments:

```bash
python run_comparisons.py --symbol AAPL --start 2020-01-01 --end 2023-01-01 --cash 100000 --commission 0.001 --strategies SMA EMA --csv results.csv
```

Available arguments:

- `--symbol`: Stock symbol to use (default: SPY)
- `--start`: Start date for data (YYYY-MM-DD) (default: 2018-01-01)
- `--end`: End date for data (YYYY-MM-DD) (default: today)
- `--cash`: Initial cash for backtesting (default: 10000)
- `--commission`: Commission rate for trades (default: 0.002)
- `--strategies`: Strategies to compare (choices: SMA, EMA, MACD, BB, ALL) (default: ALL)
- `--csv`: Export results to CSV file (optional)

### Creating Your Own Strategies

To create your own strategy, create a new Python file in the `strategies` directory and extend the `Strategy` class from Backtesting:

```python
from backtesting import Strategy
import talib

class YourCustomStrategy(Strategy):
    # Define parameters
    param1 = 20
    param2 = 50
    
    def init(self):
        # Calculate indicators
        self.indicator1 = self.I(talib.SMA, self.data.Close, self.param1)
        self.indicator2 = self.I(talib.RSI, self.data.Close, self.param2)
    
    def next(self):
        # Strategy logic
        if condition:
            self.buy()
        elif other_condition:
            self.position.close()
```

Then add your strategy to the comparison in `run_comparisons.py`.

## Example Strategies

### SimpleMovingAverageCrossover

A classic strategy that buys when a faster SMA crosses above a slower SMA and sells when the faster SMA crosses below the slower SMA. This serves as a baseline for comparison.

### ExponentialMovingAverageCrossover

Similar to the SMA crossover but using exponential moving averages, which give more weight to recent price changes.

### MACDRSIStrategy

An advanced strategy that combines MACD, RSI, and a trend-following EMA:
- Buys when MACD crosses above signal, RSI is between thresholds, and price is above trend EMA
- Sells when any of the opposite conditions occur

### BollingerRSIStrategy

A mean-reversion strategy that combines Bollinger Bands with RSI confirmation:
- Buys when price touches lower Bollinger Band and RSI is oversold
- Sells when price crosses middle/upper band or RSI becomes overbought

## Project Workflows

The project is organized into four main workflows, each with its own CLI entry point and supporting modules:

### Market Analysis Workflow
Analyzes market conditions, indices, and economic indicators.

```
market_workflow_cli.py (CLI) > workflows/market/
├── market_data.py (data fetching)
├── market_report_generator.py (report generation)
├── market_chart_generator.py (visualization)
└── market_check.html (template)
```

Usage:
```bash
python market_workflow_cli.py [--force-refresh] [--output-dir path/to/dir]
```

### Financial Analysis Workflow
Analyzes company financials and metrics.

```
financial_workflow_cli.py (CLI) > workflows/financial/
├── financial_data.py (data fetching)
├── financial_report_generator.py (report generation)
└── financial_report.html (template)
```

Usage:
```bash
python financial_workflow_cli.py --symbols AAPL MSFT [--years 5] [--output-dir path/to/dir]
```

### Backtest Strategy Workflow
Executes and analyzes individual trading strategies.

```
backtest_workflow_cli.py (CLI) > workflows/backtest/
├── backtest_data.py (data fetching)
├── backtest_report_generator.py (report generation)
├── strategy_utils.py (strategy utilities)
├── ai_explanations.py (AI-powered analysis)
└── backtest_report.html (template)
```

Usage:
```bash
python backtest_workflow_cli.py --symbol AAPL --strategy sma [--initial-capital 10000]
```

### Strategy Comparison Workflow
Compares multiple trading strategies side by side.

```
comparison_workflow_cli.py (CLI) > workflows/comparison/
├── compare_strategies.py (comparison logic)
└── strategy_comparison_report.py (report generation)
```

Usage:
```bash
python comparison_workflow_cli.py --symbol AAPL [--strategies sma ema macd bb] [--initial-capital 10000]
```

### Common Components
All workflows share common components:

- `workflows/base_fetcher.py`: Base class for data fetching with caching
- `templates/base_layout.html`: Common HTML template structure
- `templates/dashboard.html`: Central dashboard for all reports

### Data Fetching
Each workflow has its own dedicated data fetcher that extends the base fetcher:
- `workflows/market/market_data.py`: Market indices, rates, economic data
- `workflows/financial/financial_data.py`: Company financials and metrics
- `workflows/backtest/backtest_data.py`: Historical price data for backtesting

### Report Generation
Reports are generated in `public/results/` with:
- Timestamped directories for each run
- index.html for the main report
- raw_data.json for the underlying data
- Additional assets (charts, etc.)

### Dashboard Integration
All reports are integrated into a central dashboard:
- Generated reports appear in the dashboard automatically
- Access via http://localhost:8000/ when server is running
- Run `make server` to start the report server

## Database Management

The application uses PocketBase for portfolio and market data management with a robust ModelManager abstraction layer.

### Quick Database Setup
```bash
# Start database server
make db-start

# Initialize database schema (must be run from project root)
make db-init

# Start application server
make server
```

### Database Commands
- `make db-start` - Start PocketBase server
- `make db-init` - Initialize database collections (includes path verification)
- `make db-reset` - Reset database (⚠️ deletes all data)
- `make db-backup` - Create database backup
- `make db-restore` - Restore from backup

### Database Collections
- **portfolio** - Portfolio settings and cash data (user-specific)
- **positions** - Portfolio positions with deduplication
- **orders** - Trading orders with source tracking (Robinhood ID in source_id field)
- **dividends** - Dividend data with deduplication
- **symbol_cache** - Market data cache (price, beta, delta) with deduplication
- **profit_loss** - Pre-calculated profit/loss records (unrealized/realized)

### Key Features
- **User-Specific Data**: All collections support multi-user isolation
- **Deduplication**: Automatic prevention of duplicate records during data pulls
- **Source Tracking**: Orders track their origin (Robinhood, manual) via source_id
- **Data Validation**: Robust validation and sanitization of incoming data
- **Error Handling**: Graceful handling of partial data pull failures

### PocketBase Admin Interface
When PocketBase is running, access the admin interface at:
- **URL**: http://127.0.0.1:8090/_/
- **Default Admin**: No default admin (create one on first access)

For detailed database documentation, see [DATABASE.md](DATABASE.md).

### Configuration
Environment variables in `.env`:
```
POLYGON_API_KEY=your_polygon_key  # Optional - warnings shown if missing
FRED_API_KEY=your_fred_key
OPENAI_API_KEY=your_openai_key  # Optional, for AI explanations
ENV=development    # or production
```

### Logging System
The application uses a comprehensive logging system:
- **API Logs**: `logs/api/{api_name}.log` - Separate log files for each API
- **Validation Logs**: `logs/api/{api_name}_validation.log` - Data validation and sanitization logs
- **Widget Logs**: `logs/widgets/{widget_name}.log` - Frontend widget logs
- **Server Logs**: `logs/server.log` - Main server logs

### Authentication & Security
- **Session Management**: Cookie-based authentication with PocketBase
- **User Isolation**: All data is user-specific and properly isolated
- **Fresh Start Handling**: Graceful handling of authentication during fresh database starts
- **Error Classification**: Expected authentication failures logged as warnings, not errors

### Project Structure
```
├── workflows/
│   ├── market/
│   │   ├── market_data.py
│   │   ├── market_report_generator.py
│   │   ├── market_chart_generator.py
│   │   └── market_check.html
│   ├── financial/
│   │   ├── financial_data.py
│   │   ├── financial_report_generator.py
│   │   └── financial_report.html
│   ├── backtest/
│   │   ├── backtest_data.py
│   │   ├── backtest_report_generator.py
│   │   ├── strategy_utils.py
│   │   ├── ai_explanations.py
│   │   └── backtest_report.html
│   ├── comparison/
│   │   ├── compare_strategies.py
│   │   └── strategy_comparison_report.py
│   └── base_fetcher.py
├── server/
│   ├── models/             # Database models and ModelManager
│   ├── api/                # API endpoints (auth, portfolio, orders, dividends, profit_loss, robinhood)
│   ├── widgets/            # Frontend widgets
│   └── main.py             # FastAPI server
├── utils/
│   ├── pocketbase_client.py # PocketBase client
│   ├── db_init.py          # Database initialization (with path verification)
│   ├── logger.py           # Comprehensive logging system
│   └── config.py           # Configuration utilities
├── libs/
│   └── pocketbase          # PocketBase binary
├── pb_data/                # PocketBase data directory
├── templates/
│   ├── base_layout.html
│   └── dashboard.html
├── public/
│   ├── data/               # Legacy file storage
│   └── results/
├── market_workflow_cli.py
├── financial_workflow_cli.py
├── backtest_workflow_cli.py
├── comparison_workflow_cli.py
└── Makefile                # Database and build commands
```

## License

MIT License

### Template System
All report templates extend from a common base layout:

```
templates/
├── base_layout.html          # Common header, footer, and styling
├── market_check.html        ┐
├── financial_report.html    ├─ Extend base_layout.html
├── backtest_report.html     │
└── dashboard.html          ┘
```

The base layout provides:
- Consistent dark theme styling
- Responsive header with navigation
- Common footer with generation timestamp
- Shared dependencies (Tailwind CSS, Font Awesome)
- Standard meta tags and favicon

Example template inheritance:
```html
{% extends "base_layout.html" %}

{% block title %}Market Check - {{ date }}{% endblock %}

{% block content %}
  <!-- Report specific content -->
{% endblock %}

{% block generation_date %}{{ generated_at }}{% endblock %}
```

### Report Metadata
Each report generates standardized metadata using `utils/metadata_generator.py`:

```python
metadata = generate_metadata(
    symbol="AAPL",
    timeframe="daily",
    start_date="2023-01-01",
    end_date="2023-12-31",
    initial_capital=10000,
    commission=0.001,
    report_type="backtest",
    directory_name="backtest_20231231_235959",
    additional_data={
        "status": "finished",
        "strategy": "SMA Crossover"
    }
)
```

The metadata:
- Enables dashboard filtering and organization
- Tracks report status (finished/unfinished)
- Provides quick access to key report parameters
- Standardizes report identification
- Facilitates report cleanup and management

The dashboard uses this metadata to:
- Display report cards with key information
- Enable filtering by symbol, strategy, date range
- Sort reports by generation time
- Track report status for display
- Manage report lifecycle (creation to deletion)
