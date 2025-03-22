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

def create_backtest_report(results, args, results_dir):
    """Create a detailed HTML report for the backtest results using a Jinja2 template"""
    
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
                'Trades': stats['# Trades'],
                'Win Rate [%]': stats['Win Rate [%]'],
                'Avg. Trade [%]': stats['Avg. Trade [%]'],
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
    
    # Set up Jinja2 environment with filters
    env = Environment(loader=FileSystemLoader('templates'))
    
    # Register custom filters
    env.filters['format_number'] = format_number
    env.filters['format_value'] = format_value
    
    # Get template
    template = env.get_template('backtest_report.html')
    
    # Prepare template context
    context = {
        'symbol': args.ticker if hasattr(args, 'ticker') else args.symbol,
        'start_date': args.start_date if hasattr(args, 'start_date') else args.start,
        'end_date': args.end_date if hasattr(args, 'end_date') else args.end,
        'initial_capital': args.initial_capital if hasattr(args, 'initial_capital') else args.cash,
        'commission': args.commission * 100,
        'timeframe': args.timeframe,
        'strategies': list(results_df.columns),
        'metrics': metrics,
        'metric_descriptions': metric_descriptions,
        'results': {strategy: results_df[strategy].to_dict() for strategy in results_df.columns},
        'generation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'get_value_class': get_value_class,
        'format_value': format_value,
        'format_number': format_number
    }
    
    # Render the template
    html_content = template.render(**context)
    
    # Generate filename based on available args
    symbol = args.ticker if hasattr(args, 'ticker') else args.symbol
    start = args.start_date if hasattr(args, 'start_date') else args.start
    end = args.end_date if hasattr(args, 'end_date') else args.end
    
    report_path = os.path.join(results_dir, f"{symbol}_backtest_report_{args.timeframe}_{start}_{end}.html")
    with open(report_path, 'w') as f:
        f.write(html_content)
    
    return report_path 