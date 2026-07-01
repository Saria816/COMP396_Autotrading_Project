# strategies/bbands_holding_period.py
#
# Bollinger Bands contrarian strategy with a per-series max holding period.
# - Trades ONLY the 1-based series in params.series (like the R version).
# - If Close < lower band => LONG; if Close > upper band => SHORT; else => FLAT.
# - Tracks how many bars we’ve been in a trade and exits when the count hits holdPeriod.
#
# Params
#   lookback:    int, Bollinger window
#   sdParam:     float, stddev multiplier
#   holdPeriod:  int, max number of bars to remain in a position
#   series:      list[int], 1-based series indices to trade; default = all feeds
#   posSizes:    list[float], per-feed position sizes (len == n_feeds)
#   default_size:float, used if posSizes is None
#   printlog:    bool, verbose per-bar logging
#
# Notes
# - Uses order_target_size(...) → market orders at next bar with framework slippage.
# - Counting logic mirrors the R version’s intent (fixing the accidental '==' assignments).

import backtrader as bt


class TeamStrategy(bt.Strategy):
    """Bollinger Bands strategy that opens positions on band breaches and holds them for a fixed number of days."""
    params = dict(
        lookback=20,
        sdParam=2.0,
        holdPeriod=5,
        series=None,          # 1-based list; None = all series
        posSizes=None,        # len == n_feeds; else fallback to default_size
        default_size=1.0,
        printlog=False,
    )

    def __init__(self):
        self.datas_list = list(self.datas)
        nfeeds = len(self.datas_list)
        if nfeeds == 0:
            raise ValueError("No data feeds. Provide --data-glob/--data-dir to the harness.")

        # Convert 1-based series → 0-based indices
        if self.p.series is None:
            self.series_idx = list(range(nfeeds))
        else:
            self.series_idx = [i - 1 for i in self.p.series if 1 <= i <= nfeeds]
            if not self.series_idx:
                raise ValueError("params.series produced no valid indices for available feeds.")

        # Position sizes (per feed)
        if self.p.posSizes is None:
            self.pos_sizes = [float(self.p.default_size)] * nfeeds
        else:
            if len(self.p.posSizes) != nfeeds:
                raise ValueError(
                    f"posSizes length {len(self.p.posSizes)} must match number of feeds {nfeeds}."
                )
            self.pos_sizes = [float(x) for x in self.p.posSizes]

        # Bollinger indicators for each feed (we’ll consult only selected ones)
        self.bbands = []
        for d in self.datas_list:
            bb = bt.indicators.BollingerBands(
                d.close, period=int(self.p.lookback), devfactor=float(self.p.sdParam)
            )
            self.bbands.append(bb)

        # Per-selected-series holding counters: feed_index -> int
        # Convention:
        #   0 = flat last bar
        #  >0 = long for 'count' bars
        #  <0 = short for 'count' bars
        self.count = {i: 0 for i in self.series_idx}

    # Optional: echo params at start
    def start(self):
        if self.p.printlog:
            print(f"[{self.__class__.__name__}] parameters:")
            for k, v in self.p._getitems():
                print(f"  {k}: {v}")

    def log(self, txt, dt=None):
        if self.p.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            print(f"{dt.isoformat()} {txt}")

    def next(self):
        # Need enough history for Bollinger window
        if len(self) <= int(self.p.lookback):
            return

        for i in self.series_idx:
            d = self.datas_list[i]
            bb = self.bbands[i]

            close = float(d.close[0])
            up = float(bb.lines.top[0])
            dn = float(bb.lines.bot[0])
            size_base = self.pos_sizes[i]

            # Raw direction: +1 long, -1 short, 0 flat
            dir_signal = 0
            if close < dn:
                dir_signal = +1
            elif close > up:
                dir_signal = -1
            else:
                dir_signal = 0

            # Holding-period logic (R port, with the intended assignments)
            c = self.count[i]

            if dir_signal == +1:
                if c < 0:
                    # was short, flip to long and start count at +1
                    c = +1
                elif c == self.p.holdPeriod:
                    # reached max long hold → force flat
                    dir_signal = 0
                    c = 0
                else:
                    # continue/increment long count (including 0 → 1)
                    c = c + 1 if c >= 0 else +1

            elif dir_signal == -1:
                if c > 0:
                    # was long, flip to short and start count at -1
                    c = -1
                elif c == -self.p.holdPeriod:
                    # reached max short hold → force flat
                    dir_signal = 0
                    c = 0
                else:
                    # continue/decrement short count (including 0 → -1)
                    c = c - 1 if c <= 0 else -1

            else:
                # No signal → reset count
                c = 0

            self.count[i] = c

            # Target position for this instrument
            target = float(dir_signal) * float(size_base)
            curr = self.getposition(d).size
            delta = float(target) - float(curr)
            if abs(delta) > 0:
                # (optional) single-instrument overspend check
                if self.overspend_guard([(d, delta)]):
                    self.place_market(d, delta)  # goes through COMP396 buffer + flush correctly
                else:
                    self.log(f"OVRSPEND guard tripped on {d._name}; skipping")

            if self.p.printlog:
                self.log(
                    f"[data[{i}]] close={close:.4f} dn={dn:.4f} up={up:.4f} "
                    f"dir={dir_signal:+d} count={c:+d} target={target:.2f}"
                )
