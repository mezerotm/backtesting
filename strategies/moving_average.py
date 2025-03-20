from backtesting import Strategy
from backtesting.lib import crossover
import talib
import pandas as pd
import numpy as np

class SimpleMovingAverageCrossover(Strategy):
    """
    A simple moving average crossover strategy.
    
    This strategy serves as a baseline for comparison with other strategies.
    It uses two simple moving averages: a faster one and a slower one.
    
    - Buys when the fast MA crosses above the slow MA
    - Sells when the fast MA crosses below the slow MA
    
    Parameters:
        fast_ma (int): Period for the fast moving average (default: 20)
        slow_ma (int): Period for the slow moving average (default: 50)
    """
    
    # Define parameters with descriptive names
    fast_ma = 20  # Fast moving average period
    slow_ma = 50  # Slow moving average period
    
    def init(self):
        """
        Initialize the strategy by calculating the indicators.
        """
        # Calculate moving averages using TA-Lib with proper names and colors
        # This will both store the values for strategy logic and display them in the chart
        self.fast = self.I(talib.SMA, self.data.Close, self.fast_ma, 
                          overlay=True, name=f'Fast SMA ({self.fast_ma})', color='blue')
        self.slow = self.I(talib.SMA, self.data.Close, self.slow_ma, 
                          overlay=True, name=f'Slow SMA ({self.slow_ma})', color='orange')
        
        # Note: We no longer need duplicate indicator declarations
    
    def next(self):
        """
        Execute the strategy logic for each candle.
        """
        # If we don't have any open position
        if not self.position:
            # Buy when fast MA crosses above slow MA
            if crossover(self.fast, self.slow):
                self.buy()
        
        # If we have an open position
        else:
            # Sell when fast MA crosses below slow MA
            if crossover(self.slow, self.fast):
                self.position.close()

class ExponentialMovingAverageCrossover(Strategy):
    """
    An exponential moving average crossover strategy.
    
    Similar to the SMA crossover but using exponential moving averages,
    which give more weight to recent prices.
    
    - Buys when the fast EMA crosses above the slow EMA
    - Sells when the fast EMA crosses below the slow EMA
    
    Parameters:
        fast_ema (int): Period for the fast exponential moving average (default: 12)
        slow_ema (int): Period for the slow exponential moving average (default: 26)
    """
    
    # Define parameters
    fast_ema = 12
    slow_ema = 26
    
    def init(self):
        """
        Initialize the strategy by calculating the indicators.
        """
        # Calculate moving averages using TA-Lib with proper names and colors
        # This will both store the values for strategy logic and display them in the chart
        self.fast = self.I(talib.EMA, self.data.Close, self.fast_ema, 
                          overlay=True, name=f'Fast EMA ({self.fast_ema})', color='blue')
        self.slow = self.I(talib.EMA, self.data.Close, self.slow_ema, 
                          overlay=True, name=f'Slow EMA ({self.slow_ema})', color='orange')
        
        # Note: No need for duplicate indicator declarations
    
    def next(self):
        """
        Execute the strategy logic for each candle.
        """
        # If we don't have any open position
        if not self.position:
            # Buy when fast EMA crosses above slow EMA
            if crossover(self.fast, self.slow):
                self.buy()
        
        # If we have an open position
        else:
            # Sell when fast EMA crosses below slow EMA
            if crossover(self.slow, self.fast):
                self.position.close()