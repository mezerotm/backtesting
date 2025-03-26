from backtesting import Strategy
from backtesting.lib import crossover
import talib
import pandas as pd
import numpy as np
from utils.strategy_utils import StrategyUtils

class SimpleMovingAverageCrossover(Strategy):
    """
    A simple moving average crossover strategy.
    
    This strategy serves as a baseline for comparison with other strategies.
    It uses two simple moving averages: a faster one and a slower one.
    
    - Buys when the fast MA crosses above the slow MA
    - Sells when the fast MA crosses below the slow MA
    
    Parameters:
        fast_ma (int): Period for the fast moving average (default: 20)
        slow_ma (int): Period for the slow moving average (default: 50)
    """
    
    # Define parameters with descriptive names
    fast_ma = 50  # Fast moving average period
    slow_ma = 200  # Slow moving average period
    
    def init(self):
        """
        Initialize the strategy by calculating the indicators.
        """
        # Calculate moving averages using StrategyUtils
        self.fast = StrategyUtils.add_indicator(
            self, 
            talib.SMA, 
            self.data.Close, 
            self.fast_ma,
            name=f'Fast SMA ({self.fast_ma})', 
            overlay=True, 
            color='blue'
        )
        
        self.slow = StrategyUtils.add_indicator(
            self, 
            talib.SMA, 
            self.data.Close, 
            self.slow_ma,
            name=f'Slow SMA ({self.slow_ma})', 
            overlay=True, 
            color='orange'
        )
        
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
        
        current_drawdown = (self.peak_equity - current_equity) / self.peak_equity * 100 if self.peak_equity > 0 else 0
        self.drawdown.append(current_drawdown)
        
        # Calculate the buy & hold return at the end of the backtest
        if len(self.data) - 1 == self.data.index[-1]:  # Check if we're at the last bar
            start_price = self.data.Close[0]
            end_price = self.data.Close[-1]
            self.buy_hold_return = (end_price - start_price) / start_price * 100
        
        # If we don't have any open position
        if not self.position:
            # Buy when fast MA crosses above slow MA
            if crossover(self.fast, self.slow):
                print(f"BUY SIGNAL detected at index {len(self.data)-1}, price: {self.data.Close[-1]}")
                self.buy()
                
                # Track entry for reference
                self.entry_price = self.data.Close[-1]
                self.entry_time = self.data.index[-1]
        else:
            # Sell when fast MA crosses below slow MA
            if crossover(self.slow, self.fast):
                print(f"SELL SIGNAL detected at index {len(self.data)-1}, price: {self.data.Close[-1]}")
                
                # Calculate P/L before closing
                exit_price = self.data.Close[-1]
                profit_loss = exit_price - self.entry_price
                profit_pct = profit_loss/self.entry_price*100
                
                # Store trade data for later analysis
                self.trade_data.append({
                    'entry_time': self.entry_time,
                    'exit_time': self.data.index[-1],
                    'entry_price': self.entry_price,
                    'exit_price': exit_price,
                    'profit_loss': profit_loss,
                    'profit_pct': profit_pct,
                    'trade_duration': (self.data.index[-1] - self.entry_time).days
                })
                
                print(f"Trade #{self.trade_count}: P/L = {profit_loss:.2f} ({profit_pct:.2f}%)")
                
                # Close position
                self.position.close()
                self.trade_count += 1
    
    def analyze(self):
        """
        Perform post-backtest analysis.
        This method is called after the backtest is complete.
        """
        # Analyze equity curve and drawdown
        if self.equity_curve:
            equity_df = pd.DataFrame({
                'Equity': self.equity_curve,
                'Drawdown': self.drawdown
            }, index=self.data.index[:len(self.equity_curve)])
            
            print("\n=== Equity and Drawdown Statistics ===")
            print(f"Final Equity: {self.equity_curve[-1]:.2f}")
            print(f"Peak Equity: {self.peak_equity:.2f}")
            print(f"Maximum Drawdown: {max(self.drawdown):.2f}%")
        
        # Convert trade data to DataFrame for analysis
        if self.trade_data:
            trades_df = pd.DataFrame(self.trade_data)
            
            # Print trade statistics
            print("\n=== Trade Statistics ===")
            print(f"Total Trades: {len(trades_df)}")
            print(f"Winning Trades: {len(trades_df[trades_df['profit_pct'] > 0])}")
            print(f"Losing Trades: {len(trades_df[trades_df['profit_pct'] <= 0])}")
            
            if len(trades_df) > 0:
                win_rate = len(trades_df[trades_df['profit_pct'] > 0]) / len(trades_df) * 100
                print(f"Win Rate: {win_rate:.2f}%")
                print(f"Average Profit: {trades_df['profit_pct'].mean():.2f}%")
                
                if len(trades_df[trades_df['profit_pct'] > 0]) > 0:
                    print(f"Average Winner: {trades_df[trades_df['profit_pct'] > 0]['profit_pct'].mean():.2f}%")
                
                if len(trades_df[trades_df['profit_pct'] <= 0]) > 0:
                    print(f"Average Loser: {trades_df[trades_df['profit_pct'] <= 0]['profit_pct'].mean():.2f}%")
                    
                    # Calculate profit factor if there are losing trades
                    profit_sum = trades_df[trades_df['profit_pct'] > 0]['profit_pct'].sum()
                    loss_sum = abs(trades_df[trades_df['profit_pct'] <= 0]['profit_pct'].sum())
                    
                    if loss_sum > 0:
                        print(f"Profit Factor: {profit_sum / loss_sum:.2f}")
                
                print(f"Average Trade Duration: {trades_df['trade_duration'].mean():.2f} days")
                
                # Compare to buy & hold
                if self.buy_hold_return is not None:
                    print(f"\nBuy & Hold Return: {self.buy_hold_return:.2f}%")
                    strategy_return = trades_df['profit_pct'].sum()
                    print(f"Strategy Return: {strategy_return:.2f}%")
                    print(f"Outperformance: {strategy_return - self.buy_hold_return:.2f}%")

class ExponentialMovingAverageCrossover(Strategy):
    """
    An exponential moving average crossover strategy.
    
    Similar to the SMA crossover but using exponential moving averages,
    which give more weight to recent prices.
    
    - Buys when the fast EMA crosses above the slow EMA
    - Sells when the fast EMA crosses below the slow EMA
    
    Parameters:
        fast_ema (int): Period for the fast exponential moving average (default: 12)
        slow_ema (int): Period for the slow exponential moving average (default: 26)
    """
    
    # Define parameters
    fast_ema = 12
    slow_ema = 26
    
    def init(self):
        """
        Initialize the strategy by calculating indicators.
        """
        # Calculate moving averages using StrategyUtils
        self.fast = StrategyUtils.add_indicator(
            self, 
            talib.EMA, 
            self.data.Close, 
            self.fast_ema,
            name=f'Fast EMA ({self.fast_ema})', 
            overlay=True, 
            color='blue'
        )
        
        self.slow = StrategyUtils.add_indicator(
            self, 
            talib.EMA, 
            self.data.Close, 
            self.slow_ema,
            name=f'Slow EMA ({self.slow_ema})', 
            overlay=True, 
            color='orange'
        )
        
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
        
        current_drawdown = (self.peak_equity - current_equity) / self.peak_equity * 100 if self.peak_equity > 0 else 0
        self.drawdown.append(current_drawdown)
        
        # Calculate the buy & hold return at the end of the backtest
        if len(self.data) - 1 == self.data.index[-1]:  # Check if we're at the last bar
            start_price = self.data.Close[0]
            end_price = self.data.Close[-1]
            self.buy_hold_return = (end_price - start_price) / start_price * 100
        
        # If we don't have any open position
        if not self.position:
            # Buy when fast EMA crosses above slow EMA
            if crossover(self.fast, self.slow):
                print(f"EMA BUY SIGNAL at index {len(self.data)-1}, price: {self.data.Close[-1]}")
                self.buy()
                
                # Track entry for reference
                self.entry_price = self.data.Close[-1]
                self.entry_time = self.data.index[-1]
        
        # If we have an open position
        else:
            # Sell when fast EMA crosses below slow EMA
            if crossover(self.slow, self.fast):
                print(f"EMA SELL SIGNAL at index {len(self.data)-1}, price: {self.data.Close[-1]}")
                
                # Calculate P/L before closing
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
                
                print(f"Trade #{self.trade_count}: P/L = {profit_loss:.2f} ({profit_pct:.2f}%)")
                
                self.position.close()
                self.trade_count += 1
    
    def analyze(self):
        """
        Perform post-backtest analysis.
        This method is called after the backtest is complete.
        """
        # Analyze equity curve and drawdown
        if self.equity_curve:
            equity_df = pd.DataFrame({
                'Equity': self.equity_curve,
                'Drawdown': self.drawdown
            }, index=self.data.index[:len(self.equity_curve)])
            
            print("\n=== Equity and Drawdown Statistics ===")
            print(f"Final Equity: {self.equity_curve[-1]:.2f}")
            print(f"Peak Equity: {self.peak_equity:.2f}")
            print(f"Maximum Drawdown: {max(self.drawdown):.2f}%")
        
        # Convert trade data to DataFrame for analysis
        if self.trade_data:
            trades_df = pd.DataFrame(self.trade_data)
            
            # Print trade statistics
            print("\n=== Trade Statistics ===")
            print(f"Total Trades: {len(trades_df)}")
            print(f"Winning Trades: {len(trades_df[trades_df['profit_pct'] > 0])}")
            print(f"Losing Trades: {len(trades_df[trades_df['profit_pct'] <= 0])}")
            
            if len(trades_df) > 0:
                win_rate = len(trades_df[trades_df['profit_pct'] > 0]) / len(trades_df) * 100
                print(f"Win Rate: {win_rate:.2f}%")
                print(f"Average Profit: {trades_df['profit_pct'].mean():.2f}%")
                
                if len(trades_df[trades_df['profit_pct'] > 0]) > 0:
                    print(f"Average Winner: {trades_df[trades_df['profit_pct'] > 0]['profit_pct'].mean():.2f}%")
                
                if len(trades_df[trades_df['profit_pct'] <= 0]) > 0:
                    print(f"Average Loser: {trades_df[trades_df['profit_pct'] <= 0]['profit_pct'].mean():.2f}%")
                    
                    # Calculate profit factor if there are losing trades
                    profit_sum = trades_df[trades_df['profit_pct'] > 0]['profit_pct'].sum()
                    loss_sum = abs(trades_df[trades_df['profit_pct'] <= 0]['profit_pct'].sum())
                    
                    if loss_sum > 0:
                        print(f"Profit Factor: {profit_sum / loss_sum:.2f}")
                
                print(f"Average Trade Duration: {trades_df['trade_duration'].mean():.2f} days")
                
                # Compare to buy & hold
                if self.buy_hold_return is not None:
                    print(f"\nBuy & Hold Return: {self.buy_hold_return:.2f}%")
                    strategy_return = trades_df['profit_pct'].sum()
                    print(f"Strategy Return: {strategy_return:.2f}%")
                    print(f"Outperformance: {strategy_return - self.buy_hold_return:.2f}%")