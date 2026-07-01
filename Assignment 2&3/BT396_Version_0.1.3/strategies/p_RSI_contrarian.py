# strategies/p_rsi_contrarian.py
#
# Portfolio RSI contrarian strategy (BT396-safe)
# ----------------------------------------------
# - Goes long when RSI < 50 − threshold, short when RSI > 50 + threshold.
# - Trades only selected feeds (1-based indices).
# - Uses BT396-safe overspend_guard + place_market() instead of raw order_target_size().

import backtrader as bt


class TeamStrategy(bt.Strategy):
    """Portfolio contrarian strategy that targets long when RSI < 50−threshold
    and short when RSI > 50+threshold on selected series (BT396-safe)."""

    params = dict(
        lookback=14,          # RSI window
        threshold=5.0,        # 0..50 band around 50
        series=None,          # 1-based feed indices to trade; default = all
        posSizes=None,        # per-feed sizes
        default_size=1.0,     # fallback
        printlog=False,
    )

    def __init__(self):
        self.datas_list = list(self.datas)
        nfeeds = len(self.datas_list)
        if nfeeds == 0:
            raise ValueError("No data feeds. Use --portfolio with a matching --data-glob.")

        # Validate threshold range
        if not (0 <= float(self.p.threshold) <= 50):
            raise ValueError("threshold must be between 0 and 50.")

        # Convert 1-based to 0-based indices
        if self.p.series is None:
            self.series_idx = list(range(nfeeds))
        else:
            self.series_idx = [i - 1 for i in self.p.series if 1 <= i <= nfeeds]
            if not self.series_idx:
                raise ValueError("params.series produced no valid indices for available feeds.")

        # Per-feed target sizes
        if self.p.posSizes is None:
            self.pos_sizes = [float(self.p.default_size)] * nfeeds
        else:
            if len(self.p.posSizes) != nfeeds:
                raise ValueError(
                    f"posSizes length {len(self.p.posSizes)} must match number of feeds {nfeeds}."
                )
            self.pos_sizes = [float(x) for x in self.p.posSizes]

        # Build RSI indicators
        self.rsi = [bt.indicators.RSI(d.close, period=int(self.p.lookback)) for d in self.datas_list]

    def log(self, txt, dt=None):
        if self.p.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            print(f"{dt} {txt}")

    def next(self):
        # Wait until enough bars for RSI
        if len(self) < int(self.p.lookback) + 2:
            return

        up_lvl = 50.0 + float(self.p.threshold)
        dn_lvl = 50.0 - float(self.p.threshold)

        intents = []  # collect (data, delta) for overspend_guard

        # ---  Determine targets per feed ---
        for i in self.series_idx:
            d = self.datas_list[i]
            r = float(self.rsi[i][0])

            # Contrarian signal: +1 long, -1 short, 0 flat
            if r > up_lvl:
                dir_signal = -1
            elif r < dn_lvl:
                dir_signal = +1
            else:
                dir_signal = 0

            target = dir_signal * self.pos_sizes[i]
            current = self.getposition(d).size
            delta = target - current

            if abs(delta) > 1e-8:
                intents.append((d, delta))

            if self.p.printlog:
                self.log(
                    f"[data[{i}]={d._name}] RSI={r:.2f} "
                    f"(>{up_lvl:.2f} short / <{dn_lvl:.2f} long) "
                    f"target={target:+.2f} current={current:+.2f} delta={delta:+.2f}"
                )

        # --- Run overspend guard before sending any orders ---
        if intents and not self.overspend_guard(intents):
            self.log("OVRSPEND: cancelling all market orders for today")
            return

        # --- Queue safe market orders for next-open fill ---
        for d, delta in intents:
            self.place_market(d, delta)
