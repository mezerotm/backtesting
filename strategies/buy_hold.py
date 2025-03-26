from backtesting import Strategy
from backtesting.lib import crossover
import pandas as pd
import numpy as np
from utils.strategy_utils import StrategyUtils

class BuyAndHoldStrategy(Strategy):
    """Simple Buy and Hold strategy that buys at the beginning and holds until the end."""
    
    def init(self):
        """Initialize the strategy."""
        # No indicators needed for buy and hold
        self.buy_price = None
        self.buy_hold_return = None
        
        # Add tracking for equity and drawdown
        self.equity_curve = []
        self.peak_equity = 0
        self.drawdown = []
        
        # Initialize trade tracking
        self.trade_count = 0
        self.trade_data = []
        
        # Track entry information
        self.entry_price = 0
        self.entry_time = None
    
    def next(self):
        """Define the trading logic."""
        # If we don't have a position, buy on the first bar
        if not self.position:
            self.buy()
            self.buy_price = self.data.Close[-1]
            
            # Track entry for reference
            self.entry_price = self.data.Close[-1]
            self.entry_time = self.data.index[-1]
            print(f"BUY SIGNAL at index {len(self.data)-1}, price: {self.data.Close[-1]}")
            
        # Track equity and drawdown
        current_equity = self.equity
        self.equity_curve.append(current_equity)
        
        # Update peak equity and calculate drawdown
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity
        
        current_drawdown = (self.peak_equity - current_equity) / self.peak_equity * 100 if self.peak_equity > 0 else 0
        self.drawdown.append(current_drawdown)
            
        # Calculate the buy & hold return at the end of the backtest
        if len(self.data) - 1 == self.data.index[-1]:  # Check if we're at the last bar
            start_price = self.data.Close[0]
            end_price = self.data.Close[-1]
            self.buy_hold_return = (end_price - start_price) / start_price * 100
            
            # Record the final trade if we have a position
            if self.position:
                exit_price = self.data.Close[-1]
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
                
                print(f"Final P/L = {profit_loss:.2f} ({profit_pct:.2f}%)")
    
    def analyze(self):
        """Perform post-backtest analysis."""
        # Convert equity curve and drawdown to DataFrames for analysis
        if self.equity_curve:
            equity_df = pd.DataFrame({
                'Equity': self.equity_curve,
                'Drawdown': self.drawdown
            }, index=self.data.index[:len(self.equity_curve)])
            
            print("\n=== Equity and Drawdown Statistics ===")
            print(f"Final Equity: {self.equity_curve[-1]:.2f}")
            print(f"Peak Equity: {self.peak_equity:.2f}")
            print(f"Maximum Drawdown: {max(self.drawdown):.2f}%")
            
        # Print trade statistics
        if self.trade_data:
            trades_df = pd.DataFrame(self.trade_data)
            
            print("\n=== Trade Statistics ===")
            print(f"Total Trades: {len(trades_df)}")
            
            if len(trades_df) > 0:
                print(f"Buy & Hold Return: {self.buy_hold_return:.2f}%")
                print(f"Strategy Return: {trades_df['profit_pct'].sum():.2f}%")
                print(f"Trade Duration: {trades_df['trade_duration'].mean():.2f} days") 