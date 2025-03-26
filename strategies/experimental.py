from backtesting import Strategy
from backtesting.lib import crossover
import talib as ta
import numpy as np

class ExperimentalCombinedStrategy(Strategy):
    """
    An experimental combined strategy that uses multiple indicators:
    - Moving Average Crossover
    - RSI for overbought/oversold conditions
    - MACD for trend confirmation
    - Bollinger Bands for volatility
    """
    
    # Parameters that can be optimized
    fast_ma = 10
    slow_ma = 50
    rsi_period = 14
    rsi_oversold = 30
    rsi_overbought = 70
    macd_fast = 12
    macd_slow = 26
    macd_signal = 9
    bb_period = 20
    bb_std = 2
    
    def init(self):
        """Initialize the strategy with indicators."""
        # Moving Averages
        self.fast_ma_line = self.I(ta.SMA, self.data.Close, self.fast_ma)
        self.slow_ma_line = self.I(ta.SMA, self.data.Close, self.slow_ma)
        
        # RSI
        self.rsi = self.I(ta.RSI, self.data.Close, self.rsi_period)
        
        # MACD
        macd_line, signal_line, histogram = ta.MACD(
            self.data.Close, 
            fastperiod=self.macd_fast, 
            slowperiod=self.macd_slow, 
            signalperiod=self.macd_signal
        )
        self.macd_line = self.I(lambda: macd_line)
        self.signal_line = self.I(lambda: signal_line)
        self.histogram = self.I(lambda: histogram)
        
        # Bollinger Bands
        upper, middle, lower = ta.BBANDS(
            self.data.Close, 
            timeperiod=self.bb_period, 
            nbdevup=self.bb_std, 
            nbdevdn=self.bb_std
        )
        self.bb_upper = self.I(lambda: upper)
        self.bb_middle = self.I(lambda: middle)
        self.bb_lower = self.I(lambda: lower)
    
    def next(self):
        """Define the trading logic."""
        # Buy conditions (all must be true):
        # 1. Fast MA crosses above Slow MA
        # 2. RSI is oversold (below 30)
        # 3. MACD line crosses above Signal line
        # 4. Price is near lower Bollinger Band
        
        buy_condition = (
            crossover(self.fast_ma_line, self.slow_ma_line) and
            self.rsi < self.rsi_oversold and
            crossover(self.macd_line, self.signal_line) and
            self.data.Close[-1] <= self.bb_lower[-1] * 1.02  # Within 2% of lower band
        )
        
        # Simplified buy condition if the strict one is too restrictive
        simplified_buy = (
            self.fast_ma_line[-1] > self.slow_ma_line[-1] and
            self.rsi[-1] < 40 and
            self.macd_line[-1] > self.signal_line[-1]
        )
        
        # Sell conditions (any can trigger):
        # 1. Fast MA crosses below Slow MA
        # 2. RSI is overbought (above 70)
        # 3. MACD line crosses below Signal line
        # 4. Price is near upper Bollinger Band
        
        sell_condition = (
            crossover(self.slow_ma_line, self.fast_ma_line) or
            self.rsi > self.rsi_overbought or
            crossover(self.signal_line, self.macd_line) or
            self.data.Close[-1] >= self.bb_upper[-1] * 0.98  # Within 2% of upper band
        )
        
        # Trading logic
        if not self.position:  # If not in a position
            if buy_condition or simplified_buy:  # Use either strict or simplified condition
                self.buy()
        else:  # If in a position
            if sell_condition:
                self.sell() 