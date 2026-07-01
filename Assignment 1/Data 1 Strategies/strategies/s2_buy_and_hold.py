#!/usr/bin/env python3
"""
Strategy 2: Buy and Hold (Long-term Position Trading)

Target: Series 05 (Sustained uptrend pattern)
Type: Buy and Hold / Long-term Investment

Entry:
- Buy on first trading day with 100% of available capital

Exit:
- Hold until end of trading period (final day liquidation)

Position Sizing: 100% of portfolio value (single trade)

This strategy capitalizes on the sustained uptrend of Series 05 by 
simply buying and holding for the entire period, capturing the full
price appreciation with minimal complexity.
"""

import backtrader as bt


class BuyAndHold(bt.Strategy):
    """
    Buy and Hold Strategy for Series 05.

    This strategy takes advantage of the sustained uptrend by buying
    on the first day and holding until the end, capturing the full
    price appreciation of the asset.
    """

    params = (
        ('series_index', 4),      # Series 05 is at index 4 (0-based)
        ('debug', False),         # Debug logging
    )

    def __init__(self):
        """Initialize tracking variables."""
        self.data_target = self.datas[self.params.series_index]
        
        # Track if we've made our initial purchase
        self.bought = False
        self.entry_price = None
        self.entry_date = None
        
        # Track orders
        self.order = None
        
        # Performance tracking
        self.total_shares = 0

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
                self.entry_date = self.data_target.datetime.date(0)
                self.total_shares = order.executed.size
                self.bought = True

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f'ORDER CANCELED/MARGIN/REJECTED: {order.status}')

        self.order = None

    def next(self):
        """Main strategy logic executed on each bar."""
        # Skip if we have a pending order
        if self.order:
            return

        # Buy on first available day if we haven't bought yet
        if not self.bought:
            current_price = self.data_target.close[0]
            cash = self.broker.getcash()
            
            # Use all available cash (100% allocation)
            size = int(cash / current_price)
            
            if size > 0:
                self.log(f'BUY AND HOLD ENTRY: Buying {size} shares at {current_price:.2f}')
                self.log(f'  Total Investment: £{size * current_price:,.2f}')
                self.order = self.buy(data=self.data_target, size=size)
        
        # Optional: Log progress periodically (for debug)
        elif self.params.debug and self.bought:
            current_price = self.data_target.close[0]
            current_value = self.total_shares * current_price
            if self.entry_price:
                unrealized_pnl = ((current_price - self.entry_price) / self.entry_price) * 100
                self.dlog(f'HOLDING: Price={current_price:.2f}, '
                         f'Value=£{current_value:,.2f}, '
                         f'Unrealized P&L={unrealized_pnl:+.2f}%')

    def stop(self):
        """Called when backtest ends - print summary."""
        final_price = self.data_target.close[0]
        final_value = self.broker.getvalue()
        
        self.log('='*60)
        self.log('BUY AND HOLD STRATEGY SUMMARY')
        self.log('='*60)
        
        if self.entry_price and self.entry_date:
            holding_period = (self.data_target.datetime.date(0) - self.entry_date).days
            total_return = ((final_price - self.entry_price) / self.entry_price) * 100
            
            self.log(f'Entry Date: {self.entry_date}')
            self.log(f'Entry Price: £{self.entry_price:.2f}')
            self.log(f'Final Price: £{final_price:.2f}')
            self.log(f'Shares Held: {self.total_shares:,.0f}')
            self.log(f'Holding Period: {holding_period} days')
            self.log(f'Total Return: {total_return:+.2f}%')
            self.log(f'Final Portfolio Value: £{final_value:,.2f}')
        else:
            self.log('No trades executed')
            
        self.log('='*60)