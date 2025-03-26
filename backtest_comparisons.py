import argparse
import pandas as pd
from datetime import datetime, timedelta
from utils.compare_strategies import compare_strategies, plot_strategy_comparison
from strategies.moving_average import SimpleMovingAverageCrossover, ExponentialMovingAverageCrossover
from strategies.advanced_strategy import MACDRSIStrategy, BollingerRSIStrategy
from utils.data_fetcher import fetch_historical_data
import os
from utils.strategy_comparison_report import read_all_results, create_comparison_table, create_strategy_ranking, plot_strategy_performance, create_html_report
from utils.dashboard_generator import generate_dashboard_only
from utils.metadata_generator import generate_metadata, save_metadata

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Run strategy comparisons.')
    
    # Data options - Keeping symbol as is since it's already using the right term
    parser.add_argument('--symbol', type=str, required=True, help='Symbol to backtest')
    
    # Change default start date to 10 years ago
    ten_years_ago = (datetime.now() - timedelta(days=365*10)).strftime("%Y-%m-%d")
    parser.add_argument('--start-date', type=str, default=ten_years_ago,
                        help='Start date for data (default: 10 years ago)')
    parser.add_argument('--end-date', type=str, default=None,
                        help='End date for data (YYYY-MM-DD, default: today)')
    parser.add_argument('--timeframe', type=str, default='1d',
                        help='Data timeframe: e.g., 5m, 1h, 1d (default: 1d)')
    
    # Backtest options - Already using initial-capital
    parser.add_argument('--initial-capital', type=float, default=10000,
                        help='Initial capital for backtesting (default: 10000)')
    parser.add_argument('--commission', type=float, default=0.001,
                      help='Commission rate (e.g., 0.001 for 0.1%)')
    
    # Strategy selection
    parser.add_argument('--strategies', type=str, nargs='+', 
                        choices=['sma', 'ema', 'macd', 'bb', 'buy_hold', 'experimental', 'all'],
                        default=['all'],
                        help='Strategies to compare (default: all)')
    
    # Output options
    parser.add_argument('--no-plots', action='store_true',
                        help='Disable generation of plots')
    
    # Debug option
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    
    return parser.parse_args()

def get_strategies(strategy_names):
    """Get the strategy classes based on names."""
    from strategies.buy_hold import BuyAndHoldStrategy
    from strategies.experimental_strategy import CombinedStrategy
    
    all_strategies = {
        'sma': SimpleMovingAverageCrossover,
        'ema': ExponentialMovingAverageCrossover,
        'macd': MACDRSIStrategy,
        'bb': BollingerRSIStrategy,
        'buy_hold': BuyAndHoldStrategy,
        'experimental': CombinedStrategy
    }
    
    if 'all' in [s.lower() for s in strategy_names]:
        return {
            'sma crossover': SimpleMovingAverageCrossover,
            'ema crossover': ExponentialMovingAverageCrossover,
            'macd-rsi-ema': MACDRSIStrategy,
            'bollinger-rsi': BollingerRSIStrategy,
            'buy & hold': BuyAndHoldStrategy,
            'experimental': CombinedStrategy
        }
    
    # Only include selected strategies
    selected = {}
    for name in strategy_names:
        name_lower = name.lower()
        if name_lower == 'sma':
            selected['sma crossover'] = all_strategies['sma']
        elif name_lower == 'ema':
            selected['ema crossover'] = all_strategies['ema']
        elif name_lower == 'macd':
            selected['macd-rsi-ema'] = all_strategies['macd']
        elif name_lower == 'bb':
            selected['bollinger-rsi'] = all_strategies['bb']
        elif name_lower == 'buy_hold':
            selected['buy & hold'] = all_strategies['buy_hold']
        elif name_lower == 'experimental':
            selected['experimental'] = all_strategies['experimental']
    
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
    if args.end_date is None:
        end_date = datetime.today().strftime('%Y-%m-%d')
    else:
        end_date = args.end_date
    
    print(f"Fetching data for {args.symbol} from {args.start_date} to {end_date} using Polygon API (timeframe: {args.timeframe})...")
    raw_data = fetch_historical_data(
        ticker=args.symbol,  # Using symbol but keeping ticker parameter name for compatibility
        start_date=args.start_date, 
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
        cash=args.initial_capital,  # Already using initial_capital
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
    
    # Create public/results directory if it doesn't exist
    script_dir = os.path.dirname(os.path.abspath(__file__))
    public_dir = os.path.join(script_dir, 'public')
    results_dir = os.path.join(public_dir, 'results')
    os.makedirs(results_dir, exist_ok=True)
    
    # Create a dedicated directory for this comparison
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    comparison_dir_name = f"{args.symbol}_strategy_comparison_{args.timeframe}_{timestamp}"
    comparison_dir = os.path.join(results_dir, comparison_dir_name)
    os.makedirs(comparison_dir, exist_ok=True)

    # Create initial metadata.json with status "unfinished"
    metadata = generate_metadata(
        symbol=args.symbol,
        timeframe=args.timeframe,
        start_date=args.start_date,
        end_date=end_date,
        initial_capital=args.initial_capital,
        commission=args.commission,
        report_type="comparison",
        strategies_compared=list(strategies.keys()),
        directory_name=comparison_dir_name,
        additional_data={"status": "unfinished"}  # Set initial status to unfinished
    )

    save_metadata(metadata, comparison_dir)

    # Add debug output
    if args.debug:
        print(f"Strategies to compare: {strategies}")
        print(f"Results keys: {list(results.keys())}")
        for strategy in strategies:
            if strategy in results:
                print(f"Keys in results[{strategy}]: {list(results[strategy].keys())}")
            else:
                print(f"Warning: Strategy '{strategy}' not found in results")

    # Generate and open HTML report for this specific backtest
    from utils.backtest_report_generator import create_backtest_report
    # Disable AI explanations for comparison reports
    report_path = create_backtest_report(
        results, 
        args, 
        comparison_dir, 
        filename="index.html",
        disable_ai_explanations=True  # Add this parameter to disable AI explanations
    )
    print(f"\nDetailed HTML report saved to: {report_path}")

    # Update metadata status to "finished" after report generation is complete
    metadata["status"] = "finished"
    save_metadata(metadata, comparison_dir)

    # Generate consolidated strategy comparison report
    all_results = read_all_results(results_dir)
    
    if all_results:
        # Create comparison table
        comparison_table = create_comparison_table(all_results)
        
        # Create strategy ranking
        strategy_ranking = create_strategy_ranking(all_results)
        
        # Create performance plot
        performance_plot = plot_strategy_performance(strategy_ranking)
        
        # Create consolidated HTML report
        consolidated_report_path = os.path.join(results_dir, "strategy_comparison_report.html")
        create_html_report(all_results, comparison_table, strategy_ranking, performance_plot, consolidated_report_path)
        print(f"\nConsolidated strategy comparison report saved to: {consolidated_report_path}")
        
        # Generate and open the dashboard (only this should open the browser)
        dashboard_path = generate_dashboard_only()
        print(f"\nDashboard updated at: {dashboard_path}")
        print("To view the dashboard, run: python -m utils.dashboard_generator")
        print("Or access it via: http://localhost:8000/dashboard.html (if server is already running)")
    
    # Plot comparison only if not disabled
    if not args.no_plots:
        import matplotlib
        # Set the backend to a file-based one if we're in a non-interactive environment
        if os.environ.get('DISPLAY', '') == '' and not os.name == 'nt':
            matplotlib.use('Agg')  # Use non-interactive backend if no display available
            # Save the plot to a file instead of showing it
            fig = plot_strategy_comparison(results, show_plot=False)
            if fig:
                plot_path = os.path.join(results_dir, f"{args.symbol}_strategy_comparison.png")
                fig.savefig(plot_path)
                print(f"Strategy comparison plot saved to: {plot_path}")
        else:
            # We're in an environment with display capability
            plot_strategy_comparison(results)
    
    return results

if __name__ == "__main__":
    main()