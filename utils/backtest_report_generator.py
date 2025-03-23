import os
from datetime import datetime
import pandas as pd
from jinja2 import Environment, FileSystemLoader
import math

def format_number(value):
    """Format a number with commas as thousands separators"""
    if isinstance(value, (int, float)):
        return f"{value:,.2f}"
    return value

def format_value(value):
    """Format a value for display in the report"""
    if pd.isna(value) or value is None or (isinstance(value, float) and math.isnan(value)):
        return "N/A"
    elif isinstance(value, (int, float)):
        return f"{value:.2f}"
    return str(value)

def get_value_class(metric, value):
    """Determine the CSS class for a value based on the metric and value"""
    if pd.isna(value) or value is None or (isinstance(value, float) and math.isnan(value)):
        return "neutral"
    
    if "Return" in metric and not "Drawdown" in metric:
        return "positive" if value > 0 else "negative"
    elif "Drawdown" in metric:
        return "negative"
    elif "Ratio" in metric or "SQN" in metric:
        return "neutral"
    elif "Win Rate" in metric:
        return "positive" if value > 50 else "neutral"
    
    return "neutral"

def create_backtest_report(results, args, output_dir, filename="index.html", chart_paths=None):
    """Create a detailed HTML report for the backtest results.
    
    Args:
        results: Dictionary of backtest results or DataFrame
        args: Command line arguments
        output_dir: Directory to save the report
        filename: Name of the report file
        chart_paths: Dictionary mapping strategy names to chart paths or single chart path for one strategy
    """
    
    # Remove debug logging for production
    # print(f"Chart paths provided to report generator: {chart_paths}")
    
    # Convert dictionary of stats objects to DataFrame if needed
    if isinstance(results, dict) and not isinstance(results, pd.DataFrame):
        # Extract key metrics from each strategy's stats object
        metrics_data = {}
        for name, stats in results.items():
            metrics_data[name] = {
                'Return [%]': stats['Return [%]'],
                'Buy & Hold Return [%]': stats['Buy & Hold Return [%]'],
                'Max. Drawdown [%]': stats['Max. Drawdown [%]'],
                'Sharpe Ratio': stats['Sharpe Ratio'],
                'Sortino Ratio': stats['Sortino Ratio'],
                'Calmar Ratio': stats['Calmar Ratio'],
                'Trades': stats.get('# Trades', 0),  # Use get with default for safety
                'Win Rate [%]': stats.get('Win Rate [%]', 0.0),
                'Avg. Trade [%]': stats.get('Avg. Trade [%]', 0.0),
                'SQN': stats.get('SQN', float('nan'))  # Some versions might not have SQN
            }
        
        # Create DataFrame with metrics as rows and strategies as columns
        results_df = pd.DataFrame(metrics_data)
    else:
        # Results is already a DataFrame
        results_df = results
    
    # Define the metrics we want to display
    metrics = [
        'Return [%]',
        'Buy & Hold Return [%]',
        'Max. Drawdown [%]',
        'Sharpe Ratio',
        'Sortino Ratio',
        'Calmar Ratio',
        'Trades',
        'Win Rate [%]',
        'Avg. Trade [%]',
        'SQN'
    ]
    
    # Define metric descriptions for tooltips
    metric_descriptions = {
        'Return [%]': 'The total percentage return of the strategy over the backtest period.',
        'Buy & Hold Return [%]': 'The percentage return from buying and holding the asset for the entire backtest period.',
        'Max. Drawdown [%]': 'The maximum observed loss from a peak to a trough during the backtest period.',
        'Sharpe Ratio': 'A measure of risk-adjusted return. Higher values indicate better risk-adjusted performance.',
        'Sortino Ratio': 'Similar to Sharpe but only considers downside volatility. Higher values are better.',
        'Calmar Ratio': 'A measure of return relative to drawdown risk. Higher values are better.',
        'Trades': 'The total number of completed trades executed during the backtest period.',
        'Win Rate [%]': 'The percentage of trades that resulted in a profit.',
        'Avg. Trade [%]': 'The average percentage profit or loss per trade.',
        'SQN': 'System Quality Number - rates trading systems based on consistency and size of profits relative to risk.'
    }
    
    # Get the templates directory relative to this file
    templates_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'templates')
    env = Environment(loader=FileSystemLoader(templates_dir))
    
    # Register the format_number function as a filter
    env.filters['format_number'] = format_number
    env.filters['format_value'] = format_value
    
    # Load the template
    template = env.get_template('backtest_report.html')
    
    # Handle chart paths based on whether it's a single strategy or comparison
    if chart_paths is None:
        chart_paths = {}
    elif not isinstance(chart_paths, dict):
        # Single chart path as string
        if len(results_df.columns) == 1:
            chart_paths = {results_df.columns[0]: chart_paths}
        else:
            chart_paths = {'comparison': chart_paths}
    
    # Check if we have any valid chart paths
    has_charts = bool(chart_paths) and any(chart_paths.values())
    
    # Get symbol from args, handling both ticker and symbol naming
    symbol = args.symbol if hasattr(args, 'symbol') else args.ticker if hasattr(args, 'ticker') else "Unknown"
    
    # Get start_date from args, handling both start_date and start naming
    start_date = args.start_date if hasattr(args, 'start_date') else args.start if hasattr(args, 'start') else "Unknown"
    
    # Get end_date from args, handling both end_date and end naming
    end_date = args.end_date if hasattr(args, 'end_date') else args.end if hasattr(args, 'end') else "Unknown"
    
    # Get initial_capital from args, handling both initial_capital and cash naming
    initial_capital = args.initial_capital if hasattr(args, 'initial_capital') else args.cash if hasattr(args, 'cash') else 10000
    
    # Render the template with our data
    report_html = template.render(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital,
        commission=args.commission,
        timeframe=args.timeframe,
        strategies=list(results_df.columns),
        metrics=metrics,
        results={strategy: results_df[strategy].to_dict() for strategy in results_df.columns},
        metric_descriptions=metric_descriptions,
        format_value=format_value,
        get_value_class=get_value_class,
        generation_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        chart_paths=chart_paths,
        has_charts=has_charts,
        is_comparison=(len(results_df.columns) > 1)
    )
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Save the report to the specified file in the output directory
    report_path = os.path.join(output_dir, filename)
    with open(report_path, 'w') as f:
        f.write(report_html)
    
    return report_path 