from backtesting import Strategy
from backtesting.lib import crossover
import pandas as pd
import numpy as np
from utils.strategy_utils import StrategyUtils

class BuyAndHoldStrategy(Strategy):
    """Simple Buy and Hold strategy that buys at the beginning and holds until the end."""
    
    def init(self):
        """Initialize the strategy."""
        # Set up the complete chart with all indicators and panels
        self.indicators = StrategyUtils.setup_complete_chart(self, self.data)
        
        # Initialize trade tracking
        self.trade_count = 0
        self.trade_data = []
        self._trade_list = []  # Renamed from self.trades to avoid property conflict
        
        # Track entry information
        self.entry_price = 0
        self.entry_time = None
        self.entry_bar = 0
        
        # Buy & hold return tracking
        self.buy_hold_return = None
        
        # Initialize equity and drawdown tracking variables
        self.max_dd_duration = 0
        self.dd_start_equity = self.equity
        self.dd_days = 0
    
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
            print(f"BUY SIGNAL at index {self.entry_bar}, price: {self.entry_price}")
            
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
            self._trade_list.append(new_trade)  # Use _trade_list instead of trades
            
        # Calculate the buy & hold return at the end of the backtest
        if len(self.data) - 1 == self.data.index[-1]:  # Check if we're at the last bar
            start_price = self.data.Close[0]
            end_price = self.data.Close[-1]
            self.buy_hold_return = (end_price - start_price) / start_price * 100
            
            # Record the final trade if we have a position
            if self.position:
                exit_price = self.data.Close[-1]
                exit_bar = len(self.data) - 1
                profit_loss = exit_price - self.entry_price
                profit_pct = profit_loss/self.entry_price*100
                
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
        # Add trade markers to the chart
        StrategyUtils.add_trade_markers(self, self._trade_list)  # Use _trade_list instead of trades
        
        # Add key metrics annotation
        if self.trade_data:
            trades_df = pd.DataFrame(self.trade_data)
            
            metrics = {
                'Buy & Hold': f"{self.buy_hold_return:.1f}%",
                'Duration': f"{trades_df['trade_duration'].mean():.0f} days",
                'Max DD': f"{self.max_dd_duration} days"
            }
            
            StrategyUtils.annotate_key_metrics(self, metrics)
        
        # Print trade statistics
        if self.trade_data:
            trades_df = pd.DataFrame(self.trade_data)
            
            print("\n=== Buy & Hold Performance ===")
            print(f"Buy & Hold Return: {self.buy_hold_return:.2f}%")
            print(f"Strategy Return: {trades_df['profit_pct'].sum():.2f}%")
            print(f"Trade Duration: {trades_df['trade_duration'].mean():.2f} days")
            print(f"Max Drawdown Duration: {self.max_dd_duration} days") 