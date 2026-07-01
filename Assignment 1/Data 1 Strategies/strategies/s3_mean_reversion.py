import backtrader as bt
import backtrader.indicators as btind

class MeanReversionStrategy(bt.Strategy):
    """
    Mean Reversion Strategy for Series 09
    
    Strategy Logic:
    - Buy when price deviates significantly below moving average (oversold)
    - Sell when price returns to or above moving average (mean reversion)
    - Use statistical measures to identify deviation thresholds
    - Suitable for assets that oscillate around a long-term mean
    """
    
    params = (
        ('mean_period', 30),        # Period for calculating mean price
        ('std_period', 30),         # Period for calculating standard deviation
        ('entry_threshold', 2.0),   # Standard deviations below mean for entry (OPTIMIZED)
        ('exit_threshold', 0.5),    # Standard deviations above mean for exit (OPTIMIZED)
        ('rsi_period', 14),         # RSI for oversold/overbought confirmation
        ('rsi_oversold', 30),       # RSI oversold level
        ('rsi_overbought', 70),     # RSI overbought level
        ('volume_period', 10),      # Volume average period
        ('volume_threshold', 0.8),  # Minimum volume threshold (0.8x average)
        ('stake_pct', 0.15),        # Position size (15% of portfolio) (OPTIMIZED)
        ('stop_loss', 0.05),        # Stop loss percentage (5%)
        ('take_profit', 0.04),      # Take profit percentage (4%) (OPTIMIZED)
        ('max_holding_days', 20),   # Maximum holding period (OPTIMIZED)
        ('series_index', 8),        # Series 09 at index 8
    )
    
    def __init__(self):
        # Select the data feed for series 09
        self.data_target = self.datas[self.params.series_index]
        
        # Mean reversion indicators
        self.mean_price = btind.SMA(self.data_target.close, period=self.params.mean_period)
        self.std_dev = btind.StdDev(self.data_target.close, period=self.params.std_period)
        
        # Calculate z-score (standardized distance from mean)
        self.z_score = (self.data_target.close - self.mean_price) / self.std_dev
        
        # RSI for confirmation
        self.rsi = btind.RSI(self.data_target.close, period=self.params.rsi_period)
        
        # Volume confirmation
        self.volume_avg = btind.SMA(self.data_target.volume, period=self.params.volume_period)
        
        # Track entry details
        self.entry_price = None
        self.entry_date = None
        self.order = None
        
    def start(self):
        self.log("Mean Reversion Strategy started for Series 09")
        
    def next(self):
        if self.order:
            return
            
        # Get current position
        position = self.getposition(self.data_target)
        current_price = self.data_target.close[0]
        current_date = self.datas[0].datetime.date(0)
        
        # Calculate position size
        portfolio_value = self.broker.getvalue()
        position_value = portfolio_value * self.params.stake_pct
        size = int(position_value / current_price)
        
        # Skip if indicators not ready
        if len(self.z_score) < 2 or len(self.volume_avg) < 1:
            return
        
        # Volume confirmation
        volume_ok = self.data_target.volume[0] >= self.volume_avg[0] * self.params.volume_threshold
        
        # Entry Logic - Mean reversion opportunity
        if position.size == 0:
            # Buy when price is significantly below mean (oversold condition)
            oversold_signal = (self.z_score[0] <= -self.params.entry_threshold and
                              self.rsi[0] <= self.params.rsi_oversold and
                              volume_ok)
            
            if oversold_signal:
                if self.overspend_guard([(self.data_target, size)]):
                    self.order = self.buy(data=self.data_target, size=size)
                    self.entry_price = current_price
                    self.entry_date = current_date
                    self.dlog(f"BUY mean reversion: Price={current_price:.2f}, Mean={self.mean_price[0]:.2f}, "
                             f"Z-score={self.z_score[0]:.2f}, RSI={self.rsi[0]:.1f}")
        
        # Exit Logic
        elif position.size > 0:
            # Calculate holding period
            holding_days = (current_date - self.entry_date).days if self.entry_date else 0
            
            exit_signal = False
            exit_reason = ""
            
            # Mean reversion exit - price returns to mean
            if self.z_score[0] >= self.params.exit_threshold:
                exit_signal = True
                exit_reason = f"Mean reversion (Z-score={self.z_score[0]:.2f})"
            
            # RSI overbought exit
            elif self.rsi[0] >= self.params.rsi_overbought:
                exit_signal = True
                exit_reason = f"RSI overbought ({self.rsi[0]:.1f})"
            
            # Stop loss
            elif self.entry_price and (current_price <= self.entry_price * (1 - self.params.stop_loss)):
                exit_signal = True
                exit_reason = f"Stop loss ({self.params.stop_loss*100:.0f}%)"
            
            # Take profit
            elif self.entry_price and (current_price >= self.entry_price * (1 + self.params.take_profit)):
                exit_signal = True
                exit_reason = f"Take profit ({self.params.take_profit*100:.0f}%)"
            
            # Maximum holding period
            elif holding_days >= self.params.max_holding_days:
                exit_signal = True
                exit_reason = f"Max holding period ({self.params.max_holding_days} days)"
            
            # Price moves further away from mean (failed reversion)
            elif self.z_score[0] <= -self.params.entry_threshold * 1.5:
                exit_signal = True
                exit_reason = "Failed reversion (deeper oversold)"
            
            if exit_signal:
                self.order = self.sell(data=self.data_target, size=position.size)
                self.dlog(f"SELL signal ({exit_reason}): Price={current_price:.2f}, "
                         f"Entry={self.entry_price:.2f}, Days={holding_days}")
                self.entry_price = None
                self.entry_date = None
    
    def notify_order(self, order):
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY EXECUTED: Price={order.executed.price:.2f}, Size={order.executed.size}')
            else:
                self.log(f'SELL EXECUTED: Price={order.executed.price:.2f}, Size={order.executed.size}')
        
        if order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f'Order {order.getstatusname()}')
        
        self.order = None
    
    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()}: {txt}')
    
    def dlog(self, txt, dt=None):
        if hasattr(self, '_debug') and self._debug:
            self.log(txt, dt)