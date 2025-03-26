from backtesting import Strategy
from backtesting.lib import crossover
import talib
import pandas as pd
import numpy as np
from utils.strategy_utils import StrategyUtils

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
        """
        Initialize the strategy by calculating all indicators.
        """
        # Calculate Simple Moving Averages using StrategyUtils
        self.sma_fast = StrategyUtils.add_indicator(
            self, 
            talib.SMA, 
            self.data.Close, 
            self.fast_ma,
            name=f'Fast SMA ({self.fast_ma})', 
            overlay=True, 
            color='blue'
        )
        
        self.sma_slow = StrategyUtils.add_indicator(
            self, 
            talib.SMA, 
            self.data.Close, 
            self.slow_ma,
            name=f'Slow SMA ({self.slow_ma})', 
            overlay=True, 
            color='orange'
        )
        
        # Calculate Exponential Moving Averages using StrategyUtils
        self.ema_fast = StrategyUtils.add_indicator(
            self, 
            talib.EMA, 
            self.data.Close, 
            self.ema_fast,
            name=f'Fast EMA ({self.ema_fast})', 
            overlay=True, 
            color='green'
        )
        
        self.ema_slow = StrategyUtils.add_indicator(
            self, 
            talib.EMA, 
            self.data.Close, 
            self.ema_slow,
            name=f'Slow EMA ({self.ema_slow})', 
            overlay=True, 
            color='red'
        )
        
        # Calculate MACD using StrategyUtils
        self.macd, self.signal, self.hist = StrategyUtils.add_complete_macd(
            self, 
            self.data.Close, 
            fast_period=self.macd_fast,
            slow_period=self.macd_slow,
            signal_period=self.macd_signal
        )
        
        # Calculate RSI using StrategyUtils
        self.rsi, self.rsi_oversold_line, self.rsi_overbought_line = StrategyUtils.add_complete_rsi(
            self,
            self.data.Close,
            period=self.rsi_period,
            oversold=self.rsi_oversold,
            overbought=self.rsi_overbought
        )
        
        # Calculate Bollinger Bands using StrategyUtils
        self.bb_upper, self.bb_middle, self.bb_lower = StrategyUtils.add_complete_bollinger_bands(
            self,
            self.data.Close,
            period=self.bb_period,
            num_std_dev=self.bb_dev
        )
        
        # Create a signal score indicator
        self.signal_score = StrategyUtils.add_indicator(
            self,
            lambda: np.zeros(len(self.data)),
            name='Signal Score',
            overlay=False,
            color='purple'
        )
        
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
        
        # One thing to add is to track the buy & hold performance
        # This ensures we're calculating it consistently
        self.buy_hold_return = None
    
    def next(self):
        """
        Execute the strategy logic for each candle.
        """
        # Track equity and drawdown for each bar
        current_equity = self.equity
        self.equity_curve.append(current_equity)
        
        # Update peak equity and calculate drawdown
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity
        
        current_drawdown = (self.peak_equity - current_equity) / self.peak_equity * 100 if self.peak_equity > 0 else 0
        self.drawdown.append(current_drawdown)
        
        # Calculate the buy & hold return at the end of the backtest
        # This should only be calculated once at the end of the backtest
        if len(self.data) - 1 == self.data.index[-1]:  # Check if we're at the last bar
            start_price = self.data.Close[0]
            end_price = self.data.Close[-1]
            self.buy_hold_return = (end_price - start_price) / start_price * 100
        
        # Calculate signal scores from each indicator
        score = 0.0
        
        # --- Moving Average Signals ---
        # SMA Crossover (weight: 1.0)
        if crossover(self.sma_fast, self.sma_slow):
            score += 1.0
        elif crossover(self.sma_slow, self.sma_fast):
            score -= 1.0
            
        # EMA Crossover (weight: 1.0)
        if crossover(self.ema_fast, self.ema_slow):
            score += 1.0
        elif crossover(self.ema_slow, self.ema_fast):
            score -= 1.0
            
        # Price above/below SMAs (weight: 0.5)
        if self.data.Close[-1] > self.sma_slow[-1]:
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
        # Oversold condition
        if self.rsi[-1] < self.rsi_oversold:
            score += 1.5
        # Overbought condition
        elif self.rsi[-1] > self.rsi_overbought:
            score -= 1.5
        # RSI direction (weight: 0.5)
        if self.rsi[-1] > self.rsi[-2]:
            score += 0.5
        else:
            score -= 0.5
            
        # --- Bollinger Bands Signals (weight: 1.5) ---
        # Price near lower band
        if self.data.Close[-1] <= self.bb_lower[-1]:
            score += 1.5
        # Price near upper band
        elif self.data.Close[-1] >= self.bb_upper[-1]:
            score -= 1.5
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
                print(f"BUY SIGNAL at index {len(self.data)-1}, price: {self.data.Close[-1]}, score: {score:.2f}")
                self.buy()
                
                # Track entry for reference
                self.entry_price = self.data.Close[-1]
                self.entry_time = self.data.index[-1]
        else:
            # Sell when score is below threshold
            if score <= self.sell_threshold:
                print(f"SELL SIGNAL at index {len(self.data)-1}, price: {self.data.Close[-1]}, score: {score:.2f}")
                
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
                    'exit_score': score,
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
