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
    
    def analyze(self):
        """Perform post-backtest analysis."""
        # The buy & hold return should match the strategy's overall return
        # No need to calculate it here as the backtesting framework will do it accurately
        pass 