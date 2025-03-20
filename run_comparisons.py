import argparse
import pandas as pd
from datetime import datetime, timedelta
from utils.compare_strategies import compare_strategies, plot_strategy_comparison
from strategies.moving_average import SimpleMovingAverageCrossover, ExponentialMovingAverageCrossover
from strategies.advanced_strategy import MACDRSIStrategy, BollingerRSIStrategy
from utils.data_fetcher import fetch_historical_data
import os

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Run strategy comparisons.')
    
    # Data options
    parser.add_argument('--symbol', type=str, default='SPY',
                        help='Stock symbol to use (default: SPY)')
    parser.add_argument('--start', type=str, default='2018-01-01',
                        help='Start date for data (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, default=None,
                        help='End date for data (YYYY-MM-DD, default: today)')
    parser.add_argument('--timeframe', type=str, default='1d',
                        help='Data timeframe: e.g., 5m, 1h, 1d (default: 1d)')
    
    # Backtest options
    parser.add_argument('--cash', type=float, default=10000,
                        help='Initial cash for backtesting (default: 10000)')
    parser.add_argument('--commission', type=float, default=0.002,
                        help='Commission rate for trades (default: 0.002)')
    
    # Strategy selection
    parser.add_argument('--strategies', type=str, nargs='+', 
                        choices=['SMA', 'EMA', 'MACD', 'BB', 'ALL'],
                        default=['ALL'],
                        help='Strategies to compare (default: ALL)')
    
    # Output options
    parser.add_argument('--csv', type=str, default=None,
                        help='Export results to CSV file')
    parser.add_argument('--no-plots', action='store_true',
                        help='Disable generation of plots')
    
    return parser.parse_args()

def get_strategies(strategy_names):
    """Get the strategy classes based on names."""
    all_strategies = {
        'SMA': SimpleMovingAverageCrossover,
        'EMA': ExponentialMovingAverageCrossover,
        'MACD': MACDRSIStrategy,
        'BB': BollingerRSIStrategy
    }
    
    if 'ALL' in strategy_names:
        return {
            'SMA Crossover': SimpleMovingAverageCrossover,
            'EMA Crossover': ExponentialMovingAverageCrossover,
            'MACD-RSI-EMA': MACDRSIStrategy,
            'Bollinger-RSI': BollingerRSIStrategy
        }
    
    # Only include selected strategies
    selected = {}
    for name in strategy_names:
        if name == 'SMA':
            selected['SMA Crossover'] = all_strategies['SMA']
        elif name == 'EMA':
            selected['EMA Crossover'] = all_strategies['EMA']
        elif name == 'MACD':
            selected['MACD-RSI-EMA'] = all_strategies['MACD']
        elif name == 'BB':
            selected['Bollinger-RSI'] = all_strategies['BB']
    
    return selected

def prepare_data_for_backtesting(data):
    """Prepare data for backtesting by ensuring it has the correct column structure."""
    # Check if data is already in the right format
    required_columns = {'Open', 'High', 'Low', 'Close', 'Volume'}
    
    # Data from Polygon API via our data_fetcher should already have correct column names,
    # but we'll keep the validation checks to be safe
    
    # Ensure all required columns exist with the right capitalization
    if not set(data.columns).issuperset(required_columns):
        # Try to standardize column names (handle different capitalizations)
        column_map = {}
        for col in data.columns:
            std_col = col.title()  # Capitalize first letter
            if std_col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                column_map[col] = std_col
        
        # Rename columns if needed
        if column_map:
            data = data.rename(columns=column_map)
    
    # Verify required columns now exist
    missing_cols = required_columns - set(data.columns)
    if missing_cols:
        raise ValueError(f"Data is missing required columns: {', '.join(missing_cols)}")
    
    return data

def main():
    """Main function to run comparisons."""
    args = parse_args()
    
    # Set end date to today if not specified
    if args.end is None:
        end_date = datetime.today().strftime('%Y-%m-%d')
    else:
        end_date = args.end
    
    print(f"Fetching data for {args.symbol} from {args.start} to {end_date} using Polygon API (timeframe: {args.timeframe})...")
    raw_data = fetch_historical_data(
        ticker=args.symbol, 
        start_date=args.start, 
        end_date=end_date, 
        timeframe=args.timeframe
    )
    
    if len(raw_data) == 0:
        print(f"No data found for {args.symbol}. Please check the symbol and date range.")
        return
    
    print(f"Fetched {len(raw_data)} bars of data.")
    
    # Prepare data for backtesting
    try:
        data = prepare_data_for_backtesting(raw_data)
        print("Data prepared successfully for backtesting.")
    except ValueError as e:
        print(f"Error preparing data: {e}")
        return
    
    strategies = get_strategies(args.strategies)
    print(f"Comparing {len(strategies)} strategies: {', '.join(strategies.keys())}")
    
    results = compare_strategies(
        data=data,
        strategies=strategies,
        cash=args.cash,
        commission=args.commission
    )
    
    # Debug print
    print("\nRaw results:")
    print(results)
    print("\nResults info:")
    print(results.info())
    print("\nResults columns:", results.columns.tolist())
    print("Results index:", results.index.tolist())
    
    # Ensure results are in the correct format
    if not isinstance(results, pd.DataFrame):
        results = pd.DataFrame(results)
    
    # Make sure the metrics are in the index (transpose if needed)
    if 'Return [%]' in results.columns:
        results = results.transpose()
    
    # Debug print after transformation
    print("\nTransformed results:")
    print(results)
    print("\nTransformed results info:")
    print(results.info())
    
    # Print debug information
    print("\nResults DataFrame structure:")
    print("Shape:", results.shape)
    print("Index:", results.index.tolist())
    print("Columns:", results.columns.tolist())
    print("\nStrategy Comparison Results:")
    print(results)
    
    # Create results directory if it doesn't exist
    results_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')
    os.makedirs(results_dir, exist_ok=True)
    
    # Generate and open HTML report
    from utils.backtest_report_generator import create_backtest_report
    report_path = create_backtest_report(results, args, results_dir)
    print(f"\nDetailed HTML report saved to: {report_path}")
    
    # Export to CSV if requested
    if args.csv:
        results.to_csv(args.csv)
        print(f"Results exported to {args.csv}")
    
    # Plot comparison only if not disabled
    if not args.no_plots:
        plot_strategy_comparison(results)
    
    return results

if __name__ == "__main__":
    main()