"""
Backtest Strategy Workflow CLI

This CLI orchestrates the backtest strategy workflow which:
1. Executes individual trading strategies on historical data
2. Analyzes strategy performance with AI-powered insights
3. Generates detailed backtest reports with visualizations
4. Integrates with the central dashboard

The workflow is designed to provide comprehensive strategy testing through:
- workflows/backtest/backtest_data.py: Historical data fetching
- workflows/backtest/backtest_report_generator.py: Report generation
- workflows/backtest/strategy_utils.py: Strategy utilities and indicators
- workflows/backtest/ai_explanations.py: AI-powered analysis
- workflows/backtest/backtest_report.html: Report template

Usage:
    python backtest_workflow_cli.py --symbol AAPL --strategy sma [--initial-capital 10000]
"""

import os
import pandas as pd
from backtesting import Backtest
import sys
import argparse
from datetime import datetime, date, timedelta

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from workflows.market.data_fetchers.backtest_data import BacktestDataFetcher
from strategies.moving_average import SimpleMovingAverageCrossover, ExponentialMovingAverageCrossover
from strategies.advanced_strategy import MACDRSIStrategy, BollingerRSIStrategy
from utils import config
from workflows.metadata_generator import generate_metadata, save_metadata
from strategies.experimental_strategy import CombinedStrategy
from strategies.buy_hold import BuyAndHoldStrategy
from workflows.backtest.backtest_report_generator import create_backtest_report

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
                      choices=['sma', 'ema', 'macd_rsi', 'bb_rsi', 'experimental', 'buy_hold', 'all'],
                      help='Strategies to run (sma, ema, macd_rsi, bb_rsi, experimental, buy_hold, or all)')
    
    # Add flag for generating individual reports
    parser.add_argument('--generate-individual-reports', action='store_true',
                      help='Generate individual reports for each strategy in addition to comparison')
    
    # Required parameters - Changed ticker to symbol
    parser.add_argument('--symbol', type=str, required=True,
                      help='Stock symbol (e.g., AAPL)')
    
    # Add force-refresh argument
    parser.add_argument('--force-refresh', action='store_true', default=False,
                      help='Force refresh of data (bypass cache)')
    
    # Update date arguments with better defaults and validation
    one_year_ago = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    today = datetime.now().strftime("%Y-%m-%d")
    
    parser.add_argument('--start-date', type=valid_date, default=one_year_ago,
                      help='Start date (YYYY-MM-DD), defaults to 1 year ago')
    parser.add_argument('--end-date', type=valid_date, default=today,
                      help='End date (YYYY-MM-DD), defaults to today')
    
    # Optional parameters with defaults - Align with backtest_comparisons.py
    parser.add_argument('--timeframe', type=str, default="1d",
                      choices=['1m', '5m', '15m', '30m', '1h', '1d'],
                      help='Trading timeframe')
    parser.add_argument('--initial-capital', type=float, default=10000,
                      help='Initial capital for backtesting')
    parser.add_argument('--commission', type=float, default=0.001,
                      help='Commission rate (e.g., 0.001 for 0.1%)')
    
    # Optimization flag
    parser.add_argument('--optimize', action='store_true',
                      help='Run parameter optimization')
    
    args = parser.parse_args()
    
    # Validate date range
    start = datetime.strptime(args.start_date, "%Y-%m-%d")
    end = datetime.strptime(args.end_date, "%Y-%m-%d")
    today = datetime.now()
    
    if start > end:
        parser.error("Start date must be before end date")
    if end > today:
        parser.error("End date cannot be in the future")
    if start > today:
        parser.error("Start date cannot be in the future")
        
    return args

def run_backtest(args):
    # Create public/results directory if it doesn't exist
    script_dir = os.path.dirname(os.path.abspath(__file__))
    public_dir = os.path.join(script_dir, 'public')
    results_base_dir = os.path.join(public_dir, 'results')
    os.makedirs(results_base_dir, exist_ok=True)
    
    # Create data fetcher
    data_fetcher = BacktestDataFetcher(force_refresh=args.force_refresh)
    
    # Fetch historical data
    print(f"Fetching data for {args.symbol} from {args.start_date} to {args.end_date}...")
    df = data_fetcher.fetch_historical_data(
        symbol=args.symbol,
        start_date=args.start_date,
        end_date=args.end_date
    )
    
    if df.empty:
        raise ValueError(f"No data available for {args.symbol}")
    
    # Determine which strategies to run
    strategies_to_run = []
    if 'all' in args.strategies:
        strategies_to_run = ['sma', 'ema', 'macd_rsi', 'bb_rsi', 'experimental', 'buy_hold']
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
    
    # Dictionary to store results and chart paths
    results = {}
    chart_paths = {}
    
    # Strategy configurations
    strategy_configs = {
        'sma': {
            'name': 'SMA',
            'class': SimpleMovingAverageCrossover,
            'setup': lambda: None  # No setup needed, using default parameters
        },
        'ema': {
            'name': 'EMA',
            'class': ExponentialMovingAverageCrossover,
            'setup': lambda: None  # No setup needed, using default parameters
        },
        'macd_rsi': {
            'name': 'MACD+RSI',
            'class': MACDRSIStrategy,
            'setup': lambda: None  # No setup needed, using default parameters
        },
        'bb_rsi': {
            'name': 'BB+RSI',
            'class': BollingerRSIStrategy,
            'setup': lambda: None  # No setup needed, using default parameters
        },
        'experimental': {
            'name': 'Experimental',
            'class': CombinedStrategy,
            'setup': lambda: None  # No setup needed, using default parameters
        },
        'buy_hold': {
            'name': 'Buy & Hold',
            'class': BuyAndHoldStrategy,
            'setup': lambda: None  # No setup needed, using default parameters
        }
    }
    
    # Run selected strategies
    for strategy_id in strategies_to_run:
        strategy_config = strategy_configs[strategy_id]  # Rename to avoid confusion with the config module
        print(f"\nRunning {strategy_config['name']} Strategy...")
        
        # Run backtest
        bt = Backtest(
            data=df,
            strategy=strategy_config['class'],
            cash=args.initial_capital,
            commission=args.commission
        )
        
        stats = bt.run()  # Run once and store stats
        results[strategy_config['name']] = stats
        
        # Create a directory for this strategy's results - Updated to use symbol
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        strategy_dir_name = f"{args.symbol}_{strategy_config['name']}_{args.timeframe}_{timestamp}"
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
        print(f"{strategy_config['name']} Plot saved to: {chart_path}")
        
        # Create a web-accessible path for the chart
        # Use a relative path that will work in the web context
        chart_relative_path = f"../results/{strategy_dir_name}/chart.html"
        chart_paths[strategy_config['name']] = chart_relative_path
        
        # Create metadata.json - Updated to use symbol and end_date
        metadata = generate_metadata(
            symbol=args.symbol,
            timeframe=args.timeframe,
            start_date=args.start_date,
            end_date=end_date,  # This is already formatted as YYYY-MM-DD
            initial_capital=args.initial_capital,
            commission=args.commission,
            report_type="backtest",
            strategy_name=strategy_config['name'],
            directory_name=strategy_dir_name,
            chart_path=f"{strategy_dir_name}/chart.html",
            additional_data={
                "status": "finished",
                "date_range": f"{args.start_date} to {end_date}",  # Add explicit date range
                "title": f"{args.symbol} {strategy_config['name']} Backtest"
            }
        )
        
        save_metadata(metadata, strategy_dir)
        
        # Check environment directly instead of using ENABLE_AI_EXPLANATIONS
        disable_ai = config.ENV != 'production'
        
        # Always generate individual report for each strategy
        individual_report_path = create_backtest_report(
            {strategy_config['name']: stats}, 
            args, 
            strategy_dir, 
            filename="index.html", 
            chart_paths={strategy_config['name']: "chart.html"},
            disable_ai_explanations=disable_ai  # Disable AI explanations when not in production
        )
        print(f"{strategy_config['name']} individual report saved to: {individual_report_path}")
    
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

    return results

if __name__ == "__main__":
    args = parse_args()
    run_backtest(args) 