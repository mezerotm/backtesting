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
    
    @staticmethod
    def add_volume_indicator(strategy, volume, name="Volume", color=None):
        """
        Add volume indicator to the chart.
        
        Args:
            strategy: The strategy instance
            volume: Series of volume data
            name: Name for the volume indicator
            color: Color for the volume bars
            
        Returns:
            The volume indicator
        """
        volume_args = {
            'name': name,
            'overlay': False,
        }
        
        if color:
            volume_args['color'] = color
            
        return strategy.I(lambda: volume, **volume_args)
    
    @staticmethod
    def add_moving_averages(strategy, close_prices, periods=None, ema=False):
        """
        Add a set of moving averages to the chart.
        
        Args:
            strategy: The strategy instance
            close_prices: Series of closing prices
            periods: List of periods for the moving averages (default: [20, 50])
            ema: Whether to use EMA instead of SMA (default: False)
            
        Returns:
            List of moving average indicators
        """
        if periods is None:
            periods = [20, 50]
            
        results = []
        func = talib.EMA if ema else talib.SMA
        func_name = "EMA" if ema else "SMA"
        
        for period in periods:
            ma = StrategyUtils.add_indicator(
                strategy,
                func,
                close_prices,
                timeperiod=period,
                name=f"{func_name} ({period})",
                overlay=True,
                color=None  # Let the system assign colors
            )
            results.append(ma)
            
        return results
    
    @staticmethod
    def setup_standard_chart(strategy, data):
        """
        Set up a standard trading chart with common indicators.
        
        Args:
            strategy: The strategy instance
            data: The price/OHLCV data
            
        Returns:
            Dictionary of created indicators
        """
        results = {}
        
        # Add moving averages
        results['fast_sma'] = StrategyUtils.add_indicator(
            strategy, talib.SMA, data.Close, timeperiod=20,
            name='Fast SMA (20)', overlay=True, color='blue'
        )
        
        results['slow_sma'] = StrategyUtils.add_indicator(
            strategy, talib.SMA, data.Close, timeperiod=50,
            name='Slow SMA (50)', overlay=True, color='orange'
        )
        
        results['fast_ema'] = StrategyUtils.add_indicator(
            strategy, talib.EMA, data.Close, timeperiod=12,
            name='Fast EMA (12)', overlay=True, color='purple'
        )
        
        results['slow_ema'] = StrategyUtils.add_indicator(
            strategy, talib.EMA, data.Close, timeperiod=26,
            name='Slow EMA (26)', overlay=True, color='brown'
        )
        
        # Add Bollinger Bands
        bb_upper, bb_middle, bb_lower = StrategyUtils.add_complete_bollinger_bands(
            strategy, data.Close, period=20, num_std_dev=2.0
        )
        results['bb_upper'] = bb_upper
        results['bb_middle'] = bb_middle
        results['bb_lower'] = bb_lower
        
        # Add MACD
        macd, signal, hist = StrategyUtils.add_complete_macd(
            strategy, data.Close, fast_period=12, slow_period=26, signal_period=9
        )
        results['macd'] = macd
        results['signal'] = signal
        results['hist'] = hist
        
        # Add volume indicator if available
        if hasattr(data, 'Volume'):
            results['volume'] = StrategyUtils.add_volume_indicator(
                strategy, data.Volume, color='#00AA00'
            )
        
        return results 
    
    @staticmethod
    def add_performance_metrics(strategy, data, equity_curve=None):
        """
        Add comprehensive performance metrics panels to the chart.
        
        Args:
            strategy: The strategy instance
            data: The price/OHLCV data
            equity_curve: Custom equity curve if available (otherwise uses strategy.equity_curve)
            
        Returns:
            Dictionary of created indicators
        """
        results = {}
        
        # Use strategy's equity curve if none provided
        if equity_curve is None and hasattr(strategy, 'equity_curve'):
            equity_curve = strategy.equity_curve
        
        # Add equity panel
        if equity_curve is not None:
            # Main equity curve
            results['equity'] = strategy.I(
                lambda: equity_curve,
                name='Equity',
                overlay=False,
                color='blue',
                panel='Equity'
            )
            
            # Add peak equity as annotation
            peak_equity = np.max(equity_curve)
            results['peak_equity_line'] = strategy.I(
                lambda: np.full(len(data), peak_equity),
                name=f'Peak (${peak_equity:.2f})',
                overlay=False,
                color='cyan',
                linestyle='--',
                panel='Equity'
            )
            
            # Add max drawdown line
            if hasattr(strategy, 'max_dd_duration'):
                results['max_dd_line'] = strategy.I(
                    lambda: np.full(len(data), 0),  # Placeholder value
                    name=f'Max Dd Dur. ({strategy.max_dd_duration} days)',
                    overlay=False,
                    color='red',
                    linestyle='-',
                    panel='Equity'
                )
            
            # Calculate and add return curve
            initial_equity = equity_curve[0] if len(equity_curve) > 0 else 1
            returns = equity_curve / initial_equity - 1  # Percentage returns
            results['returns'] = strategy.I(
                lambda: returns * 100,  # Convert to percentage
                name='Return %',
                overlay=False,
                color='blue',
                panel='Return'
            )
            
            # Add peak return
            peak_return = np.max(returns) * 100
            results['peak_return_line'] = strategy.I(
                lambda: np.full(len(data), peak_return),
                name=f'Peak ({peak_return:.2f}%)',
                overlay=False,
                color='cyan',
                linestyle='--',
                panel='Return'
            )
            
            # Calculate and add drawdown curve
            if len(equity_curve) > 0:
                running_max = np.maximum.accumulate(equity_curve)
                drawdown = (equity_curve / running_max - 1) * 100  # Convert to percentage
                results['drawdown'] = strategy.I(
                    lambda: drawdown,
                    name='Drawdown',
                    overlay=False,
                    color='blue',
                    panel='Drawdown'
                )
                
                # Add peak drawdown point
                peak_dd = np.min(drawdown)
                results['peak_dd_point'] = strategy.I(
                    lambda: np.full(len(data), peak_dd if peak_dd < -10 else -50),  # Ensure visibility
                    name=f'Peak ({abs(peak_dd):.2f}%)',
                    overlay=False,
                    color='red',
                    linestyle='',
                    panel='Drawdown'
                )
        
        return results
    
    @staticmethod
    def add_trade_markers(strategy, trades=None):
        """
        Add trade markers and profit/loss visualization.
        
        Args:
            strategy: The strategy instance
            trades: List of trade objects (if None, tries to get from strategy)
            
        Returns:
            Dictionary of created indicators
        """
        results = {}
        
        # Get trades from strategy if not provided
        if trades is None and hasattr(strategy, 'trades'):
            trades = strategy.trades
        
        if trades:
            # Create buy markers
            buy_signals = np.zeros(len(strategy.data.Close))
            # Create sell markers
            sell_signals = np.zeros(len(strategy.data.Close))
            # Create profit/loss markers
            profit_markers = []
            loss_markers = []
            
            # Process trades to create markers
            for trade in trades:
                # This is a simplified example - you would need to map trade entry/exit times
                # to the corresponding indices in your price data
                if hasattr(trade, 'entry_bar') and trade.entry_bar < len(buy_signals):
                    buy_signals[trade.entry_bar] = strategy.data.Close[trade.entry_bar]
                
                if hasattr(trade, 'exit_bar') and trade.exit_bar < len(sell_signals):
                    sell_signals[trade.exit_bar] = strategy.data.Close[trade.exit_bar]
                    
                    # Add to profit/loss visualization
                    if hasattr(trade, 'pl_pct'):
                        marker = {
                            'index': trade.exit_bar,
                            'value': 0,  # Baseline
                            'size': abs(trade.pl_pct) * 0.5 + 5,  # Scale marker size with profit/loss
                            'color': 'green' if trade.pl_pct > 0 else 'red'
                        }
                        if trade.pl_pct > 0:
                            profit_markers.append(marker)
                        else:
                            loss_markers.append(marker)
            
            # Add buy signals to chart
            if np.any(buy_signals):
                results['buy_signals'] = strategy.I(
                    lambda: buy_signals,
                    name='Buy',
                    overlay=True,
                    color='green',
                    scatter=True,
                    scatter_size=100
                )
            
            # Add sell signals to chart
            if np.any(sell_signals):
                results['sell_signals'] = strategy.I(
                    lambda: sell_signals,
                    name='Sell',
                    overlay=True,
                    color='red',
                    scatter=True,
                    scatter_size=100
                )
            
            # Add profit/loss visualization
            # Note: This implementation may need to be adjusted based on the specific
            # APIs and capabilities of your backtesting library
            results['trade_count'] = strategy.I(
                lambda: np.zeros(len(strategy.data)) + 0.5,  # Fixed position for marker placement
                name=f'Trades ({len(trades)})',
                overlay=False,
                color='black',
                panel='Profit / Loss'
            )
        
        return results
    
    @staticmethod
    def setup_complete_chart(strategy, data):
        """
        Set up a complete trading chart with all standard indicators and performance metrics.
        
        Args:
            strategy: The strategy instance
            data: The price/OHLCV data
            
        Returns:
            Dictionary of created indicators
        """
        results = {}
        
        # Add standard price indicators
        indicator_results = StrategyUtils.setup_standard_chart(strategy, data)
        results.update(indicator_results)
        
        # Add performance metrics
        performance_results = StrategyUtils.add_performance_metrics(strategy, data)
        results.update(performance_results)
        
        # Add trade markers and profit/loss visualization
        trade_results = StrategyUtils.add_trade_markers(strategy)
        results.update(trade_results)
        
        return results

    @staticmethod 
    def annotate_key_metrics(strategy, metrics):
        """
        Annotate the chart with key performance metrics.
        
        Args:
            strategy: The strategy instance
            metrics: Dictionary of metrics to display (e.g., {'CAGR': 15.2, 'Sharpe': 1.1})
            
        Returns:
            Dictionary of created annotations
        """
        results = {}
        
        # Create a text annotation with key metrics
        metrics_text = ', '.join([f"{k}: {v}" for k, v in metrics.items()])
        
        # This is a placeholder - implementation depends on the specific
        # annotation capabilities of your backtesting library
        results['metrics_annotation'] = strategy.I(
            lambda: np.zeros(len(strategy.data)),
            name=metrics_text,
            overlay=True,
            color='black'
        )
        
        return results 