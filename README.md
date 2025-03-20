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

## License

MIT License
