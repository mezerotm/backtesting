from backtesting import Strategy
from backtesting.lib import crossover
import talib
import pandas as pd
import numpy as np

class MACDRSIStrategy(Strategy):
    """
    An advanced strategy that combines:
    - MACD (Moving Average Convergence Divergence)
    - RSI (Relative Strength Index)
    - EMA (Exponential Moving Average)
    
    Entry conditions:
    - MACD line crosses above signal line
    - RSI is above oversold threshold but below overbought threshold
    - Price is above the long-term EMA (trend filter)
    
    Exit conditions:
    - MACD line crosses below signal line, or
    - RSI goes above overbought threshold, or
    - Price falls below the long-term EMA
    
    Parameters:
        macd_fast (int): Fast period for MACD calculation
        macd_slow (int): Slow period for MACD calculation
        macd_signal (int): Signal period for MACD
        rsi_period (int): Period for RSI calculation
        rsi_oversold (int): RSI oversold threshold
        rsi_overbought (int): RSI overbought threshold
        ema_period (int): Period for trend-following EMA
    """
    
    # Strategy parameters
    macd_fast = 12      # Fast period for MACD
    macd_slow = 26      # Slow period for MACD
    macd_signal = 9     # Signal line period
    
    rsi_period = 14     # RSI calculation period
    rsi_oversold = 30   # RSI oversold threshold
    rsi_overbought = 70 # RSI overbought threshold
    
    ema_period = 100    # Trend filter EMA
    
    def init(self):
        """
        Initialize the strategy by calculating all indicators.
        """
        # Calculate MACD using TA-Lib with proper names and colors
        self.macd, self.signal, self.hist = self.I(
            talib.MACD, 
            self.data.Close, 
            fastperiod=self.macd_fast,
            slowperiod=self.macd_slow,
            signalperiod=self.macd_signal,
            name=f'MACD ({self.macd_fast},{self.macd_slow},{self.macd_signal})',
            overlay=False
        )
        
        # Calculate RSI using TA-Lib with proper name
        self.rsi = self.I(
            talib.RSI, 
            self.data.Close, 
            timeperiod=self.rsi_period,
            name=f'RSI ({self.rsi_period})',
            overlay=False
        )
        
        # Calculate EMA trend filter using TA-Lib with proper name and color
        self.ema = self.I(
            talib.EMA, 
            self.data.Close, 
            timeperiod=self.ema_period,
            name=f'Trend EMA ({self.ema_period})',
            overlay=True,
            color='purple'
        )
        
        # Add RSI threshold lines with proper names and colors
        self.rsi_oversold_line = self.I(
            lambda: np.repeat(self.rsi_oversold, len(self.data)),
            name='RSI Oversold',
            overlay=False,
            color='green'
        )
        self.rsi_overbought_line = self.I(
            lambda: np.repeat(self.rsi_overbought, len(self.data)),
            name='RSI Overbought',
            overlay=False,
            color='red'
        )
    
    def next(self):
        """
        Execute the strategy logic for each candle.
        """
        # Entry logic - if no position is open
        if not self.position:
            # Entry conditions:
            # 1. MACD line crosses above signal line
            # 2. RSI is above oversold but below overbought
            # 3. Price is above the trend filter EMA
            macd_crossover = crossover(self.macd, self.signal)
            rsi_good = self.rsi_oversold_line[-1] < self.rsi[-1] < self.rsi_overbought_line[-1]
            price_above_ema = self.data.Close[-1] > self.ema[-1]
            
            if macd_crossover and rsi_good and price_above_ema:
                self.buy()
        
        # Exit logic - if we have an open position
        else:
            # Exit conditions (any of these):
            # 1. MACD crosses below signal line
            # 2. RSI becomes overbought
            # 3. Price falls below EMA
            macd_crossunder = crossover(self.signal, self.macd)
            rsi_overbought = self.rsi[-1] > self.rsi_overbought_line[-1]
            price_below_ema = self.data.Close[-1] < self.ema[-1]
            
            if macd_crossunder or rsi_overbought or price_below_ema:
                self.position.close()


class BollingerRSIStrategy(Strategy):
    """
    A strategy that combines Bollinger Bands and RSI:
    - Uses Bollinger Bands for identifying volatility and potential reversals
    - Uses RSI for confirming oversold/overbought conditions
    
    Entry conditions:
    - Price touches or crosses below the lower Bollinger Band
    - RSI is in oversold territory
    
    Exit conditions:
    - Price touches or crosses above the middle Bollinger Band (MA), or
    - Price touches or crosses above the upper Bollinger Band, or
    - RSI becomes overbought
    
    Parameters:
        bb_period (int): Period for Bollinger Bands calculation
        bb_dev (float): Number of standard deviations for Bollinger Bands
        rsi_period (int): Period for RSI calculation
        rsi_oversold (int): RSI oversold threshold
        rsi_overbought (int): RSI overbought threshold
    """
    
    # Strategy parameters
    bb_period = 20      # Bollinger Bands period
    bb_dev = 2.0        # Number of standard deviations
    
    rsi_period = 14     # RSI calculation period
    rsi_oversold = 30   # RSI oversold threshold
    rsi_overbought = 70 # RSI overbought threshold
    
    def init(self):
        """
        Initialize the strategy by calculating all indicators.
        """
        # Calculate Bollinger Bands using TA-Lib with proper names and colors
        self.bb_upper, self.bb_middle, self.bb_lower = self.I(
            talib.BBANDS,
            self.data.Close,
            timeperiod=self.bb_period,
            nbdevup=self.bb_dev,
            nbdevdn=self.bb_dev,
            matype=0,  # Simple Moving Average
            name=f'BB ({self.bb_period}, {self.bb_dev})',
            overlay=True,
            color=['red', 'blue', 'green']
        )
        
        # Calculate RSI using TA-Lib with proper name
        self.rsi = self.I(
            talib.RSI, 
            self.data.Close, 
            timeperiod=self.rsi_period,
            name=f'RSI ({self.rsi_period})',
            overlay=False
        )
        
        # Add RSI threshold lines with proper names and colors
        self.rsi_oversold_line = self.I(
            lambda: np.repeat(self.rsi_oversold, len(self.data)),
            name='RSI Oversold',
            overlay=False,
            color='green'
        )
        self.rsi_overbought_line = self.I(
            lambda: np.repeat(self.rsi_overbought, len(self.data)),
            name='RSI Overbought',
            overlay=False,
            color='red'
        )
    
    def next(self):
        """
        Execute the strategy logic for each candle.
        """
        # Entry logic - if no position is open
        if not self.position:
            # Check if price is at or below lower Bollinger Band
            price_at_lower_band = self.data.Close[-1] <= self.bb_lower[-1]
            # Check if RSI is oversold
            rsi_oversold = self.rsi[-1] <= self.rsi_oversold_line[-1]
            
            if price_at_lower_band and rsi_oversold:
                self.buy()
        
        # Exit logic - if we have an open position
        else:
            # Check if price is at or above middle Bollinger Band
            price_at_middle_band = self.data.Close[-1] >= self.bb_middle[-1]
            # Check if price is at or above upper Bollinger Band
            price_at_upper_band = self.data.Close[-1] >= self.bb_upper[-1]
            # Check if RSI is overbought
            rsi_overbought = self.rsi[-1] >= self.rsi_overbought_line[-1]
            
            if price_at_middle_band or price_at_upper_band or rsi_overbought:
                self.position.close() 