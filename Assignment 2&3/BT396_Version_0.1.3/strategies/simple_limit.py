# strategies/simple_limit.py
#
# Simple daily limit-quote strategy (BT396-safe)
# ----------------------------------------------
# - Cancels previous orders automatically via BT396 wrapper.
# - Computes daily bid/ask around a chosen center.
# - Flattens positions if inventory exceeds limits.
# - Places limit orders through place_limit1()/place_limit2() wrappers.
# - Optionally rotates which series trades each day.

import backtrader as bt
from math import isfinite


class TeamStrategy(bt.Strategy):
    """
    BT396 market-making style strategy.

    Each day:
      • spread = spreadPercentage * range_source(High - Low)
      • BUY limit  at center − 0.5 * spread
      • SELL limit at center + 0.5 * spread
      • If |position| > inventoryLimits → flatten (market)
      • Acts on all or rotating series.

    Framework provides: place_limit1/2, place_market, overspend_guard.
    """

    params = dict(
        size=1,
        spreadPercentage=0.30,
        inventoryLimits=50,
        center_on="open",          # 'open' | 'prev_close'
        range_source="yesterday",  # 'yesterday' | 'today'
        series_mode="all",         # 'all' | 'rotate'
        rotate_start=0,
        log_debug=True,
    )

    def __init__(self):
        self._last_clock_date = None
        self._day_index = 0  # for rotation across series

    # --- helpers -------------------------------------------------------------
    def log(self, txt, dt=None):
        """Conditional diagnostic logging."""
        if self.p.log_debug:
            dt = dt or self.datas[0].datetime.date(0)
            print(f"{dt} {txt}")

    def _targets_today(self):
        """Select which feeds to act on today based on mode."""
        if self.p.series_mode.lower() == "rotate":
            i = (self.p.rotate_start + self._day_index) % len(self.datas)
            return [self.datas[i]]
        return list(self.datas)

    def _center_price(self, d):
        if self.p.center_on.lower() == "prev_close":
            if len(d) < 2:
                return None
            return float(d.close[-1])
        return float(d.open[0])

    def _range_value(self, d):
        if self.p.range_source.lower() == "today":
            hi, lo = float(d.high[0]), float(d.low[0])
        else:
            if len(d) < 2:
                return None
            hi, lo = float(d.high[-1]), float(d.low[-1])
        rng = hi - lo
        return rng if isfinite(rng) and rng > 0 else None

    # --- main loop -----------------------------------------------------------
    def next(self):
        # Run once per calendar day using data0 as clock
        clock_today = self.datas[0].datetime.date(0)
        if self._last_clock_date == clock_today:
            return
        self._last_clock_date = clock_today
        self._day_index += 1

        self.log(f"SimpleLimit.next() clock={clock_today} mode={self.p.series_mode}")

        # Verify that wrappers exist
        required = ("place_limit1", "place_limit2", "place_market", "overspend_guard")
        if not all(hasattr(self, n) for n in required):
            self.log("FATAL: wrapper not injected; aborting today")
            return

        targets = self._targets_today()

        for d in targets:
            # --- 0) Inventory control ---
            pos = self.getposition(d).size
            if abs(pos) > self.p.inventoryLimits:
                delta = -pos
                if delta > 0 and not self.overspend_guard([(d, delta)]):
                    self.log(f"{getattr(d, '_name', 'series')} OVRSPEND: skip flatten BUY")
                else:
                    self.place_market(d, delta)
                    self.log(f"{getattr(d, '_name', 'series')} flatten delta={delta:+.2f}")

            # --- 1) Compute today's quote levels ---
            center = self._center_price(d)
            rng = self._range_value(d)
            if center is None or rng is None:
                continue

            spread = float(self.p.spreadPercentage) * rng
            buy_px = round(center - 0.5 * spread, 6)
            sell_px = round(center + 0.5 * spread, 6)

            # --- 2) Optional overspend check for BUY limit ---
            if not self.overspend_guard([(d, +abs(self.p.size))]):
                self.log(f"{getattr(d,'_name','series')} OVRSPEND: skip BUY limit")
            else:
                self.place_limit1(d, size=+abs(self.p.size), price=buy_px)

            # SELL limit (no cash guard needed)
            self.place_limit2(d, size=-abs(self.p.size), price=sell_px)

            # --- 3) Log diagnostics ---
            lo0 = float(d.low[0])
            hi0 = float(d.high[0])
            self.log(
                f"{getattr(d, '_name', 'series')} rng={rng:.4f} spread={spread:.4f} center={center:.4f} "
                f"buy@{buy_px:.4f} sell@{sell_px:.4f} "
                f"lo0={lo0:.4f} hi0={hi0:.4f} "
                f"touch: BUY={lo0 <= buy_px} SELL={hi0 >= sell_px}"
            )

    # --- optional fill logging ----------------------------------------------
    def notify_order(self, order):
        if order.status == order.Completed:
            side = "BUY" if order.isbuy() else "SELL"
            self.log(
                f"{side} filled @{order.executed.price:.6f} "
                f"size={order.executed.size:+.2f} value={order.executed.value:.2f}"
            )
