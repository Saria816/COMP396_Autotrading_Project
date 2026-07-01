# ==============================================================
# strategies/team2.py
# --------------------------------------------------------------
# Combined Team Strategy based on BT396 Framework
#
# Portfolio Allocation: trend asset 70% + other asset 30% (Equal weight within each group)
#
# Trend Assets (14% each, 70% total):
#   series_1: breakout strategy
#   series_3: above_ma strategy
#   series_4: ma_crossover strategy
#   series_6: above_ma strategy
#   series_9: above_ma strategy
#
# Mean Reversion Assets (6% each, 24% total):
#   series_2: zscore strategy
#   series_7: bollinger strategy
#   series_8: rsi strategy
#   series_10: zscore strategy
#
# Short Asset (6% total):
#   series_5: rsi_short strategy
#
# ==============================================================
import backtrader as bt


class TeamStrategy(bt.Strategy):
    """
    Combined strategy integrating 3 sub-strategies:
    - Trend/Momentum for series_1, 3, 4, 6, 9
    - Mean Reversion for series_2, 7, 8, 10
    - Short for series_5
    """

    params = dict(
        printlog=False,
        # Trend asset allocation (70% total)
        trend_allocation=0.70,
        # Other asset allocation (30% total)
        other_allocation=0.30,
    )

    def __init__(self):
        # ============================================================
        # Asset grouping and weights
        # ============================================================
        self.trend_assets = ['series_1', 'series_3', 'series_4', 'series_6', 'series_9']
        self.mr_assets = ['series_2', 'series_7', 'series_8', 'series_10']
        self.short_assets = ['series_5']

        n_trend = len(self.trend_assets)
        n_other = len(self.mr_assets) + len(self.short_assets)

        # Calculate per-asset weights
        self.trend_weight = self.p.trend_allocation / n_trend  # 14% each
        self.other_weight = self.p.other_allocation / n_other  # 6% each

        # ============================================================
        # Map data feeds by name
        # ============================================================
        self.data_map = {}
        for d in self.datas:
            self.data_map[d._name] = d

        # ============================================================
        # Strategy parameters for each asset
        # ============================================================
        self.asset_params = {
            # Trend assets
            'series_1': {'type': 'trend', 'strategy': 'breakout', 'lookback': 25},
            'series_3': {'type': 'trend', 'strategy': 'above_ma', 'ma_period': 20, 'confirm_days': 3},
            'series_4': {'type': 'trend', 'strategy': 'ma_crossover', 'fast': 10, 'slow': 30},
            'series_6': {'type': 'trend', 'strategy': 'above_ma', 'ma_period': 15, 'confirm_days': 2},
            'series_9': {'type': 'trend', 'strategy': 'above_ma', 'ma_period': 15, 'confirm_days': 2},
            # Mean reversion assets
            'series_2': {'type': 'mr', 'strategy': 'zscore', 'lookback': 20, 'entry_z': 2.0, 'exit_z': 0.0},
            'series_7': {'type': 'mr', 'strategy': 'bollinger', 'lookback': 15, 'std_mult': 2.0},
            'series_8': {'type': 'mr', 'strategy': 'rsi', 'rsi_period': 14, 'oversold': 30},
            'series_10': {'type': 'mr', 'strategy': 'zscore', 'lookback': 25, 'entry_z': 2.5, 'exit_z': 0.0},
            # Short asset
            'series_5': {'type': 'short', 'rsi_period': 7, 'overbought': 75, 'oversold': 40},
        }

        # ============================================================
        # Create indicators for each asset
        # ============================================================
        self.indicators = {}

        for name, d in self.data_map.items():
            params = self.asset_params.get(name, {})
            self.indicators[name] = {}

            if params.get('type') == 'trend':
                strategy = params.get('strategy')

                if strategy == 'breakout':
                    lookback = params.get('lookback', 25)
                    self.indicators[name]['highest'] = bt.indicators.Highest(
                        d.close, period=lookback)
                    self.indicators[name]['lowest'] = bt.indicators.Lowest(
                        d.close, period=lookback)

                elif strategy == 'above_ma':
                    ma_period = params.get('ma_period', 20)
                    self.indicators[name]['sma'] = bt.indicators.SMA(
                        d.close, period=ma_period)

                elif strategy == 'ma_crossover':
                    fast = params.get('fast', 10)
                    slow = params.get('slow', 30)
                    self.indicators[name]['fast_ma'] = bt.indicators.SMA(
                        d.close, period=fast)
                    self.indicators[name]['slow_ma'] = bt.indicators.SMA(
                        d.close, period=slow)

            elif params.get('type') == 'mr':
                strategy = params.get('strategy')

                if strategy == 'zscore':
                    lookback = params.get('lookback', 20)
                    self.indicators[name]['sma'] = bt.indicators.SMA(
                        d.close, period=lookback)
                    self.indicators[name]['std'] = bt.indicators.StdDev(
                        d.close, period=lookback)

                elif strategy == 'bollinger':
                    lookback = params.get('lookback', 15)
                    std_mult = params.get('std_mult', 2.0)
                    self.indicators[name]['bb'] = bt.indicators.BollingerBands(
                        d.close, period=lookback, devfactor=std_mult)

                elif strategy == 'rsi':
                    rsi_period = params.get('rsi_period', 14)
                    self.indicators[name]['rsi'] = bt.indicators.RSI(
                        d.close, period=rsi_period)

            elif params.get('type') == 'short':
                rsi_period = params.get('rsi_period', 7)
                self.indicators[name]['rsi'] = bt.indicators.RSI(
                    d.close, period=rsi_period)

        # Track confirmation days for above_ma strategy
        self.above_ma_count = {name: 0 for name in self.trend_assets}

        # Track previous MA values for crossover detection
        self.prev_fast_ma = {}
        self.prev_slow_ma = {}

    def log(self, txt, dt=None):
        if self.p.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            print(f"{dt} {txt}")

    def get_portfolio_value(self):
        """Calculate current portfolio value"""
        return self.broker.getvalue()

    def get_target_value(self, asset_name):
        """Get target position value for an asset"""
        portfolio_value = self.get_portfolio_value()

        if asset_name in self.trend_assets:
            return portfolio_value * self.trend_weight
        else:
            return portfolio_value * self.other_weight

    # ============================================================
    # Signal generation methods
    # ============================================================

    def get_trend_signal(self, name, d):
        """Generate trend strategy signal"""
        params = self.asset_params[name]
        strategy = params.get('strategy')
        ind = self.indicators[name]

        if strategy == 'breakout':
            lookback = params.get('lookback', 25)
            if len(d) < lookback + 1:
                return 0

            # Get previous bar's high/low (not including current bar)
            prev_high = ind['highest'][-1]
            prev_low = ind['lowest'][-1]

            if d.close[0] >= prev_high:
                return 1  # Breakout up - buy
            elif d.close[0] <= prev_low:
                return -1  # Breakout down - sell

        elif strategy == 'above_ma':
            ma_period = params.get('ma_period', 20)
            confirm_days = params.get('confirm_days', 3)

            if len(d) < ma_period + confirm_days:
                return 0

            sma = ind['sma'][0]

            # Count consecutive days above MA
            if d.close[0] > sma:
                self.above_ma_count[name] += 1
            else:
                self.above_ma_count[name] = 0

            # Buy signal: confirm_days consecutive days above MA
            if self.above_ma_count[name] >= confirm_days:
                return 1
            # Sell signal: price below MA
            elif d.close[0] < sma:
                return -1

        elif strategy == 'ma_crossover':
            slow = params.get('slow', 30)

            if len(d) < slow + 1:
                return 0

            fast_ma = ind['fast_ma'][0]
            slow_ma = ind['slow_ma'][0]

            prev_fast = self.prev_fast_ma.get(name, fast_ma)
            prev_slow = self.prev_slow_ma.get(name, slow_ma)

            # Golden cross - buy
            if fast_ma > slow_ma and prev_fast <= prev_slow:
                signal = 1
            # Death cross - sell
            elif fast_ma < slow_ma and prev_fast >= prev_slow:
                signal = -1
            else:
                signal = 0

            # Update previous values
            self.prev_fast_ma[name] = fast_ma
            self.prev_slow_ma[name] = slow_ma

            return signal

        return 0

    def get_mr_signal(self, name, d):
        """Generate mean reversion strategy signal"""
        params = self.asset_params[name]
        strategy = params.get('strategy')
        ind = self.indicators[name]

        if strategy == 'zscore':
            lookback = params.get('lookback', 20)
            entry_z = params.get('entry_z', 2.0)
            exit_z = params.get('exit_z', 0.0)

            if len(d) < lookback:
                return 0

            sma = ind['sma'][0]
            std = ind['std'][0]

            if std < 1e-10:
                return 0

            zscore = (d.close[0] - sma) / std

            # Oversold - buy
            if zscore < -entry_z:
                return 1
            # Mean reversion complete - sell
            elif zscore > exit_z:
                return -1

        elif strategy == 'bollinger':
            lookback = params.get('lookback', 15)

            if len(d) < lookback:
                return 0

            bb = ind['bb']
            lower = bb.lines.bot[0]
            mid = bb.lines.mid[0]

            # Below lower band - buy
            if d.close[0] < lower:
                return 1
            # Above middle band - sell
            elif d.close[0] > mid:
                return -1

        elif strategy == 'rsi':
            rsi_period = params.get('rsi_period', 14)
            oversold = params.get('oversold', 30)

            if len(d) < rsi_period + 1:
                return 0

            rsi = ind['rsi'][0]

            # Oversold - buy
            if rsi < oversold:
                return 1
            # RSI above 50 - sell
            elif rsi > 50:
                return -1

        return 0

    def get_short_signal(self, name, d):
        """Generate short strategy signal"""
        params = self.asset_params[name]
        rsi_period = params.get('rsi_period', 7)
        overbought = params.get('overbought', 75)
        oversold = params.get('oversold', 40)

        if len(d) < rsi_period + 1:
            return 0

        rsi = self.indicators[name]['rsi'][0]
        position = self.getposition(d).size

        # No position - check for short entry
        if position == 0:
            if rsi > overbought:
                return -2  # Short signal
        # In short position - check for exit
        elif position < 0:
            if rsi < oversold or rsi < 50:
                return 1  # Cover signal

        return 0

    # ============================================================
    # Main trading logic
    # ============================================================

    def next(self):
        # Process each asset
        for name, d in self.data_map.items():
            params = self.asset_params.get(name, {})
            asset_type = params.get('type')

            if not asset_type:
                continue

            position = self.getposition(d).size
            target_value = self.get_target_value(name)
            current_price = d.close[0]

            # Generate signal based on asset type
            if asset_type == 'trend':
                signal = self.get_trend_signal(name, d)
            elif asset_type == 'mr':
                signal = self.get_mr_signal(name, d)
            elif asset_type == 'short':
                signal = self.get_short_signal(name, d)
            else:
                signal = 0

            # Buy signal and no long position at present
            if signal == 1 and position <= 0:
                # Buy signal - close short first if any
                if position < 0:
                    # Cover short position
                    size = -position
                    if not self.overspend_guard([(d, size)]):
                        self.log(f"OVERSPEND: Cannot cover {name}")
                        continue
                    self.place_market(d, size)
                    self.log(f"[{name}] COVER short size={size:.2f}")

                # Calculate the target position quantity: target amount × 95% / current price
                target_size = int(target_value * 0.95 / current_price)
                if target_size > 0:
                    # Overspending check: Ensure sufficient cash
                    if not self.overspend_guard([(d, target_size)]):
                        self.log(f"OVERSPEND: Cannot buy {name}")
                        continue
                    self.place_market(d, target_size)
                    self.log(f"[{name}] BUY size={target_size:.2f}")

            elif signal == -1 and position > 0:
                # Sell signal - close long position
                self.place_market(d, -position)
                self.log(f"[{name}] SELL size={position:.2f}")

            elif signal == -2 and position >= 0:
                # Short signal
                if position > 0:
                    # Close long first
                    self.place_market(d, -position)
                    self.log(f"[{name}] SELL (before short) size={position:.2f}")

                # Open short position
                target_size = int(target_value * 0.95 / current_price)
                if target_size > 0:
                    self.place_market(d, -target_size)
                    self.log(f"[{name}] SHORT size={target_size:.2f}")

    def notify_order(self, order):
        if not self.p.printlog:
            return

        d = order.data
        st = order.getstatusname()

        if order.status == order.Completed:
            side = "BUY" if order.isbuy() else "SELL"
            self.log(
                f"[{d._name}] {side} filled "
                f"@{order.executed.price:.4f} "
                f"size={order.executed.size:+.2f} "
                f"value={order.executed.value:.2f}"
            )
        elif order.status in (order.Canceled, order.Margin, order.Rejected):
            self.log(f"[{d._name}] ORDER {st.upper()}")
