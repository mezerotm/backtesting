#!/usr/bin/env python
"""
Create a consolidated HTML report from multiple strategy comparison CSV files.
"""
import os
import glob
import pandas as pd
import argparse
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Create a consolidated report from CSV results.')
    parser.add_argument('--dir', type=str, default='results',
                        help='Directory containing CSV result files')
    parser.add_argument('--output', type=str, default='strategy_report.html',
                        help='Output HTML file name')
    return parser.parse_args()

def read_all_results(results_dir):
    """Read all CSV files in the results directory and combine them."""
    results = {}
    
    # Get all CSV files
    csv_files = glob.glob(os.path.join(results_dir, '*.csv'))
    
    for csv_file in csv_files:
        # Get the file name without extension as a key
        file_key = os.path.splitext(os.path.basename(csv_file))[0]
        
        # Read the CSV file
        df = pd.read_csv(csv_file)
        
        # Store in results dictionary
        results[file_key] = df
    
    return results

def create_comparison_table(results):
    """Create a table comparing the best strategy for each scenario."""
    comparison = []
    
    for scenario, df in results.items():
        # Find the best strategy based on Return [%]
        best_return_idx = df['Return [%]'].idxmax()
        best_return_strategy = df.loc[best_return_idx, 'Strategy']
        best_return_value = df.loc[best_return_idx, 'Return [%]']
        
        # Find the best strategy based on Sharpe Ratio
        best_sharpe_idx = df['Sharpe Ratio'].idxmax()
        best_sharpe_strategy = df.loc[best_sharpe_idx, 'Strategy']
        best_sharpe_value = df.loc[best_sharpe_idx, 'Sharpe Ratio']
        
        # Find the best strategy based on Win Rate [%]
        best_winrate_idx = df['Win Rate [%]'].idxmax()
        best_winrate_strategy = df.loc[best_winrate_idx, 'Strategy']
        best_winrate_value = df.loc[best_winrate_idx, 'Win Rate [%]']
        
        # Store in comparison list
        comparison.append({
            'Scenario': scenario,
            'Best Return Strategy': best_return_strategy,
            'Best Return [%]': best_return_value,
            'Best Sharpe Strategy': best_sharpe_strategy,
            'Best Sharpe Ratio': best_sharpe_value,
            'Best Win Rate Strategy': best_winrate_strategy,
            'Best Win Rate [%]': best_winrate_value
        })
    
    return pd.DataFrame(comparison)

def create_strategy_ranking(results):
    """Create a ranking of strategies across all scenarios."""
    # Combine all dataframes
    all_results = []
    
    for scenario, df in results.items():
        # Add scenario column
        df_copy = df.copy()
        df_copy['Scenario'] = scenario
        all_results.append(df_copy)
    
    combined_df = pd.concat(all_results, ignore_index=True)
    
    # Get average metrics for each strategy
    strategy_ranking = combined_df.groupby('Strategy').agg({
        'Return [%]': 'mean',
        'Max. Drawdown [%]': 'mean',
        'Sharpe Ratio': 'mean',
        'Sortino Ratio': 'mean',
        'Win Rate [%]': 'mean',
        'Trades': 'mean'
    }).reset_index()
    
    # Rank strategies by Sharpe Ratio
    strategy_ranking = strategy_ranking.sort_values('Sharpe Ratio', ascending=False)
    
    return strategy_ranking

def plot_strategy_performance(strategy_ranking):
    """Create plots for strategy performance comparison."""
    # Set up the style
    sns.set(style="whitegrid")
    
    # Create a figure with multiple subplots
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    
    # Plot Return [%]
    sns.barplot(x='Strategy', y='Return [%]', data=strategy_ranking, ax=axes[0, 0])
    axes[0, 0].set_title('Average Return [%]')
    axes[0, 0].set_xticklabels(axes[0, 0].get_xticklabels(), rotation=45, ha='right')
    
    # Plot Sharpe Ratio
    sns.barplot(x='Strategy', y='Sharpe Ratio', data=strategy_ranking, ax=axes[0, 1])
    axes[0, 1].set_title('Average Sharpe Ratio')
    axes[0, 1].set_xticklabels(axes[0, 1].get_xticklabels(), rotation=45, ha='right')
    
    # Plot Win Rate [%]
    sns.barplot(x='Strategy', y='Win Rate [%]', data=strategy_ranking, ax=axes[1, 0])
    axes[1, 0].set_title('Average Win Rate [%]')
    axes[1, 0].set_xticklabels(axes[1, 0].get_xticklabels(), rotation=45, ha='right')
    
    # Plot Max Drawdown [%] (negative values)
    sns.barplot(x='Strategy', y='Max. Drawdown [%]', data=strategy_ranking, ax=axes[1, 1])
    axes[1, 1].set_title('Average Max Drawdown [%]')
    axes[1, 1].set_xticklabels(axes[1, 1].get_xticklabels(), rotation=45, ha='right')
    
    plt.tight_layout()
    
    # Save the figure
    plt.savefig('strategy_performance.png')
    return 'strategy_performance.png'

def create_html_report(results, comparison_table, strategy_ranking, performance_plot, output_file):
    """Create an HTML report from the results."""
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Trading Strategy Comparison Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1, h2, h3 {{ color: #2c3e50; }}
            table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f5f5f5; }}
            tr:nth-child(even) {{ background-color: #f9f9f9; }}
            .metric-positive {{ color: green; }}
            .metric-negative {{ color: red; }}
            .container {{ margin-bottom: 30px; }}
            img {{ max-width: 100%; height: auto; }}
        </style>
    </head>
    <body>
        <h1>Trading Strategy Comparison Report</h1>
        <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <div class="container">
            <h2>Strategy Ranking Across All Scenarios</h2>
            <p>Strategies ranked by average Sharpe Ratio</p>
            {strategy_ranking.to_html(index=False, classes='table', float_format='%.2f')}
        </div>
        
        <div class="container">
            <h2>Strategy Performance Visualization</h2>
            <img src="{performance_plot}" alt="Strategy Performance">
        </div>
        
        <div class="container">
            <h2>Best Strategies by Scenario</h2>
            {comparison_table.to_html(index=False, classes='table', float_format='%.2f')}
        </div>
        
        <div class="container">
            <h2>Detailed Results by Scenario</h2>
    """
    
    # Add each scenario's results
    for scenario, df in results.items():
        html += f"""
            <h3>{scenario}</h3>
            {df.to_html(index=False, classes='table', float_format='%.2f')}
            <br>
        """
    
    html += """
        </div>
    </body>
    </html>
    """
    
    # Write the HTML to file
    with open(output_file, 'w') as f:
        f.write(html)
    
    print(f"Report generated: {output_file}")

def main():
    """Main function to create the report."""
    args = parse_args()
    
    # Read all CSV results
    results = read_all_results(args.dir)
    
    if not results:
        print(f"No CSV files found in {args.dir}")
        return
    
    # Create comparison table
    comparison_table = create_comparison_table(results)
    
    # Create strategy ranking
    strategy_ranking = create_strategy_ranking(results)
    
    # Create performance plot
    performance_plot = plot_strategy_performance(strategy_ranking)
    
    # Create HTML report
    create_html_report(results, comparison_table, strategy_ranking, performance_plot, args.output)

if __name__ == "__main__":
    main() 