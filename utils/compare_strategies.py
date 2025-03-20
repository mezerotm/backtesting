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

def plot_strategy_comparison(results_df):
    """Plot strategy comparison results."""
    import matplotlib.pyplot as plt
    
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
    plt.show()

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
    
    # Plot comparison
    plot_strategy_comparison(results)
    
    # Return results for further analysis if needed
    return results

if __name__ == "__main__":
    run_example() 