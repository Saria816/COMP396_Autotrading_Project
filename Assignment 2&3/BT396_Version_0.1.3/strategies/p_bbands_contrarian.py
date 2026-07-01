# strategies/p_bbands_contrarian.py
#
# Bollinger Bands contrarian strategy adapted for BT396.
# All orders go through the COMP396Base safe order layer
# (overspend guard + buffered next-open execution).

import backtrader as bt

class TeamStrategy(bt.Strategy):
    """Portfolio Bollinger Bands contrarian strategy that targets long below the lower band
    and short above the upper band on selected series."""

    params = dict(
        lookback=20,          # Bollinger lookback window
        sdParam=2.0,          # standard deviation multiplier
        series=None,          # 1-based series indices to trade (e.g., [1,3,5,7,9])
        posSizes=None,        # list of per-series sizes (one per feed)
        default_size=1.0,     # fallback if posSizes not provided
        printlog=False,
    )

    def __init__(self):
        self.datas_list = list(self.datas)
        nfeeds = len(self.datas_list)
        if nfeeds == 0:
            raise ValueError("No data feeds provided. Use --portfolio with a matching --data-glob.")

        # Convert 1-based indices to 0-based
        if self.p.series is None:
            self.series_idx = list(range(nfeeds))
        else:
            self.series_idx = [i - 1 for i in self.p.series if 1 <= i <= nfeeds]
            if not self.series_idx:
                raise ValueError("params.series produced no valid indices for available feeds.")

        # Prepare per-feed target sizes
        if self.p.posSizes is None:
            self.pos_sizes = [float(self.p.default_size)] * nfeeds
        else:
            if len(self.p.posSizes) != nfeeds:
                raise ValueError(
                    f"posSizes length {len(self.p.posSizes)} must match number of feeds {nfeeds}."
                )
            self.pos_sizes = [float(x) for x in self.p.posSizes]

        # Build Bollinger indicators for each feed
        self.bbands = []
        for d in self.datas_list:
            bb = bt.indicators.BollingerBands(
                d.close, period=int(self.p.lookback), devfactor=float(self.p.sdParam)
            )
            self.bbands.append(bb)

    def log(self, txt, dt=None):
        if self.p.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            print(f"{dt.isoformat()} {txt}")

    def next(self):
        # Wait until enough data for Bollinger bands
        if len(self) <= int(self.p.lookback):
            return

        intents = []  # collect (data, target_diff) for overspend_guard

        # First pass: compute desired targets and deltas
        for i in self.series_idx:
            d = self.datas_list[i]
            bb = self.bbands[i]

            close = float(d.close[0])
            up = float(bb.lines.top[0])
            dn = float(bb.lines.bot[0])

            # contrarian logic
            target = 0.0
            if close < dn:
                target = +self.pos_sizes[i]
            elif close > up:
                target = -self.pos_sizes[i]

            # current position
            current = self.getposition(d).size
            delta = target - current
            if abs(delta) > 1e-8:  # avoid zero deltas
                intents.append((d, delta))

            if self.p.printlog:
                self.log(
                    f"[data[{i}]] close={close:.4f} dn={dn:.4f} up={up:.4f} "
                    f"→ target={target:.2f} (current={current:.2f})"
                )

        # Run overspend guard for all market intents
        if intents and not self.overspend_guard(intents):
            self.log("OVRSPEND: cancelling ALL market orders for today")
            return

        # Place market orders for each instrument delta
        for d, delta in intents:
            self.place_market(d, delta)
