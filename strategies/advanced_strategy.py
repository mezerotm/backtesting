from backtesting import Strategy
from backtesting.lib import crossover
import pandas as pd
import talib


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
    rsi_overbought = 70  # RSI overbought threshold

    ema_period = 100    # Trend filter EMA

    def init(self):
        """Initialize the strategy with indicators."""
        # Calculate MACD
        self.macd_line, self.signal_line, self.macd_histogram = self.I(
            talib.MACD, self.data.Close, fastperiod=self.macd_fast, slowperiod=self.macd_slow, signalperiod=self.macd_signal)

        # Calculate RSI
        self.rsi = self.I(
            talib.RSI,
            self.data.Close,
            timeperiod=self.rsi_period)

        # Calculate EMA for trend filter
        self.ema = self.I(
            talib.EMA,
            self.data.Close,
            timeperiod=self.ema_period)

        # Initialize tracking variables
        self.position_size = 0
        self.entry_price = 0
        self.peak_equity = 0
        self.equity_curve = []
        self.drawdown = []
        self.trade_data = []
        self.buy_hold_return = None

    def next(self):
        """
        Execute the strategy logic for each candle.
        """
        # Track equity and drawdown
        current_equity = self.equity
        self.equity_curve.append(current_equity)

        # Update peak equity and calculate drawdown
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity

        current_drawdown = (self.peak_equity - current_equity) / \
            self.peak_equity * 100 if self.peak_equity > 0 else 0
        self.drawdown.append(current_drawdown)

        # Calculate the buy & hold return at the end of the backtest
        if len(self.data) - \
                1 == self.data.index[-1]:  # Check if we're at the last bar
            start_price = self.data.Close[0]
            end_price = self.data.Close[-1]
            self.buy_hold_return = (
                end_price - start_price) / start_price * 100

        # Entry logic - if no position is open
        if not self.position:
            # Entry conditions:
            # 1. MACD line crosses above signal line
            # 2. RSI is above oversold but below overbought
            # 3. Price is above the trend filter EMA
            macd_crossover = crossover(self.macd_line, self.signal_line)
            rsi_good = self.rsi[-1] > self.rsi_oversold
            price_above_ema = self.data.Close[-1] > self.ema[-1]

            if macd_crossover and rsi_good and price_above_ema:
                print(
                    f"BUY SIGNAL at index {len(self.data) - 1}, price: {self.data.Close[-1]}")
                self.buy()

                # Track entry for reference
                self.entry_price = self.data.Close[-1]
                self.entry_time = self.data.index[-1]

        # Exit logic - if we have an open position
        else:
            # Exit conditions (any of these):
            # 1. MACD crosses below signal line
            # 2. RSI becomes overbought
            # 3. Price falls below EMA
            macd_crossunder = crossover(self.signal_line, self.macd_line)
            rsi_overbought = self.rsi[-1] > self.rsi_overbought
            price_below_ema = self.data.Close[-1] < self.ema[-1]

            if macd_crossunder or rsi_overbought or price_below_ema:
                print(
                    f"SELL SIGNAL at index {len(self.data) - 1}, price: {self.data.Close[-1]}")

                # Calculate P/L before closing
                exit_price = self.data.Close[-1]
                profit_loss = exit_price - self.entry_price
                profit_pct = profit_loss / self.entry_price * 100

                # Store trade data
                self.trade_data.append({
                    'entry_time': self.entry_time,
                    'exit_time': self.data.index[-1],
                    'entry_price': self.entry_price,
                    'exit_price': exit_price,
                    'profit_loss': profit_loss,
                    'profit_pct': profit_pct,
                    'trade_duration': (self.data.index[-1] - self.entry_time).days
                })

                print(
                    f"Trade #{self.trade_count}: P/L = {profit_loss:.2f} ({profit_pct:.2f}%)")

                self.position.close()
                self.trade_count += 1

    def analyze(self):
        """
        Perform post-backtest analysis.
        """
        # Analyze equity curve and drawdown
        if self.equity_curve:
            print("\n=== Equity and Drawdown Statistics ===")
            print(f"Final Equity: {self.equity_curve[-1]:.2f}")
            print(f"Peak Equity: {self.peak_equity:.2f}")
            print(f"Maximum Drawdown: {max(self.drawdown):.2f}%")

        # Calculate additional metrics
        self.metrics = {
            'total_return': (self.equity[-1] / self.equity[0] - 1) * 100,
            'max_drawdown': self.stats['Max. Drawdown [%]'],
            'sharpe_ratio': self.stats['Sharpe Ratio'],
            'sortino_ratio': self.stats['Sortino Ratio'],
            'win_rate': self.stats['Win Rate [%]'],
            'total_trades': self.stats['# Trades']
        }

        # Convert trade data to DataFrame for analysis
        if self.trade_data:
            orders_df = pd.DataFrame(self.trade_data)

            # Print trade statistics
            print("\n=== Trade Statistics ===")
            print(f"Total Orders: {len(orders_df)}")
            print(
                f"Winning Orders: {len(orders_df[orders_df['profit_pct'] > 0])}")
            print(
                f"Losing Orders: {len(orders_df[orders_df['profit_pct'] <= 0])}")

            if len(orders_df) > 0:
                win_rate = len(
                    orders_df[orders_df['profit_pct'] > 0]) / len(orders_df) * 100
                print(f"Win Rate: {win_rate:.2f}%")
                print(f"Average Profit: {orders_df['profit_pct'].mean():.2f}%")

                if len(orders_df[orders_df['profit_pct'] > 0]) > 0:
                    print(
                        f"Average Winner: {orders_df[orders_df['profit_pct'] > 0]['profit_pct'].mean():.2f}%")

                if len(orders_df[orders_df['profit_pct'] <= 0]) > 0:
                    print(
                        f"Average Loser: {orders_df[orders_df['profit_pct'] <= 0]['profit_pct'].mean():.2f}%")

                    # Calculate profit factor if there are losing orders
                    profit_sum = orders_df[orders_df['profit_pct']
                                           > 0]['profit_pct'].sum()
                    loss_sum = abs(
                        orders_df[orders_df['profit_pct'] <= 0]['profit_pct'].sum())

                    if loss_sum > 0:
                        print(f"Profit Factor: {profit_sum / loss_sum:.2f}")

                print(
                    f"Average Order Duration: {orders_df['trade_duration'].mean():.2f} days")

                # Compare to buy & hold
                if self.buy_hold_return is not None:
                    print(f"\nBuy & Hold Return: {self.buy_hold_return:.2f}%")
                    strategy_return = orders_df['profit_pct'].sum()
                    print(f"Strategy Return: {strategy_return:.2f}%")
                    print(
                        f"Outperformance: {strategy_return - self.buy_hold_return:.2f}%")


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
    rsi_overbought = 70  # RSI overbought threshold

    def init(self):
        """
        Initialize the strategy by calculating all indicators.
        """
        # Use StrategyUtils to add Bollinger Bands
        self.bb_upper, self.bb_middle, self.bb_lower = self.I(
            talib.BBANDS, self.data.Close, period=self.bb_period, nbdevup=self.bb_dev, nbdevdn=self.bb_dev, matype=0)

        # Use StrategyUtils to add RSI with threshold lines
        self.rsi = self.I(
            talib.RSI,
            self.data.Close,
            timeperiod=self.rsi_period)

        # Initialize trade tracking
        self.trade_count = 0
        self.trade_data = []

        # Track entry information
        self.entry_price = 0
        self.entry_time = None

        # Add tracking for equity and drawdown
        self.equity_curve = []
        self.peak_equity = 0
        self.drawdown = []

        # Track buy & hold return
        self.buy_hold_return = None

    def next(self):
        """
        Execute the strategy logic for each candle.
        """
        # Track equity and drawdown
        current_equity = self.equity
        self.equity_curve.append(current_equity)

        # Update peak equity and calculate drawdown
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity

        current_drawdown = (self.peak_equity - current_equity) / \
            self.peak_equity * 100 if self.peak_equity > 0 else 0
        self.drawdown.append(current_drawdown)

        # Calculate the buy & hold return at the end of the backtest
        if len(self.data) - \
                1 == self.data.index[-1]:  # Check if we're at the last bar
            start_price = self.data.Close[0]
            end_price = self.data.Close[-1]
            self.buy_hold_return = (
                end_price - start_price) / start_price * 100

        # Entry logic - if no position is open
        if not self.position:
            # Check if price is at or below lower Bollinger Band
            price_at_lower_band = self.data.Close[-1] <= self.bb_lower[-1]
            # Check if RSI is oversold
            rsi_oversold = self.rsi[-1] <= self.rsi_oversold

            if price_at_lower_band and rsi_oversold:
                print(
                    f"BUY SIGNAL at index {len(self.data) - 1}, price: {self.data.Close[-1]}")
                self.buy()

                # Track entry for reference
                self.entry_price = self.data.Close[-1]
                self.entry_time = self.data.index[-1]

        # Exit logic - if we have an open position
        else:
            # Check if price is at or above middle Bollinger Band
            price_at_middle_band = self.data.Close[-1] >= self.bb_middle[-1]
            # Check if price is at or above upper Bollinger Band
            price_at_upper_band = self.data.Close[-1] >= self.bb_upper[-1]
            # Check if RSI is overbought
            rsi_overbought = self.rsi[-1] >= self.rsi_overbought

            if price_at_middle_band or price_at_upper_band or rsi_overbought:
                print(
                    f"SELL SIGNAL at index {len(self.data) - 1}, price: {self.data.Close[-1]}")

                # Calculate P/L before closing
                exit_price = self.data.Close[-1]
                profit_loss = exit_price - self.entry_price
                profit_pct = profit_loss / self.entry_price * 100

                # Store trade data
                self.trade_data.append({
                    'entry_time': self.entry_time,
                    'exit_time': self.data.index[-1],
                    'entry_price': self.entry_price,
                    'exit_price': exit_price,
                    'profit_loss': profit_loss,
                    'profit_pct': profit_pct,
                    'trade_duration': (self.data.index[-1] - self.entry_time).days
                })

                print(
                    f"Trade #{self.trade_count}: P/L = {profit_loss:.2f} ({profit_pct:.2f}%)")

                self.position.close()
                self.trade_count += 1

    def analyze(self):
        """
        Perform post-backtest analysis.
        """
        # Analyze equity curve and drawdown
        if self.equity_curve:
            print("\n=== Equity and Drawdown Statistics ===")
            print(f"Final Equity: {self.equity_curve[-1]:.2f}")
            print(f"Peak Equity: {self.peak_equity:.2f}")
            print(f"Maximum Drawdown: {max(self.drawdown):.2f}%")

        # Calculate additional metrics
        self.metrics = {
            'total_return': (self.equity[-1] / self.equity[0] - 1) * 100,
            'max_drawdown': self.stats['Max. Drawdown [%]'],
            'sharpe_ratio': self.stats['Sharpe Ratio'],
            'sortino_ratio': self.stats['Sortino Ratio'],
            'win_rate': self.stats['Win Rate [%]'],
            'total_trades': self.stats['# Trades']
        }

        # Convert trade data to DataFrame for analysis
        if self.trade_data:
            orders_df = pd.DataFrame(self.trade_data)

            # Print trade statistics
            print("\n=== Trade Statistics ===")
            print(f"Total Orders: {len(orders_df)}")
            print(
                f"Winning Orders: {len(orders_df[orders_df['profit_pct'] > 0])}")
            print(
                f"Losing Orders: {len(orders_df[orders_df['profit_pct'] <= 0])}")

            if len(orders_df) > 0:
                win_rate = len(
                    orders_df[orders_df['profit_pct'] > 0]) / len(orders_df) * 100
                print(f"Win Rate: {win_rate:.2f}%")
                print(f"Average Profit: {orders_df['profit_pct'].mean():.2f}%")

                if len(orders_df[orders_df['profit_pct'] > 0]) > 0:
                    print(
                        f"Average Winner: {orders_df[orders_df['profit_pct'] > 0]['profit_pct'].mean():.2f}%")

                if len(orders_df[orders_df['profit_pct'] <= 0]) > 0:
                    print(
                        f"Average Loser: {orders_df[orders_df['profit_pct'] <= 0]['profit_pct'].mean():.2f}%")

                    # Calculate profit factor if there are losing orders
                    profit_sum = orders_df[orders_df['profit_pct']
                                           > 0]['profit_pct'].sum()
                    loss_sum = abs(
                        orders_df[orders_df['profit_pct'] <= 0]['profit_pct'].sum())

                    if loss_sum > 0:
                        print(f"Profit Factor: {profit_sum / loss_sum:.2f}")

                print(
                    f"Average Order Duration: {orders_df['trade_duration'].mean():.2f} days")

                # Compare to buy & hold
                if self.buy_hold_return is not None:
                    print(f"\nBuy & Hold Return: {self.buy_hold_return:.2f}%")
                    strategy_return = orders_df['profit_pct'].sum()
                    print(f"Strategy Return: {strategy_return:.2f}%")
                    print(
                        f"Outperformance: {strategy_return - self.buy_hold_return:.2f}%")
