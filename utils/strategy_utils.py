import numpy as np
import pandas as pd
import talib
from backtesting import Strategy

class StrategyUtils:
    """
    Utility class for enhancing strategy visualization and functionality.
    This class provides methods to add indicators, annotations, and other
    visual elements to strategy charts consistently across all strategies.
    """
    
    @staticmethod
    def add_indicator(strategy, func, *args, name=None, overlay=False, color=None, **kwargs):
        """
        Add an indicator to the strategy chart with proper naming and styling.
        
        Args:
            strategy: The strategy instance
            func: The indicator function to call (e.g., talib.SMA)
            *args: Arguments to pass to the indicator function
            name: Custom name for the indicator
            overlay: Whether to overlay on price chart (True) or create a subplot (False)
            color: Color for the indicator line
            **kwargs: Additional keyword arguments for the indicator function
            
        Returns:
            The indicator values
        """
        # Generate a default name if none provided
        if name is None:
            func_name = func.__name__ if hasattr(func, '__name__') else 'indicator'
            name = f"{func_name}({', '.join(str(a) for a in args if not isinstance(a, pd.Series))})"
        
        # Add indicator to the strategy
        indicator_args = {
            'name': name,
            'overlay': overlay
        }
        
        if color:
            indicator_args['color'] = color
            
        return strategy.I(func, *args, **kwargs, **indicator_args)
    
    @staticmethod
    def add_threshold_line(strategy, value, name="Threshold", overlay=False, color='gray'):
        """
        Add a horizontal threshold line to the chart.
        
        Args:
            strategy: The strategy instance
            value: The y-value for the horizontal line
            name: Name for the line
            overlay: Whether to overlay on price chart
            color: Color for the line
            
        Returns:
            The line values
        """
        return strategy.I(
            lambda: np.repeat(value, len(strategy.data)),
            name=name,
            overlay=overlay,
            color=color
        )
    
    @staticmethod
    def add_band(strategy, upper_values, lower_values, name="Band", overlay=True):
        """
        Add a band (like Bollinger Bands) between upper and lower values.
        
        Args:
            strategy: The strategy instance
            upper_values: Upper band values
            lower_values: Lower band values
            name: Name prefix for the band
            overlay: Whether to overlay on price chart
            
        Returns:
            Tuple of (upper, lower) indicators
        """
        upper = strategy.I(
            lambda: upper_values,
            name=f"{name} Upper",
            overlay=overlay,
            color='red'
        )
        
        lower = strategy.I(
            lambda: lower_values,
            name=f"{name} Lower",
            overlay=overlay,
            color='green'
        )
        
        return upper, lower
    
    @staticmethod
    def add_signal_markers(strategy, buy_signals, sell_signals):
        """
        Add buy and sell signal markers to the chart.
        
        Args:
            strategy: The strategy instance
            buy_signals: Array of boolean values indicating buy signals
            sell_signals: Array of boolean values indicating sell signals
        """
        # This is a placeholder - backtesting.py doesn't directly support
        # adding custom markers, but this method could be expanded in the future
        # when such functionality becomes available
        pass
    
    @staticmethod
    def calculate_macd(close_prices, fast_period=12, slow_period=26, signal_period=9):
        """
        Calculate MACD indicator with proper naming.
        
        Args:
            close_prices: Series of closing prices
            fast_period: Fast EMA period
            slow_period: Slow EMA period
            signal_period: Signal line period
            
        Returns:
            Tuple of (macd_line, signal_line, histogram)
        """
        macd_line, signal_line, histogram = talib.MACD(
            close_prices,
            fastperiod=fast_period,
            slowperiod=slow_period,
            signalperiod=signal_period
        )
        return macd_line, signal_line, histogram
    
    @staticmethod
    def calculate_bollinger_bands(close_prices, period=20, num_std_dev=2):
        """
        Calculate Bollinger Bands.
        
        Args:
            close_prices: Series of closing prices
            period: Period for the moving average
            num_std_dev: Number of standard deviations
            
        Returns:
            Tuple of (upper_band, middle_band, lower_band)
        """
        upper, middle, lower = talib.BBANDS(
            close_prices,
            timeperiod=period,
            nbdevup=num_std_dev,
            nbdevdn=num_std_dev,
            matype=0
        )
        return upper, middle, lower
    
    @staticmethod
    def add_complete_rsi(strategy, close_prices, period=14, oversold=30, overbought=70):
        """
        Add RSI indicator with overbought and oversold lines.
        
        Args:
            strategy: The strategy instance
            close_prices: Series of closing prices
            period: RSI calculation period
            oversold: Oversold threshold
            overbought: Overbought threshold
            
        Returns:
            Tuple of (rsi, oversold_line, overbought_line)
        """
        # Calculate RSI
        rsi = StrategyUtils.add_indicator(
            strategy,
            talib.RSI,
            close_prices,
            timeperiod=period,
            name=f'RSI ({period})',
            overlay=False,
            color='blue'
        )
        
        # Add threshold lines
        oversold_line = StrategyUtils.add_threshold_line(
            strategy, 
            oversold, 
            name='RSI Oversold', 
            overlay=False, 
            color='green'
        )
        
        overbought_line = StrategyUtils.add_threshold_line(
            strategy, 
            overbought, 
            name='RSI Overbought', 
            overlay=False, 
            color='red'
        )
        
        return rsi, oversold_line, overbought_line
    
    @staticmethod
    def add_complete_macd(strategy, close_prices, fast_period=12, slow_period=26, signal_period=9):
        """
        Add MACD indicator with signal line and histogram.
        
        Args:
            strategy: The strategy instance
            close_prices: Series of closing prices
            fast_period: Fast EMA period
            slow_period: Slow EMA period
            signal_period: Signal line period
            
        Returns:
            Tuple of (macd_line, signal_line, histogram)
        """
        # Calculate MACD components
        macd_line, signal_line, histogram = StrategyUtils.calculate_macd(
            close_prices, 
            fast_period, 
            slow_period, 
            signal_period
        )
        
        # Add MACD line
        macd = StrategyUtils.add_indicator(
            strategy,
            lambda: macd_line,
            name=f'MACD ({fast_period},{slow_period},{signal_period})',
            overlay=False,
            color='blue'
        )
        
        # Add signal line
        signal = StrategyUtils.add_indicator(
            strategy,
            lambda: signal_line,
            name=f'Signal ({signal_period})',
            overlay=False,
            color='red'
        )
        
        # Add histogram
        hist = StrategyUtils.add_indicator(
            strategy,
            lambda: histogram,
            name='Histogram',
            overlay=False,
            color='green'
        )
        
        return macd, signal, hist
    
    @staticmethod
    def add_complete_bollinger_bands(strategy, close_prices, period=20, num_std_dev=2):
        """
        Add complete Bollinger Bands indicator.
        
        Args:
            strategy: The strategy instance
            close_prices: Series of closing prices
            period: Period for the moving average
            num_std_dev: Number of standard deviations
            
        Returns:
            Tuple of (upper_band, middle_band, lower_band)
        """
        # Calculate Bollinger Bands
        upper, middle, lower = StrategyUtils.calculate_bollinger_bands(
            close_prices, period, num_std_dev
        )
        
        # Add upper band
        upper_band = StrategyUtils.add_indicator(
            strategy,
            lambda: upper,
            name=f'BB Upper ({period}, {num_std_dev})',
            overlay=True,
            color='red'
        )
        
        # Add middle band (SMA)
        middle_band = StrategyUtils.add_indicator(
            strategy,
            lambda: middle,
            name=f'BB SMA ({period})',
            overlay=True,
            color='blue'
        )
        
        # Add lower band
        lower_band = StrategyUtils.add_indicator(
            strategy,
            lambda: lower,
            name=f'BB Lower ({period}, {num_std_dev})',
            overlay=True,
            color='green'
        )
        
        return upper_band, middle_band, lower_band 