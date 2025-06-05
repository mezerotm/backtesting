# Trading Strategy Backtesting Framework

This framework provides tools for backtesting trading strategies using TA-Lib indicators and the Backtesting.py library. It allows for easy comparison between different strategies on historical data.

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

The project follows a consistent pattern for different types of analysis:

### Common Pattern
Each workflow follows a CLI > Generator > HTML Template pattern:
```
CLI Script > Report Generator > HTML Template (extends base_layout.html)
```

### Market Check Workflow
Generates daily market snapshots with indices, rates, and economic indicators.

```
market_check.py > market_report_generator.py > market_check.html
└── utils/data_fetchers/market_data.py (data fetching)
```

Usage:
```bash
python market_check.py [--force-refresh] [--output-dir path/to/dir]
```

### Financial Analysis Workflow
Analyzes company financials and metrics.

```
financial_analysis.py > financial_report_generator.py > financial_report.html
└── utils/data_fetchers/financial_data.py (data fetching)
```

Usage:
```bash
python financial_analysis.py --symbols AAPL MSFT [--years 5] [--output-dir path/to/dir]
```

### Backtest Comparison Workflow
Compares different trading strategies.

```
backtest_comparisons.py > backtest_report_generator.py > backtest_report.html
└── utils/data_fetchers/backtest_data.py (data fetching)
```

Usage:
```bash
python backtest_comparisons.py --symbol AAPL [--strategies sma ema macd bb] [--initial-capital 10000]
```

### Data Fetching
Each workflow has its own dedicated data fetcher in `utils/data_fetchers/`:
- `base_fetcher.py`: Base class with caching functionality
- `market_data.py`: Market indices, rates, economic data
- `financial_data.py`: Company financials and metrics
- `backtest_data.py`: Historical price data for backtesting

### Caching
All data fetchers support caching with force-refresh capability:
- Cache location: `cache/data/`
- Cache duration: Configurable per data type
- Force refresh: Use `--force-refresh` flag to bypass cache

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
- Run `python -m utils.dashboard_generator` to start server

### Configuration
Environment variables in `.env`:
```
POLYGON_API_KEY=your_polygon_key
FRED_API_KEY=your_fred_key
OPENAI_API_KEY=your_openai_key  # Optional, for AI explanations
ENV=development    # or production
```

### Project Structure
```
├── public/
│   └── results/     # Generated reports
├── templates/       # HTML templates
│   ├── base_layout.html
│   ├── market_check.html
│   ├── financial_report.html
│   └── backtest_report.html
├── utils/
│   ├── data_fetchers/
│   │   ├── base_fetcher.py
│   │   ├── market_data.py
│   │   ├── financial_data.py
│   │   └── backtest_data.py
│   ├── market_report_generator.py
│   ├── financial_report_generator.py
│   ├── backtest_report_generator.py
│   └── dashboard_generator.py
├── market_check.py
├── financial_analysis.py
└── backtest_comparisons.py
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
