#!/usr/bin/env python3
"""
Strategy 1: Dual Moving Average Crossover (Trend-Following)

Target: Series 04
Type: Trend-Following / Momentum

Optimized Parameters:
- Fast MA: 3 days
- Slow MA: 24 days

Entry:
- Fast MA (3-day) crosses above Slow MA (24-day) - Golden Cross
- Price > Fast MA (momentum confirmation)
- Volume > average (volume confirmation)

Exit:
- Fast MA crosses below Slow MA (Death Cross)
- OR Stop-loss: -10%
- OR Take-profit: +20%

Position Sizing: 25% of portfolio value
"""

import backtrader as bt


class DualMACrossover(bt.Strategy):
    """
    Dual Moving Average Crossover Strategy for Series 04.

    This strategy captures trend reversals using moving average crossovers.
    Designed for volatile assets with clear V-shaped patterns.
    """

    params = (
        ('fast_period', 3),       # Fast MA period (optimized)
        ('slow_period', 24),      # Slow MA period (optimized)
        ('volume_period', 10),    # Volume average period
        ('stop_pct', 0.10),       # Stop-loss percentage (10%)
        ('target_pct', 0.20),     # Take-profit percentage (20%)
        ('stake_pct', 0.25),      # Position size (25% of portfolio)
        ('series_index', 3),      # Series 04 is at index 3 (0-based)
        ('debug', False),         # Debug logging
    )

    def __init__(self):
        """Initialize indicators and tracking variables."""
        self.data_target = self.datas[self.params.series_index]

        # Moving averages
        self.fast_ma = bt.indicators.SimpleMovingAverage(
            self.data_target.close,
            period=self.params.fast_period
        )
        self.slow_ma = bt.indicators.SimpleMovingAverage(
            self.data_target.close,
            period=self.params.slow_period
        )

        # Crossover signal
        self.crossover = bt.indicators.CrossOver(self.fast_ma, self.slow_ma)

        # Volume indicator
        self.volume_ma = bt.indicators.SimpleMovingAverage(
            self.data_target.volume,
            period=self.params.volume_period
        )

        # Track entry price for stop-loss and take-profit
        self.entry_price = None
        self.entry_bar = None

        # Track orders
        self.order = None

        # Performance tracking
        self.trades_count = 0
        self.wins = 0
        self.losses = 0

    def log(self, txt, dt=None):
        """Logging function."""
        dt = dt or self.data_target.datetime.date(0)
        print(f'{dt.isoformat()} | {txt}')

    def dlog(self, txt, dt=None):
        """Debug logging (only if debug=True)."""
        if self.params.debug:
            self.log(txt, dt)

    def notify_order(self, order):
        """Track order status."""
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY EXECUTED: Price={order.executed.price:.2f}, '
                        f'Size={order.executed.size:.0f}, '
                        f'Cost={order.executed.value:.2f}, '
                        f'Comm={order.executed.comm:.2f}')
                self.entry_price = order.executed.price
                self.entry_bar = len(self)
            elif order.issell():
                self.log(f'SELL EXECUTED: Price={order.executed.price:.2f}, '
                        f'Size={order.executed.size:.0f}, '
                        f'Value={order.executed.value:.2f}, '
                        f'Comm={order.executed.comm:.2f}')
                # Calculate P&L
                if self.entry_price:
                    pnl = order.executed.price - self.entry_price
                    pnl_pct = (pnl / self.entry_price) * 100
                    self.log(f'TRADE P&L: {pnl:.2f} ({pnl_pct:+.2f}%)')

                    self.trades_count += 1
                    if pnl > 0:
                        self.wins += 1
                    else:
                        self.losses += 1

                self.entry_price = None
                self.entry_bar = None

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f'ORDER CANCELED/MARGIN/REJECTED: {order.status}')

        self.order = None

    def notify_trade(self, trade):
        """Track trade closure."""
        if not trade.isclosed:
            return

        self.dlog(f'TRADE CLOSED: Gross P&L={trade.pnl:.2f}, '
                 f'Net P&L={trade.pnlcomm:.2f}')

    def next(self):
        """Main strategy logic executed on each bar."""
        # Skip if we have a pending order
        if self.order:
            return

        # Get current position
        position = self.getposition(self.data_target)
        pos_size = position.size

        current_price = self.data_target.close[0]
        current_volume = self.data_target.volume[0]

        # Debug info
        self.dlog(f'Close={current_price:.2f}, '
                 f'Fast MA={self.fast_ma[0]:.2f}, '
                 f'Slow MA={self.slow_ma[0]:.2f}, '
                 f'Volume={current_volume:.0f}, '
                 f'Volume MA={self.volume_ma[0]:.0f}, '
                 f'Position={pos_size:.0f}')

        # ===== EXIT LOGIC =====
        if pos_size > 0:
            # Check stop-loss
            if self.entry_price:
                stop_price = self.entry_price * (1 - self.params.stop_pct)
                target_price = self.entry_price * (1 + self.params.target_pct)

                if current_price <= stop_price:
                    self.log(f'STOP-LOSS TRIGGERED: '
                            f'Price {current_price:.2f} <= Stop {stop_price:.2f}')
                    self.order = self.sell(data=self.data_target, size=pos_size)
                    return

                if current_price >= target_price:
                    self.log(f'TAKE-PROFIT TRIGGERED: '
                            f'Price {current_price:.2f} >= Target {target_price:.2f}')
                    self.order = self.sell(data=self.data_target, size=pos_size)
                    return

            # Check death cross
            if self.crossover[0] < 0:  # Fast MA crosses below Slow MA
                self.log(f'DEATH CROSS: Selling {pos_size:.0f} units')
                self.order = self.sell(data=self.data_target, size=pos_size)
                return

        # ===== ENTRY LOGIC =====
        if pos_size == 0:
            # Golden Cross conditions
            if self.crossover[0] > 0:  # Fast MA crosses above Slow MA
                # Additional confirmations
                price_above_fast = current_price > self.fast_ma[0]
                volume_confirmation = current_volume > self.volume_ma[0]

                if price_above_fast and volume_confirmation:
                    # Calculate position size
                    cash = self.broker.getcash()
                    position_value = cash * self.params.stake_pct
                    size = int(position_value / current_price)

                    if size > 0:
                        self.log(f'GOLDEN CROSS: Buying {size} units at {current_price:.2f}')
                        self.log(f'  Price > Fast MA: {price_above_fast}')
                        self.log(f'  Volume > Avg: {volume_confirmation}')
                        self.order = self.buy(data=self.data_target, size=size)
                else:
                    self.dlog(f'GOLDEN CROSS but conditions not met: '
                             f'Price>FastMA={price_above_fast}, '
                             f'Volume>Avg={volume_confirmation}')

    def stop(self):
        """Called when backtest ends - print summary."""
        self.log('='*60)
        self.log('STRATEGY SUMMARY')
        self.log('='*60)
        self.log(f'Final Portfolio Value: £{self.broker.getvalue():,.2f}')
        self.log(f'Total Trades: {self.trades_count}')
        if self.trades_count > 0:
            win_rate = (self.wins / self.trades_count) * 100
            self.log(f'Wins: {self.wins} | Losses: {self.losses} | Win Rate: {win_rate:.1f}%')
        self.log(f'Parameters: Fast={self.params.fast_period}, '
                f'Slow={self.params.slow_period}, '
                f'Stop={self.params.stop_pct*100:.0f}%, '
                f'Target={self.params.target_pct*100:.0f}%')
        self.log('='*60)
