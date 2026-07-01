# strategies/p_short5_long5.py
#
# BT396-safe version.
# -------------------
# - Day 1: SHORT series 1–5 equally so total short exposure = leverage.
# - Day 2: LONG series 6–10 equally using (cash − cash_buffer).
# - Uses COMP396Base.place_market() and overspend_guard() to comply with the framework.

import backtrader as bt


class TeamStrategy(bt.Strategy):
    # Two-phase leveraged portfolio: short series 1–5 on day one, then go long
    # series 6–10 on day two. BT396-safe version with overspend guard.

    params = dict(
        leverage=40_000_000,   # total short exposure across series 1–5
        cash_buffer=1_000_000, # reserve cash before long phase
        printlog=False,
    )

    def __init__(self):
        self._did_shorts = False
        self._did_longs = False
        self.datas_list = list(self.datas)

        # Require ≥10 data feeds
        if len(self.datas_list) < 10:
            raise ValueError(
                f"p_short5_long5 expects at least 10 data feeds; got {len(self.datas_list)}. "
                "Run with --portfolio and a glob that matches 10 CSV files."
            )

    def log(self, txt, dt=None):
        if self.p.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            print(f"{dt} {txt}")

    def next(self):
        # --- Phase 1: Day 1 SHORTS across 1–5 ---
        if not self._did_shorts:
            exposure_total = float(self.p.leverage)
            per_series_exposure = exposure_total / 5.0
            intents = []

            for i in range(5):
                d = self.datas_list[i]
                opx = float(d.open[0])
                if opx <= 0:
                    continue
                size = - per_series_exposure / opx  # negative = short
                intents.append((d, size))

            # Cash forecast check before placing all shorts
            if not self.overspend_guard(intents):
                self.log("OVRSPEND: cancelling short basket (Day 1)")
                return

            for i, (d, size) in enumerate(intents):
                self.place_market(d, size)
                self.log(f"SHORT data[{i}] @open≈{float(d.open[0]):.2f} size={size:.2f}")

            self._did_shorts = True
            return  # next day handles longs

        # --- Phase 2: Day 2 LONGS across 6–10 ---
        if self._did_shorts and not self._did_longs:
            cash = float(self.broker.getcash())
            to_spend = max(0.0, cash - float(self.p.cash_buffer))
            per_series_exposure = to_spend / 5.0 if to_spend > 0 else 0.0

            intents = []
            for i in range(5, 10):
                d = self.datas_list[i]
                opx = float(d.open[0])
                if opx <= 0:
                    continue
                size = per_series_exposure / opx  # positive = long
                intents.append((d, size))

            if not self.overspend_guard(intents):
                self.log("OVRSPEND: cancelling long basket (Day 2)")
                return

            for i, (d, size) in enumerate(intents, start=5):
                self.place_market(d, size)
                self.log(f"LONG  data[{i}] @open≈{float(d.open[0]):.2f} size={size:.2f}")

            self._did_longs = True
            return

        # --- Phase 3: Hold thereafter ---
        return
