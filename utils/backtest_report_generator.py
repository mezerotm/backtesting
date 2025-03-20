import os
from datetime import datetime
import pandas as pd

def create_backtest_report(results, args, results_dir):
    """Create a detailed HTML report for the backtest results"""
    
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
    
    html_content = f"""
    <html>
    <head>
        <title>Backtest Results - {args.ticker if hasattr(args, 'ticker') else args.symbol}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            .header {{ background-color: #4CAF50; color: white; padding: 20px; }}
            .section {{ margin: 20px 0; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Backtest Results for {args.ticker if hasattr(args, 'ticker') else args.symbol}</h1>
            <p>Period: {args.start_date if hasattr(args, 'start_date') else args.start} to {args.end_date if hasattr(args, 'end_date') else args.end}</p>
        </div>
        
        <div class="section">
            <h2>Test Parameters</h2>
            <table>
                <tr><th>Parameter</th><th>Value</th></tr>
                <tr><td>Initial Capital</td><td>${args.initial_capital if hasattr(args, 'initial_capital') else args.cash:,.2f}</td></tr>
                <tr><td>Commission</td><td>{args.commission*100}%</td></tr>
                <tr><td>Timeframe</td><td>{args.timeframe}</td></tr>
            </table>
        </div>
        
        <div class="section">
            <h2>Strategy Results</h2>
            <table>
                <tr>
                    <th>Metric</th>
                    {"".join(f"<th>{strategy}</th>" for strategy in results_df.columns)}
                </tr>
    """
    
    # Define the metrics we want to display and their mappings
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
    
    # Add rows for each metric
    for metric in metrics:
        try:
            if metric in results_df.index:
                row_cells = []
                for strategy in results_df.columns:
                    value = results_df.loc[metric, strategy]
                    if pd.isna(value):
                        formatted_value = "N/A"
                    elif isinstance(value, (int, float)):
                        formatted_value = f"{value:.2f}"
                    else:
                        formatted_value = str(value)
                    row_cells.append(f"<td>{formatted_value}</td>")
                
                html_content += f"""
                    <tr>
                        <td>{metric}</td>
                        {"".join(row_cells)}
                    </tr>"""
            else:
                print(f"Warning: Metric '{metric}' not found in results")
                html_content += f"""
                    <tr>
                        <td>{metric}</td>
                        {"".join("<td>N/A</td>" for _ in results_df.columns)}
                    </tr>"""
        except Exception as e:
            print(f"Warning: Error processing metric '{metric}': {str(e)}")
            continue
    
    html_content += """
            </table>
        </div>
    </body>
    </html>
    """
    
    # Generate filename based on available args
    symbol = args.ticker if hasattr(args, 'ticker') else args.symbol
    start = args.start_date if hasattr(args, 'start_date') else args.start
    end = args.end_date if hasattr(args, 'end_date') else args.end
    
    report_path = os.path.join(results_dir, f"{symbol}_backtest_report_{args.timeframe}_{start}_{end}.html")
    with open(report_path, 'w') as f:
        f.write(html_content)
    
    return report_path 