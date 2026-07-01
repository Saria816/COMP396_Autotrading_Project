# strategies/p_mm_spread.py
#
# Portfolio "pseudo market making" strategy (BT396-safe)
# ------------------------------------------------------
# - Cancels yesterday’s still-open limit orders each morning.
# - If |position| > inventoryLimits → flatten to 0 using safe order_target_size().
# - Otherwise places one BUY and one SELL limit order per instrument per day.
# - Limit orders go through COMP396Base.place_limit1/2 so that framework
#   enforces per-side caps and rule compliance.

import backtrader as bt
import math


class TeamStrategy(bt.Strategy):
    """BT396-safe pseudo market-making strategy that places daily buy/sell limits
    within a spread unless inventory limits are breached."""

    params = dict(
        spreadPercentage=0.10,   # 10 % of yesterday’s range
        inventoryLimits=1000,    # scalar or list per feed
        quote_size=1.0,          # units per limit
        printlog=False,
    )

    def __init__(self):
        self.datas_list = list(self.datas)
        n = len(self.datas_list)
        if n == 0:
            raise ValueError("No data feeds. Use --portfolio with a matching --data-glob.")

        # Normalise inventoryLimits → list
        if isinstance(self.p.inventoryLimits, (list, tuple)):
            if len(self.p.inventoryLimits) != n:
                raise ValueError(
                    f"inventoryLimits length {len(self.p.inventoryLimits)} must match number of feeds {n}."
                )
            self.inv_limits = [float(x) for x in self.p.inventoryLimits]
        else:
            self.inv_limits = [float(self.p.inventoryLimits)] * n

        # Track outstanding limits to cancel next bar
        self.open_buy_orders = {d: None for d in self.datas_list}
        self.open_sell_orders = {d: None for d in self.datas_list}

    def log(self, txt, dt=None):
        if self.p.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            print(f"{dt.isoformat()} {txt}")

    def _cancel_if_open(self, o):
        """Cancel any still-open limit order safely."""
        if o is not None and o.status in [bt.Order.Submitted, bt.Order.Accepted]:
            try:
                self.cancel(o)
            except Exception:
                pass

    def next(self):
        # --- 1) Cancel yesterday’s outstanding limit orders ---
        for d in self.datas_list:
            self._cancel_if_open(self.open_buy_orders[d])
            self._cancel_if_open(self.open_sell_orders[d])
            self.open_buy_orders[d] = None
            self.open_sell_orders[d] = None

        # --- 2) For each feed, flatten or place new quotes ---
        for i, d in enumerate(self.datas_list):
            pos = self.getposition(d).size
            lim = self.inv_limits[i]

            # a) Flatten if over inventory limit
            if abs(pos) > lim:
                self.order_target_size(data=d, target=0)  # safe override in COMP396Base
                self.log(f"[data[{i}]] |pos|={abs(pos):.0f} > limit={lim:.0f} → flatten")
                continue

            # b) Need at least 2 bars to compute prior-day range
            if len(d) < 2:
                continue

            close_yday = float(d.close[-1])
            high_yday = float(d.high[-1])
            low_yday = float(d.low[-1])
            day_range = max(0.0, high_yday - low_yday)
            spread = float(self.p.spreadPercentage) * day_range
            half = spread * 0.5

            buy_px = close_yday - half
            sell_px = close_yday + half

            # sanity checks
            if not (math.isfinite(buy_px) and math.isfinite(sell_px)):
                continue

            qty = float(self.p.quote_size)
            if qty <= 0:
                continue

            # c) Place fresh limit orders via COMP396Base wrappers
            self.open_buy_orders[d] = self.place_limit1(d, size=+qty, price=buy_px)
            self.open_sell_orders[d] = self.place_limit2(d, size=-qty, price=sell_px)

            if self.p.printlog:
                self.log(
                    f"[data[{i}]] pos={pos:+.0f} lim={lim:.0f} "
                    f"close_yday={close_yday:.4f} rng={day_range:.4f} "
                    f"buy@{buy_px:.4f} sell@{sell_px:.4f} qty={qty}"
                )
