import os
import pandas as pd
from backtesting import Backtest
import sys
import argparse
from datetime import datetime, date

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.data_fetcher import fetch_historical_data
from strategies.moving_average import SimpleMovingAverageCrossover, ExponentialMovingAverageCrossover
from strategies.advanced_strategy import MACDRSIStrategy, BollingerRSIStrategy
from utils import config
from utils.backtest_report_generator import create_backtest_report

def valid_date(s):
    """Convert string to date for argparse"""
    try:
        return datetime.strptime(s, "%Y-%m-%d").strftime("%Y-%m-%d")
    except ValueError:
        msg = f"Not a valid date: '{s}'. Use YYYY-MM-DD format."
        raise argparse.ArgumentTypeError(msg)

def parse_args():
    parser = argparse.ArgumentParser(description='Run backtesting strategy')
    
    # Update strategy choices
    parser.add_argument('--strategies', type=str, nargs='+', default=['sma'],
                      choices=['sma', 'ema', 'macd_rsi', 'bb_rsi', 'all'],
                      help='Strategies to run (sma, ema, macd_rsi, bb_rsi, or all)')
    
    # Add parameters for advanced strategies
    parser.add_argument('--macd-fast', type=int, default=12,
                      help='MACD fast period')
    parser.add_argument('--macd-slow', type=int, default=26,
                      help='MACD slow period')
    parser.add_argument('--macd-signal', type=int, default=9,
                      help='MACD signal period')
    parser.add_argument('--rsi-period', type=int, default=14,
                      help='RSI period')
    parser.add_argument('--rsi-overbought', type=int, default=70,
                      help='RSI overbought threshold')
    parser.add_argument('--rsi-oversold', type=int, default=30,
                      help='RSI oversold threshold')
    parser.add_argument('--bb-period', type=int, default=20,
                      help='Bollinger Bands period')
    parser.add_argument('--bb-dev', type=float, default=2.0,
                      help='Bollinger Bands standard deviation')
    
    # Required parameters
    parser.add_argument('--ticker', type=str, required=True,
                      help='Stock ticker symbol (e.g., AAPL)')
    
    # Optional parameters with defaults
    parser.add_argument('--start-date', type=valid_date, default="2022-01-01",
                      help='Start date in YYYY-MM-DD format')
    parser.add_argument('--end-date', type=valid_date, default=date.today().strftime("%Y-%m-%d"),
                      help='End date in YYYY-MM-DD format')
    parser.add_argument('--timeframe', type=str, default="1d",
                      choices=['1m', '5m', '15m', '30m', '1h', '1d'],
                      help='Trading timeframe')
    parser.add_argument('--initial-capital', type=float, default=10000,
                      help='Initial capital for backtesting')
    parser.add_argument('--commission', type=float, default=0.001,
                      help='Commission rate (e.g., 0.001 for 0.1%)')
    
    # Strategy parameters
    parser.add_argument('--fast-ma', type=int, default=50,
                      help='Fast moving average period')
    parser.add_argument('--slow-ma', type=int, default=200,
                      help='Slow moving average period')
    
    # Optimization flag
    parser.add_argument('--optimize', action='store_true',
                      help='Run parameter optimization')
    
    return parser.parse_args()

def run_backtest(args):
    # Create results directory if it doesn't exist
    results_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')
    os.makedirs(results_dir, exist_ok=True)
    
    # Determine which strategies to run
    strategies_to_run = []
    if 'all' in args.strategies:
        strategies_to_run = ['sma', 'ema', 'macd_rsi', 'bb_rsi']
    else:
        strategies_to_run = args.strategies
    
    # Fetch data once for all strategies
    print(f"Fetching data for {args.ticker} from {args.start_date} to {args.end_date}...")
    df = fetch_historical_data(
        ticker=args.ticker,
        start_date=args.start_date,
        end_date=args.end_date,
        timeframe=args.timeframe
    )
    
    # Dictionary to store results
    results = {}
    
    # Strategy configurations
    strategy_configs = {
        'sma': {
            'name': 'SMA',
            'class': SimpleMovingAverageCrossover,
            'setup': lambda: setattr(SimpleMovingAverageCrossover, 'fast_ma', args.fast_ma) or 
                           setattr(SimpleMovingAverageCrossover, 'slow_ma', args.slow_ma)
        },
        'ema': {
            'name': 'EMA',
            'class': ExponentialMovingAverageCrossover,
            'setup': lambda: setattr(ExponentialMovingAverageCrossover, 'fast_ema', args.fast_ma) or 
                           setattr(ExponentialMovingAverageCrossover, 'slow_ema', args.slow_ma)
        },
        'macd_rsi': {
            'name': 'MACD+RSI',
            'class': MACDRSIStrategy,
            'setup': lambda: setattr(MACDRSIStrategy, 'macd_fast', args.macd_fast) or 
                           setattr(MACDRSIStrategy, 'macd_slow', args.macd_slow) or
                           setattr(MACDRSIStrategy, 'macd_signal', args.macd_signal) or
                           setattr(MACDRSIStrategy, 'rsi_period', args.rsi_period) or
                           setattr(MACDRSIStrategy, 'rsi_oversold', args.rsi_oversold) or
                           setattr(MACDRSIStrategy, 'rsi_overbought', args.rsi_overbought)
        },
        'bb_rsi': {
            'name': 'BB+RSI',
            'class': BollingerRSIStrategy,
            'setup': lambda: setattr(BollingerRSIStrategy, 'bb_period', args.bb_period) or
                           setattr(BollingerRSIStrategy, 'bb_dev', args.bb_dev) or
                           setattr(BollingerRSIStrategy, 'rsi_period', args.rsi_period) or
                           setattr(BollingerRSIStrategy, 'rsi_oversold', args.rsi_oversold) or
                           setattr(BollingerRSIStrategy, 'rsi_overbought', args.rsi_overbought)
        }
    }
    
    # Run selected strategies
    for strategy_id in strategies_to_run:
        config = strategy_configs[strategy_id]
        print(f"\nRunning {config['name']} Strategy...")
        
        # Setup strategy parameters
        config['setup']()
        
        # Run backtest
        bt = Backtest(
            df,
            config['class'],
            cash=args.initial_capital,
            commission=args.commission
        )
        
        stats = bt.run()
        results[config['name']] = stats
        
        # Generate plot
        output = os.path.join(results_dir, 
                            f"{args.ticker}_{config['name']}_{args.timeframe}_{args.start_date}_{args.end_date}.html")
        bt.plot(filename=output, open_browser=True)
        print(f"{config['name']} Plot saved to: {output}")
    
    # Print comparison if multiple strategies were run
    if len(results) > 1:
        print("\nStrategy Comparison:")
        print("-" * 80)
        metrics = ['Return [%]', 'Buy & Hold Return [%]', 'Max. Drawdown [%]', 'Sharpe Ratio', '# Trades']
        
        # Create header
        strategies = list(results.keys())
        print(f"{'Metric':<20}", end='')
        for strategy in strategies:
            print(f"{strategy:>15}", end='')
        print("\n" + "-" * 80)
        
        # Print metrics
        for metric in metrics:
            print(f"{metric:<20}", end='')
            for strategy in strategies:
                value = results[strategy][metric]
                print(f"{value:>15.2f}", end='')
            print()
    
    # After the results comparison, replace the create_html_report call with:
    report_path = create_backtest_report(results, args, results_dir)
    print(f"\nDetailed HTML report saved to: {report_path}")
    
    return results

if __name__ == "__main__":
    args = parse_args()
    run_backtest(args) 