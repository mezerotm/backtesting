import os
import pandas as pd
from backtesting import Backtest
import sys
import argparse
from datetime import datetime, date, timedelta

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.data_fetcher import fetch_historical_data
from strategies.moving_average import SimpleMovingAverageCrossover, ExponentialMovingAverageCrossover
from strategies.advanced_strategy import MACDRSIStrategy, BollingerRSIStrategy
from utils import config
from utils.metadata_generator import generate_metadata, save_metadata

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
    
    # Add flag for generating individual reports
    parser.add_argument('--generate-individual-reports', action='store_true',
                      help='Generate individual reports for each strategy in addition to comparison')
    
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
    
    # Required parameters - Changed ticker to symbol
    parser.add_argument('--symbol', type=str, required=True,
                      help='Stock symbol (e.g., AAPL)')
    
    # Optional parameters with defaults - Align with backtest_comparisons.py
    # Change default start date to 2 years ago instead of 10 years
    two_years_ago = (datetime.now() - timedelta(days=365*2)).strftime("%Y-%m-%d")
    parser.add_argument('--start-date', type=valid_date, default=two_years_ago,
                      help='Start date in YYYY-MM-DD format (default: 2 years ago)')
    parser.add_argument('--end-date', type=valid_date, default=None,
                      help='End date in YYYY-MM-DD format (default: today)')
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
    # Create public/results directory if it doesn't exist
    script_dir = os.path.dirname(os.path.abspath(__file__))
    public_dir = os.path.join(script_dir, 'public')
    results_base_dir = os.path.join(public_dir, 'results')
    os.makedirs(results_base_dir, exist_ok=True)
    
    # Import the backtest report generator at the beginning of the function
    from utils.backtest_report_generator import create_backtest_report
    
    # Determine which strategies to run
    strategies_to_run = []
    if 'all' in args.strategies:
        strategies_to_run = ['sma', 'ema', 'macd_rsi', 'bb_rsi']
    else:
        strategies_to_run = args.strategies
    
    # Set end date to today if not specified
    if args.end_date is None:
        args.end_date = datetime.today().strftime('%Y-%m-%d')  # Update args.end_date directly
    
    end_date = args.end_date  # Now end_date will always have a value
    
    # Check if start date is more than 2 years ago and warn the user
    start_date_obj = datetime.strptime(args.start_date, "%Y-%m-%d")
    two_years_ago = datetime.now() - timedelta(days=365*2)
    
    if start_date_obj < two_years_ago:
        original_start_date = args.start_date
        args.start_date = two_years_ago.strftime("%Y-%m-%d")
        print(f"\n⚠️ WARNING: The requested start date ({original_start_date}) is more than 2 years ago.")
        print(f"Due to data provider limitations, only 2 years of historical data is available.")
        print(f"Adjusting start date to {args.start_date}.\n")
    
    # Fetch data once for all strategies - Updated to use symbol instead of ticker
    print(f"Fetching data for {args.symbol} from {args.start_date} to {end_date}...")
    df = fetch_historical_data(
        ticker=args.symbol,  # Using symbol but keeping ticker parameter name for compatibility
        start_date=args.start_date,
        end_date=end_date,
        timeframe=args.timeframe
    )
    
    # Dictionary to store results and chart paths
    results = {}
    chart_paths = {}
    
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
            data=df,
            strategy=config['class'],
            cash=args.initial_capital,
            commission=args.commission
        )
        
        stats = bt.run()  # Run once and store stats
        results[config['name']] = stats
        
        # Create a directory for this strategy's results - Updated to use symbol
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        strategy_dir_name = f"{args.symbol}_{config['name']}_{args.timeframe}_{timestamp}"
        strategy_dir = os.path.join(results_base_dir, strategy_dir_name)
        os.makedirs(strategy_dir, exist_ok=True)
        
        # Generate plot with explicitly enabled trade markers
        chart_path = os.path.join(strategy_dir, "chart.html")
        bt.plot(
            filename=chart_path,
            open_browser=False,
            plot_width=1200,
            plot_equity=True,        # Show equity curve
            plot_return=True,        # Show return curve
            plot_pl=True,            # Show profit/loss for trades
            plot_volume=True,        # Show volume
            plot_drawdown=True,      # Show drawdown
            plot_trades=True,        # Ensure trades are plotted
            smooth_equity=False,     # Don't smooth equity curve
            relative_equity=False,   # Show absolute equity, not relative
            superimpose=False,       # Don't superimpose equity on price
            resample=False,          # Don't resample data
            reverse_indicators=False,# Don't reverse indicator order
            show_legend=True         # Show chart legend
        )
        print(f"{config['name']} Plot saved to: {chart_path}")
        
        # Create a web-accessible path for the chart
        # Use a relative path that will work in the web context
        chart_relative_path = f"../results/{strategy_dir_name}/chart.html"
        chart_paths[config['name']] = chart_relative_path
        
        # Create metadata.json - Updated to use symbol and end_date
        metadata = generate_metadata(
            symbol=args.symbol,
            timeframe=args.timeframe,
            start_date=args.start_date,
            end_date=end_date,
            initial_capital=args.initial_capital,
            commission=args.commission,
            report_type="backtest",
            strategy_name=config['name'],
            directory_name=strategy_dir_name,
            chart_path=f"{strategy_dir_name}/chart.html"
        )
        
        save_metadata(metadata, strategy_dir)
        
        # Always generate individual report for each strategy
        individual_report_path = create_backtest_report(
            {config['name']: stats}, 
            args, 
            strategy_dir, 
            filename="index.html", 
            chart_paths={config['name']: "chart.html"}  # Use local path for individual reports
        )
        print(f"{config['name']} individual report saved to: {individual_report_path}")
    
    # Only print comparison metrics if multiple strategies were run, but don't generate a comparison report
    if len(results) > 1:
        print("\nStrategy Comparison Metrics:")
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
        
        print("\nNote: For a detailed comparison report, use run_comparisons.py instead.")

    # Generate the dashboard and print instructions for viewing it
    from utils.dashboard_generator import generate_dashboard_only
    dashboard_path = generate_dashboard_only()
    print(f"\nDashboard updated at: {dashboard_path}")
    print("To view the dashboard, run: python -m utils.dashboard_generator")
    print("Or access it via: http://localhost:8000/ (if server is already running)")

    return results

if __name__ == "__main__":
    args = parse_args()
    run_backtest(args) 