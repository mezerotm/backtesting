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
    """Plot strategy performance comparison and return the figure."""
    import matplotlib.pyplot as plt
    import matplotlib
    matplotlib.use('Agg')  # Use non-interactive backend
    
    # Check if we have valid data to plot
    if strategy_ranking.empty or strategy_ranking.isnull().all().all():
        print("Warning: No valid data for strategy performance plot")
        return "no_data_available.png"  # Return a placeholder
    
    # Create a figure with a smaller size (reduced from 12x8)
    fig, ax = plt.subplots(figsize=(8, 5))  # Smaller figure size
    
    # Plot each strategy's performance
    strategies = strategy_ranking.index
    returns = strategy_ranking['Return [%]']
    
    # Handle NaN values - replace with zeros for plotting
    returns = returns.fillna(0)
    
    # Create the bar chart
    bars = ax.bar(strategies, returns, color='skyblue')
    
    # Add value labels on top of each bar (with smaller font)
    for bar in bars:
        height = bar.get_height()
        if not pd.isna(height):
            ax.text(
                bar.get_x() + bar.get_width()/2.,
                height + 1,
                f'{height:.2f}%',
                ha='center', va='bottom', fontsize=8  # Smaller font
            )
    
    # Add titles and labels with smaller fonts
    ax.set_title('Strategy Performance Comparison', fontsize=12)
    ax.set_ylabel('Return [%]', fontsize=10)
    ax.set_xlabel('Strategy', fontsize=10)
    
    # Rotate x-axis labels for better readability
    plt.xticks(rotation=45, ha='right', fontsize=9)  # Smaller tick labels
    
    # Add grid lines for easier reading
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    
    # Adjust layout
    plt.tight_layout()
    
    # Save the figure to the results directory with reduced DPI
    import os
    results_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'results')
    os.makedirs(results_dir, exist_ok=True)
    plot_path = os.path.join(results_dir, 'strategy_performance.png')
    relative_path = 'strategy_performance.png'  # Use relative path in HTML
    
    try:
        plt.savefig(plot_path, dpi=80)  # Lower DPI for smaller file size
        print(f"Strategy performance plot saved to: {plot_path}")
        plt.close(fig)  # Close the figure to free memory
        return relative_path  # Return the relative path for the HTML
    except Exception as e:
        print(f"Error saving strategy performance plot: {e}")
        return "error_generating_plot.png"  # Return a placeholder on error

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

def visualize_best_strategies(results, output_path=None):
    """
    Create a visualization showing the best strategies for each scenario.
    
    Parameters:
        results (dict): Dictionary mapping scenario names to DataFrames of results
        output_path (str, optional): Path to save the visualization image
    
    Returns:
        matplotlib.figure.Figure: The generated figure
    """
    import matplotlib
    import matplotlib.pyplot as plt
    import numpy as np
    
    # Set non-interactive backend if saving to file in non-interactive environment
    if output_path and not matplotlib.is_interactive():
        matplotlib.use('Agg')
    
    # Get all unique strategies across scenarios
    all_strategies = set()
    for df in results.values():
        all_strategies.update(df['Strategy'].unique())
    
    # Extract best strategy for each scenario based on Sharpe Ratio
    best_strategies = {}
    for scenario, df in results.items():
        # Find the strategy with the highest Sharpe Ratio
        best_idx = df['Sharpe Ratio'].idxmax()
        best_strategy = df.loc[best_idx, 'Strategy']
        best_sharpe = df.loc[best_idx, 'Sharpe Ratio']
        best_return = df.loc[best_idx, 'Return [%]']
        
        best_strategies[scenario] = {
            'Strategy': best_strategy,
            'Sharpe Ratio': best_sharpe,
            'Return [%]': best_return
        }
    
    # Create a figure with two subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 8))
    
    # Plot best strategies by Sharpe Ratio
    scenarios = list(best_strategies.keys())
    sharpe_values = [best_strategies[s]['Sharpe Ratio'] for s in scenarios]
    colors = plt.cm.viridis(np.linspace(0, 1, len(scenarios)))
    
    bars = ax1.bar(scenarios, sharpe_values, color=colors)
    ax1.set_title('Best Strategy by Sharpe Ratio in Each Scenario')
    ax1.set_ylabel('Sharpe Ratio')
    ax1.set_xticklabels(scenarios, rotation=45, ha='right')
    ax1.grid(True, linestyle='--', alpha=0.7)
    
    # Add strategy names as text labels
    for i, bar in enumerate(bars):
        strategy_name = best_strategies[scenarios[i]]['Strategy']
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                 strategy_name, ha='center', va='bottom', rotation=0,
                 fontsize=8, fontweight='bold')
    
    # Plot best strategies by Return
    return_values = [best_strategies[s]['Return [%]'] for s in scenarios]
    
    bars = ax2.bar(scenarios, return_values, color=colors)
    ax2.set_title('Best Strategy by Return [%] in Each Scenario')
    ax2.set_ylabel('Return [%]')
    ax2.set_xticklabels(scenarios, rotation=45, ha='right')
    ax2.grid(True, linestyle='--', alpha=0.7)
    
    # Add strategy names as text labels
    for i, bar in enumerate(bars):
        strategy_name = best_strategies[scenarios[i]]['Strategy']
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2,
                 strategy_name, ha='center', va='bottom', rotation=0,
                 fontsize=8, fontweight='bold')
    
    plt.tight_layout()
    
    # Save the figure if a path is provided
    if output_path:
        plt.savefig(output_path, dpi=100, bbox_inches='tight')
        print(f"Best strategies visualization saved to {output_path}")
    
    return fig

def create_interactive_scenario_comparison(results, output_path=None):
    """
    Create an interactive Plotly visualization comparing the best strategies across scenarios.
    
    Parameters:
        results (dict): Dictionary mapping scenario names to DataFrames of results
        output_path (str, optional): Path to save the HTML file
    
    Returns:
        plotly.graph_objects.Figure: The Plotly figure object
    """
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    import numpy as np
    
    # Get all unique strategies across scenarios
    all_strategies = set()
    for df in results.values():
        all_strategies.update(df['Strategy'].unique())
    all_strategies = list(all_strategies)
    
    # Create a subplot figure
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=["Strategy Performance by Sharpe Ratio", "Strategy Performance by Return [%]"],
        vertical_spacing=0.15
    )
    
    # Create color map for strategies
    import plotly.express as px
    colors = px.colors.qualitative.Plotly
    strategy_colors = {strategy: colors[i % len(colors)] for i, strategy in enumerate(all_strategies)}
    
    # Prepare data for plotting
    scenarios = list(results.keys())
    
    # Create dataframes for each metric
    sharpe_data = {}
    return_data = {}
    
    for scenario, df in results.items():
        for _, row in df.iterrows():
            strategy = row['Strategy']
            if strategy not in sharpe_data:
                sharpe_data[strategy] = {s: None for s in scenarios}
                return_data[strategy] = {s: None for s in scenarios}
            
            sharpe_data[strategy][scenario] = row['Sharpe Ratio']
            return_data[strategy][scenario] = row['Return [%]']
    
    # Plot Sharpe Ratio data
    for strategy in all_strategies:
        fig.add_trace(
            go.Bar(
                x=scenarios,
                y=[sharpe_data[strategy][s] if s in sharpe_data[strategy] else None for s in scenarios],
                name=strategy,
                marker_color=strategy_colors[strategy],
                legendgroup=strategy,
                showlegend=True,
                text=strategy
            ),
            row=1, col=1
        )
    
    # Plot Return data
    for strategy in all_strategies:
        fig.add_trace(
            go.Bar(
                x=scenarios,
                y=[return_data[strategy][s] if s in return_data[strategy] else None for s in scenarios],
                name=strategy,
                marker_color=strategy_colors[strategy],
                legendgroup=strategy,
                showlegend=False
            ),
            row=2, col=1
        )
    
    # Update layout
    fig.update_layout(
        title="Strategy Performance Across Scenarios",
        barmode='group',
        height=800,
        width=1200,
        template="plotly_white",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    # Add axis labels
    fig.update_yaxes(title_text="Sharpe Ratio", row=1, col=1)
    fig.update_yaxes(title_text="Return [%]", row=2, col=1)
    fig.update_xaxes(title_text="Scenario", row=2, col=1)
    
    # Save the figure if a path is provided
    if output_path:
        fig.write_html(output_path)
        print(f"Interactive scenario comparison saved to {output_path}")
    
    return fig

def generate_strategy_comparison_report(results_dir, output_file=None):
    """
    Generate a comprehensive strategy comparison report from multiple scenario results.
    
    Parameters:
        results_dir (str): Directory containing the scenario results CSV files
        output_file (str, optional): Path to save the report HTML file
    """
    import os
    import pandas as pd
    from datetime import datetime
    
    # Load all scenario results
    scenario_results = {}
    for filename in os.listdir(results_dir):
        if filename.endswith('.csv'):
            scenario_name = os.path.splitext(filename)[0]
            file_path = os.path.join(results_dir, filename)
            scenario_results[scenario_name] = pd.read_csv(file_path)
    
    if not scenario_results:
        print(f"No CSV result files found in {results_dir}")
        return
    
    # Create strategy ranking
    strategy_ranking = create_strategy_ranking(scenario_results)
    
    # Create visualizations
    fig_dir = os.path.join(results_dir, 'figures')
    os.makedirs(fig_dir, exist_ok=True)
    
    # Generate static visualization
    best_strategies_img = os.path.join(fig_dir, 'best_strategies.png')
    visualize_best_strategies(scenario_results, best_strategies_img)
    
    # Generate interactive visualization
    interactive_path = os.path.join(fig_dir, 'scenario_comparison.html')
    create_interactive_scenario_comparison(scenario_results, interactive_path)
    
    # Generate HTML report if output file is specified
    if output_file:
        generate_html_report(
            scenario_results=scenario_results,
            strategy_ranking=strategy_ranking,
            best_strategies_img=best_strategies_img,
            interactive_path=interactive_path,
            output_file=output_file
        )
        print(f"Strategy comparison report generated: {output_file}")
    
    return strategy_ranking

def generate_html_report(scenario_results, strategy_ranking, best_strategies_img, interactive_path, output_file):
    """
    Generate HTML report with strategy comparison results.
    
    Parameters:
        scenario_results (dict): Dictionary of scenario results DataFrames
        strategy_ranking (pd.DataFrame): DataFrame with strategy rankings
        best_strategies_img (str): Path to the best strategies visualization image
        interactive_path (str): Path to the interactive visualization HTML
        output_file (str): Path to save the HTML report
    """
    import os
    from datetime import datetime
    
    # Create HTML content
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Strategy Comparison Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1, h2, h3 {{ color: #333; }}
            table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
            th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
            th {{ background-color: #f2f2f2; }}
            tr:hover {{ background-color: #f5f5f5; }}
            .img-container {{ margin: 20px 0; }}
            .img-container img {{ max-width: 100%; }}
            .interactive-link {{ margin: 20px 0; }}
            a {{ color: #0066cc; text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}
        </style>
    </head>
    <body>
        <h1>Strategy Comparison Report</h1>
        <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <h2>Overall Strategy Ranking</h2>
        <table>
            <tr>
                <th>Strategy</th>
                <th>Return [%]</th>
                <th>Max. Drawdown [%]</th>
                <th>Sharpe Ratio</th>
                <th>Sortino Ratio</th>
                <th>Win Rate [%]</th>
                <th>Trades</th>
            </tr>
    """
    
    # Add rows for strategy ranking
    for _, row in strategy_ranking.iterrows():
        html_content += f"""
            <tr>
                <td>{row['Strategy']}</td>
                <td>{row['Return [%]']:.2f}</td>
                <td>{row['Max. Drawdown [%]']:.2f}</td>
                <td>{row['Sharpe Ratio']:.2f}</td>
                <td>{row['Sortino Ratio']:.2f}</td>
                <td>{row['Win Rate [%]']:.2f}</td>
                <td>{row['Trades']:.0f}</td>
            </tr>
        """
    
    html_content += """
        </table>
        
        <h2>Strategy Performance Visualization</h2>
        <div class="img-container">
            <img src="BEST_STRATEGIES_IMG_REL_PATH" alt="Strategy Performance">
        </div>
        
        <h2>Best Strategies by Scenario</h2>
    """
    
    # Add tables for each scenario
    for scenario, df in scenario_results.items():
        html_content += f"""
        <h3>{scenario} Scenario</h3>
        <table>
            <tr>
                <th>Strategy</th>
                <th>Return [%]</th>
                <th>Max. Drawdown [%]</th>
                <th>Sharpe Ratio</th>
                <th>Win Rate [%]</th>
            </tr>
        """
        
        # Sort by Sharpe Ratio
        df_sorted = df.sort_values('Sharpe Ratio', ascending=False)
        for _, row in df_sorted.iterrows():
            html_content += f"""
            <tr>
                <td>{row['Strategy']}</td>
                <td>{row['Return [%]']:.2f}</td>
                <td>{row['Max. Drawdown [%]']:.2f}</td>
                <td>{row['Sharpe Ratio']:.2f}</td>
                <td>{row['Win Rate [%]']:.2f}</td>
            </tr>
            """
        
        html_content += """
        </table>
        """
    
    # Add link to interactive visualization
    rel_interactive_path = os.path.relpath(interactive_path, os.path.dirname(output_file))
    html_content += f"""
        <div class="interactive-link">
            <a href="{rel_interactive_path}" target="_blank">View Interactive Strategy Comparison</a>
        </div>
    """
    
    html_content += """
    </body>
    </html>
    """
    
    # Replace image path with relative path
    rel_img_path = os.path.relpath(best_strategies_img, os.path.dirname(output_file))
    html_content = html_content.replace('BEST_STRATEGIES_IMG_REL_PATH', rel_img_path)
    
    # Write HTML file
    with open(output_file, 'w') as f:
        f.write(html_content)

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