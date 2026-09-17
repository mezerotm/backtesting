from backtesting import Strategy
from backtesting.lib import crossover
import pandas as pd
import talib


class CombinedStrategy(Strategy):
    """
    An experimental strategy that combines multiple technical indicators:
    - Moving Averages (SMA and EMA)
    - MACD (Moving Average Convergence Divergence)
    - RSI (Relative Strength Index)
    - Bollinger Bands

    The strategy uses a weighted scoring system to generate buy/sell signals
    based on the combined signals from all indicators.

    Entry conditions:
    - Positive overall score above the buy threshold
    - Multiple indicators showing bullish signals

    Exit conditions:
    - Negative overall score below the sell threshold
    - Multiple indicators showing bearish signals

    Parameters:
        fast_ma (int): Period for fast moving average
        slow_ma (int): Period for slow moving average
        ema_fast (int): Period for fast exponential moving average
        ema_slow (int): Period for slow exponential moving average
        macd_fast (int): Fast period for MACD
        macd_slow (int): Slow period for MACD
        macd_signal (int): Signal period for MACD
        rsi_period (int): Period for RSI calculation
        rsi_oversold (int): RSI oversold threshold
        rsi_overbought (int): RSI overbought threshold
        bb_period (int): Period for Bollinger Bands
        bb_dev (float): Standard deviation for Bollinger Bands
        buy_threshold (float): Minimum score required for buy signal
        sell_threshold (float): Maximum score required for sell signal
    """

    # Strategy parameters with sensible defaults
    # Moving Average parameters
    fast_ma = 20
    slow_ma = 50
    ema_fast = 12
    ema_slow = 26

    # MACD parameters
    macd_fast = 12
    macd_slow = 26
    macd_signal = 9

    # RSI parameters
    rsi_period = 14
    rsi_oversold = 30
    rsi_overbought = 70

    # Bollinger Bands parameters
    bb_period = 20
    bb_dev = 2.0

    # Signal thresholds
    buy_threshold = 2.0   # Minimum score to generate buy signal
    sell_threshold = -2.0  # Maximum score to generate sell signal

    def init(self):
        """Initialize the strategy with indicators."""
        # Calculate moving averages
        self.sma_short = self.I(
            talib.SMA,
            self.data.Close,
            timeperiod=self.fast_ma)
        self.sma_long = self.I(
            talib.SMA,
            self.data.Close,
            timeperiod=self.slow_ma)

        # Calculate RSI
        self.rsi = self.I(
            talib.RSI,
            self.data.Close,
            timeperiod=self.rsi_period)

        # Calculate Bollinger Bands
        self.bb_upper, self.bb_middle, self.bb_lower = self.I(
            talib.BBANDS, self.data.Close, period=self.bb_period, nbdevup=self.bb_dev, nbdevdn=self.bb_dev, matype=0)

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
        # Track drawdown duration
        if self.equity < self.dd_start_equity:
            self.dd_days += 1
            if self.dd_days > self.max_dd_duration:
                self.max_dd_duration = self.dd_days
        else:
            self.dd_start_equity = self.equity
            self.dd_days = 0

        # Calculate the buy & hold return at the end of the backtest
        if len(self.data) - \
                1 == self.data.index[-1]:  # Check if we're at the last bar
            start_price = self.data.Close[0]
            end_price = self.data.Close[-1]
            self.buy_hold_return = (
                end_price - start_price) / start_price * 100

        # Calculate signal scores from each indicator
        score = 0.0

        # --- Moving Average Signals ---
        # SMA Crossover (weight: 1.0)
        if crossover(self.sma_short, self.sma_long):
            score += 1.0
        elif crossover(self.sma_long, self.sma_short):
            score -= 1.0

        # Price above/below SMAs (weight: 0.5)
        if self.data.Close[-1] > self.sma_long[-1]:
            score += 0.5
        else:
            score -= 0.5

        # --- MACD Signals (weight: 1.5) ---
        if crossover(self.macd, self.signal):
            score += 1.5
        elif crossover(self.signal, self.macd):
            score -= 1.5

        # MACD histogram direction (weight: 0.5)
        if self.hist[-1] > self.hist[-2]:
            score += 0.5
        else:
            score -= 0.5

        # --- RSI Signals (weight: 1.5) ---
        # RSI signals (weight: 0.8)
        if self.rsi[-1] < self.rsi_oversold:
            score += 0.8  # Oversold - bullish signal
        elif self.rsi[-1] > self.rsi_overbought:
            score -= 0.8  # Overbought - bearish signal
        # RSI direction (weight: 0.5)
        if self.rsi[-1] > self.rsi[-2]:
            score += 0.5
        else:
            score -= 0.5

        # --- Bollinger Bands Signals (weight: 1.5) ---
        # Bollinger Band signals (weight: 0.6)
        if self.data.Close[-1] <= self.bb_lower[-1]:
            score += 0.6  # Price at lower band - bullish signal
        elif self.data.Close[-1] >= self.bb_upper[-1]:
            score -= 0.6  # Price at upper band - bearish signal
        # Price relative to middle band (weight: 0.5)
        if self.data.Close[-1] > self.bb_middle[-1]:
            score += 0.5
        else:
            score -= 0.5

        # Update the signal score indicator
        self.signal_score[-1] = score

        # Trading logic based on the combined score
        if not self.position:
            # Buy when score is above threshold
            if score >= self.buy_threshold:
                print(
                    f"BUY SIGNAL at index {len(self.data) - 1}, price: {self.data.Close[-1]}, score: {score:.2f}")
                self.buy()

                # Track entry for reference
                self.entry_price = self.data.Close[-1]
                self.entry_time = self.data.index[-1]
                self.entry_bar = len(self.data) - 1

                # Create a new order object for visualization
                new_order = {
                    'entry_bar': self.entry_bar,
                    'entry_price': self.entry_price,
                    'entry_time': self.entry_time,
                    'direction': 'long',
                    'exit_bar': None,
                    'exit_price': None,
                    'pl_pct': None
                }
                self.orders.append(new_order)
        else:
            # Sell when score is below threshold
            if score <= self.sell_threshold:
                print(
                    f"SELL SIGNAL at index {len(self.data) - 1}, price: {self.data.Close[-1]}, score: {score:.2f}")

                # Calculate P/L before closing
                exit_price = self.data.Close[-1]
                profit_loss = exit_price - self.entry_price
                profit_pct = profit_loss / self.entry_price * 100
                exit_bar = len(self.data) - 1

                # Store trade data
                self.trade_data.append({
                    'entry_time': self.entry_time,
                    'exit_time': self.data.index[-1],
                    'entry_price': self.entry_price,
                    'exit_price': exit_price,
                    'profit_loss': profit_loss,
                    'profit_pct': profit_pct,
                    'exit_score': score,
                    'order_duration': (self.data.index[-1] - self.entry_time).days
                })

                # Update the current order for visualization
                if self.orders:
                    current_order = self.orders[-1]
                    current_order['exit_bar'] = exit_bar
                    current_order['exit_price'] = exit_price
                    current_order['pl_pct'] = profit_pct

                print(
                    f"Order #{self.trade_count}: P/L = {profit_loss:.2f} ({profit_pct:.2f}%)")

                self.position.close()
                self.trade_count += 1

    def analyze(self):
        """
        Perform post-backtest analysis.
        This method is called after the backtest is complete.
        """
        # Add order markers to the chart
        # Add key metrics annotation
        if self.trade_data:
            orders_df = pd.DataFrame(self.trade_data)
            win_rate = len(orders_df[orders_df['profit_pct'] > 0]) / \
                len(orders_df) * 100 if len(orders_df) > 0 else 0

            metrics = {
                'Win Rate': f"{win_rate:.1f}%",
                'Total Orders': len(orders_df),
                'Max DD': f"{self.max_dd_duration} days"
            }

            # Calculate profit factor if there are losing orders
            if len(orders_df) > 0 and len(
                    orders_df[orders_df['profit_pct'] <= 0]) > 0:
                profit_sum = orders_df[orders_df['profit_pct']
                                       > 0]['profit_pct'].sum()
                loss_sum = abs(
                    orders_df[orders_df['profit_pct'] <= 0]['profit_pct'].sum())

                if loss_sum > 0:
                    metrics['Profit Factor'] = f"{profit_sum / loss_sum:.2f}"

            # Print trade statistics
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
                    print(
                        f"Average Profit: {orders_df['profit_pct'].mean():.2f}%")

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
                            print(
                                f"Profit Factor: {profit_sum /loss_sum:.2f}")

                    print(
                        f"Average Order Duration: {orders_df['order_duration'].mean():.2f} days")

                    # Compare to buy & hold
                    if self.buy_hold_return is not None:
                        print(
                            f"\nBuy & Hold Return: {self.buy_hold_return:.2f}%")
                        strategy_return = orders_df['profit_pct'].sum()
                        print(f"Strategy Return: {strategy_return:.2f}%")
                        print(
                            f"Outperformance: {strategy_return - self.buy_hold_return:.2f}%")

                    print(
                        f"Max Drawdown Duration: {self.max_dd_duration} days")
