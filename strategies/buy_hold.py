from backtesting import Strategy
from config.backend.logger import get_app_logger

logger = get_app_logger(__name__)


class BuyAndHoldStrategy(Strategy):
    """Simple Buy and Hold strategy that buys at the beginning and holds until the end."""

    def init(self):
        """Initialize the strategy."""
        # No indicators needed for buy & hold
        self.position_size = 0
        self.entry_price = 0
        self.peak_equity = 0
        self.equity_curve = []
        self.drawdown = []
        self.trade_data = []
        self.buy_hold_return = None

    def next(self):
        """Define the trading logic."""
        # Track drawdown duration
        if self.equity < self.dd_start_equity:
            self.dd_days += 1
            if self.dd_days > self.max_dd_duration:
                self.max_dd_duration = self.dd_days
        else:
            self.dd_start_equity = self.equity
            self.dd_days = 0

        # If we don't have a position, buy on the first bar
        if not self.position:
            self.buy()

            # Track entry for reference
            self.entry_price = self.data.Close[-1]
            self.entry_time = self.data.index[-1]
            self.entry_bar = len(self.data) - 1
            print(
                f"BUY SIGNAL at index {
                    self.entry_bar}, price: {
                    self.entry_price}")

            # Create a new trade object for visualization
            new_trade = {
                'entry_bar': self.entry_bar,
                'entry_price': self.entry_price,
                'entry_time': self.entry_time,
                'direction': 'long',
                'exit_bar': None,
                'exit_price': None,
                'pl_pct': None
            }
            # Use _trade_list instead of trades
            self._trade_list.append(new_trade)

        # Calculate the buy & hold return at the end of the backtest
        if len(self.data) - \
                1 == self.data.index[-1]:  # Check if we're at the last bar
            start_price = self.data.Close[0]
            end_price = self.data.Close[-1]
            self.buy_hold_return = (
                end_price - start_price) / start_price * 100

            # Record the final trade if we have a position
            if self.position:
                exit_price = self.data.Close[-1]
                exit_bar = len(self.data) - 1
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

                # Update the current trade for visualization
                if self._trade_list:  # Use _trade_list instead of trades
                    current_trade = self._trade_list[-1]
                    current_trade['exit_bar'] = exit_bar
                    current_trade['exit_price'] = exit_price
                    current_trade['pl_pct'] = profit_pct

                print(f"Final P/L = {profit_loss:.2f} ({profit_pct:.2f}%)")

    def analyze(self):
        """Perform post-backtest analysis."""
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
