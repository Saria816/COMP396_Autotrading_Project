# strategies/p_bbands_contrarian_diag.py
#
# Diagnostic Bollinger Bands variant with holding period and safe BT396 order handling.
# Uses overspend guard + place_market() for all trades.

import backtrader as bt


class TeamStrategy(bt.Strategy):
    """Diagnostic variant of Bollinger Bands with holding period that logs decisions
    and sends heartbeat trades for visibility. All orders go through COMP396Base-safe
    functions (overspend_guard + place_market)."""

    params = dict(
        lookback=20,
        sdParam=2.0,
        holdPeriod=5,
        series=None,         # 1-based
        posSizes=None,       # len == n_feeds
        default_size=1.0,
        printlog=True,       # always on for diagnostics
        diag_heartbeat=True  # place a tiny test trade so we can see activity
    )

    def __init__(self):
        self.datas_list = list(self.datas)
        nfeeds = len(self.datas_list)
        if nfeeds == 0:
            raise ValueError("No data feeds in Cerebro.")

        # Map 1-based → 0-based indices
        if self.p.series is None:
            self.series_idx = list(range(nfeeds))
        else:
            self.series_idx = [i - 1 for i in self.p.series if 1 <= i <= nfeeds]
            if not self.series_idx:
                raise ValueError("params.series produced no valid indices.")

        # Per-feed sizes
        if self.p.posSizes is None:
            self.pos_sizes = [float(self.p.default_size)] * nfeeds
        else:
            if len(self.p.posSizes) != nfeeds:
                raise ValueError("posSizes len must match number of feeds.")
            self.pos_sizes = [float(x) for x in self.p.posSizes]

        # Bollinger indicators
        self.bbands = []
        for d in self.datas_list:
            bb = bt.indicators.BollingerBands(
                d.close, period=int(self.p.lookback), devfactor=float(self.p.sdParam)
            )
            self.bbands.append(bb)

        # Holding counters per selected series
        self.count = {i: 0 for i in self.series_idx}

        # Diagnostic printout
        print("\n=== Strategy wired ===")
        print(f"Class: {self.__class__.__name__}")
        print(f"Feeds: {len(self.datas_list)} → {[d._name for d in self.datas_list]}")
        print(f"Selected series (0-based): {self.series_idx}")
        for k, v in self.p._getitems():
            print(f"  {k}: {v}")
        print("======================\n")

    def _log(self, msg):
        dt = self.datas[0].datetime.date(0)
        print(f"{dt} {msg}")

    def next(self):
        # --- 1) Optional heartbeat trade for diagnostics ---
        if (
            self.p.diag_heartbeat
            and len(self) == int(self.p.lookback) + 1
            and self.series_idx
        ):
            d0 = self.datas_list[self.series_idx[0]]
            self._log("[HEARTBEAT] submitting test buy size=0.1")
            # Use the framework-safe place_market() instead of raw order_target_size()
            if self.overspend_guard([(d0, 0.1)]):
                self.place_market(d0, 0.1)
            else:
                self._log("OVRSPEND guard tripped on heartbeat order")

        # Skip until enough bars for Bollinger bands
        if len(self) <= int(self.p.lookback):
            return

        # --- 2) Core Bollinger + holding-period logic ---
        for i in self.series_idx:
            d = self.datas_list[i]
            bb = self.bbands[i]

            close = float(d.close[0])
            up = float(bb.lines.top[0])
            dn = float(bb.lines.bot[0])
            size_base = self.pos_sizes[i]

            # Raw contrarian signal
            if close < dn:
                dir_signal = +1
            elif close > up:
                dir_signal = -1
            else:
                dir_signal = 0

            curr_pos = self.getposition(d).size
            self._log(
                f"[data[{i}]={d._name}] close={close:.4f} dn={dn:.4f} up={up:.4f} "
                f"raw_dir={dir_signal:+d} curr_pos={curr_pos:.2f}"
            )

            # Holding-period counting
            c = self.count[i]
            if dir_signal == +1:
                if c < 0:
                    c = +1
                elif c == self.p.holdPeriod:
                    dir_signal, c = 0, 0
                else:
                    c = c + 1 if c >= 0 else +1
            elif dir_signal == -1:
                if c > 0:
                    c = -1
                elif c == -self.p.holdPeriod:
                    dir_signal, c = 0, 0
                else:
                    c = c - 1 if c <= 0 else -1
            else:
                c = 0
            self.count[i] = c

            # Target position and delta
            target = float(dir_signal) * float(size_base)
            delta = float(target) - float(curr_pos)

            if abs(delta) > 1e-8:
                self._log(
                    f"[data[{i}]={d._name}] NEW target={target:.2f} (count={c:+d}) → sending order"
                )
                if self.overspend_guard([(d, delta)]):
                    self.place_market(d, delta)
                else:
                    self._log(f"OVRSPEND guard tripped on {d._name}; skipping")
