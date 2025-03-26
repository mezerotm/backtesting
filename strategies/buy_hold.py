from backtesting import Strategy
from backtesting.lib import crossover

class BuyAndHoldStrategy(Strategy):
    """Simple Buy and Hold strategy that buys at the beginning and holds until the end."""
    
    def init(self):
        """Initialize the strategy."""
        # No indicators needed for buy and hold
        self.buy_price = None
        self.buy_hold_return = None
    
    def next(self):
        """Define the trading logic."""
        # If we don't have a position, buy on the first bar
        if not self.position:
            self.buy()
            self.buy_price = self.data.Close[-1]
        
        # On the last bar, calculate the buy & hold return to ensure it matches
        if len(self.data) - 1 == self.data.index[-1]:  # Check if we're at the last bar
            if self.buy_price:
                end_price = self.data.Close[-1]
                # Calculate return the same way as the strategy's return
                self.buy_hold_return = (end_price - self.buy_price) / self.buy_price * 100
    
    def analyze(self):
        """Perform post-backtest analysis."""
        # If we calculated our buy_hold_return, print it for confirmation
        if self.buy_hold_return is not None:
            print(f"Buy & Hold Return calculated: {self.buy_hold_return:.2f}%") 