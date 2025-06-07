from backtesting import Backtest
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import webbrowser
import tempfile
import os
from typing import Dict, Type, List
from backtesting import Strategy

def compare_strategies(data, strategies, cash=10000, commission=0.002):
    """Compare multiple trading strategies."""
    results = {}
    
    for name, strategy_class in strategies.items():
        # Create a Backtest instance for each strategy
        bt = Backtest(data.copy(), strategy_class, cash=cash, commission=commission)
        stats = bt.run()
        # Store the stats object directly instead of trying to access _trade_data
        results[name] = stats
    
    # Convert results to DataFrame
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
            'SQN': stats.get('SQN', np.nan)  # Some versions might not have SQN
        }
    
    results_df = pd.DataFrame(metrics_data)
    
    # No need for metric mapping since we're already using the correct names
    
    return results_df

def plot_strategy_comparison(results_df, show_plot=True, save_path=None):
    """
    Plot strategy comparison results using matplotlib.
    
    Parameters:
        results_df (pd.DataFrame): DataFrame with metrics as rows and strategies as columns
        show_plot (bool): Whether to attempt to show the plot interactively
        save_path (str, optional): Path to save the figure as an image file
        
    Returns:
        matplotlib.figure.Figure: The matplotlib figure object
    """
    import matplotlib
    import matplotlib.pyplot as plt
    
    # Check if we're in a non-interactive environment
    if not matplotlib.is_interactive() and show_plot:
        print("Warning: Running in a non-interactive environment. Plot will be saved but not shown.")
        # Set a non-interactive backend if we're going to save but not show
        if save_path:
            matplotlib.use('Agg')
    
    # Define metrics to plot
    metrics_to_plot = [
        'Return [%]',
        'Max. Drawdown [%]',
        'Sharpe Ratio',
        'Win Rate [%]'
    ]
    
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    axes = axes.ravel()
    
    for i, metric in enumerate(metrics_to_plot):
        ax = axes[i]
        results_df.loc[metric].plot(kind='bar', ax=ax)
        ax.set_title(metric)
        ax.set_ylabel('Value')
        ax.tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    
    # Save the figure if a path is provided
    if save_path:
        plt.savefig(save_path)
        print(f"Strategy comparison plot saved to {save_path}")
    
    # Only try to show the plot if explicitly requested and we're in an interactive environment
    if show_plot and matplotlib.is_interactive():
        try:
            plt.show()
        except Exception as e:
            print(f"Could not display plot: {e}")
            print("Consider saving the plot to a file instead.")
    
    # Return the figure so it can be saved if needed
    return fig

def plot_interactive_comparison(results_df, show_plot=True):
    """
    Create an interactive Plotly visualization for strategy comparison.
    
    Parameters:
        results_df (pd.DataFrame): DataFrame with metrics as rows and strategies as columns
        show_plot (bool): Whether to open the plot in a browser
        
    Returns:
        plotly.graph_objects.Figure: The Plotly figure object
    """
    # Define metrics to plot
    metrics_to_plot = [
        'Return [%]',
        'Max. Drawdown [%]',
        'Sharpe Ratio',
        'Sortino Ratio',
        'Win Rate [%]',
        'Calmar Ratio'
    ]
    
    # Create subplots: 2 rows, 3 columns
    fig = make_subplots(
        rows=2, 
        cols=3,
        subplot_titles=metrics_to_plot,
        vertical_spacing=0.1,
        horizontal_spacing=0.05
    )
    
    # Get strategies (columns of the DataFrame)
    strategies = results_df.columns.tolist()
    
    # Define a color map for strategies
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
    
    # Add bars for each metric and strategy
    for i, metric in enumerate(metrics_to_plot):
        row = i // 3 + 1
        col = i % 3 + 1
        
        if metric in results_df.index:
            values = results_df.loc[metric]
            
            # For Max Drawdown, use negative values for better visualization
            y_values = values
            if metric == 'Max. Drawdown [%]':
                y_values = -values  # Negate for better visual comparison
            
            fig.add_trace(
                go.Bar(
                    x=strategies,
                    y=y_values,
                    name=metric,
                    marker_color=[colors[i % len(colors)] for _ in range(len(strategies))],
                    showlegend=False,
                    text=[f"{v:.2f}" for v in values],
                    textposition='auto'
                ),
                row=row, col=col
            )
            
            # Add a horizontal line at zero for reference
            fig.add_shape(
                type="line",
                x0=-0.5,
                x1=len(strategies) - 0.5,
                y0=0,
                y1=0,
                line=dict(color="gray", width=1, dash="dash"),
                row=row, col=col
            )
    
    # Update layout
    fig.update_layout(
        title="Strategy Comparison",
        height=800,
        width=1200,
        template="plotly_white",
        margin=dict(l=50, r=50, t=100, b=50)
    )
    
    # Show the plot in browser if requested
    if show_plot:
        # Create a temporary HTML file and open it in the browser
        with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as f:
            fig.write_html(f.name)
            webbrowser.open('file://' + os.path.realpath(f.name), new=2)
    
    return fig

def save_interactive_comparison(results_df, filename):
    """
    Save an interactive Plotly visualization to an HTML file.
    
    Parameters:
        results_df (pd.DataFrame): DataFrame with metrics as rows and strategies as columns
        filename (str): Path to save the HTML file
    """
    fig = plot_interactive_comparison(results_df, show_plot=False)
    fig.write_html(filename)
    print(f"Interactive comparison saved to {filename}")

def run_example():
    """
    Example usage of the comparison functions.
    """
    from strategies.moving_average import SimpleMovingAverageCrossover, ExponentialMovingAverageCrossover
    from strategies.advanced_strategy import MACDRSIStrategy, BollingerRSIStrategy
    import yfinance as yf
    import pandas as pd
    
    # Download sample data
    raw_data = yf.download('SPY', start='2018-01-01', end='2023-01-01')
    
    # Prepare data for backtesting
    # Handle multi-level column indices from yfinance
    if isinstance(raw_data.columns, pd.MultiIndex):
        raw_data.columns = raw_data.columns.get_level_values(1)
    
    # Define strategies to compare
    strategies = {
        'SMA Crossover': SimpleMovingAverageCrossover,
        'EMA Crossover': ExponentialMovingAverageCrossover,
        'MACD-RSI-EMA': MACDRSIStrategy,
        'Bollinger-RSI': BollingerRSIStrategy
    }
    
    # Compare strategies
    results = compare_strategies(raw_data, strategies)
    print("\nStrategy Comparison:")
    print(results)
    
    # Create results directory if it doesn't exist
    results_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'results')
    os.makedirs(results_dir, exist_ok=True)
    
    # Plot comparison and save to file
    plot_strategy_comparison(
        results, 
        show_plot=True,
        save_path=os.path.join(results_dir, 'strategy_comparison.png')
    )
    
    # Create and show interactive comparison
    plot_interactive_comparison(results)
    
    # Save interactive comparison to file
    save_interactive_comparison(results, os.path.join(results_dir, 'strategy_comparison.html'))
    
    # Return results for further analysis if needed
    return results

if __name__ == "__main__":
    run_example() 