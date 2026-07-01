# strategies/condpr.py
#
# Conditional-Probability Direction Strategy (BT396-safe, fixed timing)
# ---------------------------------------------------------------------
# - Flattens positions at the *start* of each day (based on yesterday’s state)
# - Opens new trades the *next* day using response_to_up/response_to_dn
# - Avoids cancelling itself by staggering flatten and re-entry logic.
#
#
# python main.py --strategy condpr \
#   --param response_to_up=[1,1,1,1,1,-1,-1,-1,-1,-1] \
#   --param response_to_dn=[-1,-1,-1,-1,-1,1,1,1,1,1] \
#   --param printlog=True \
#   --data-dir ./DATA/PART1
#
#

import backtrader as bt


class TeamStrategy(bt.Strategy):
    # Conditional-probability direction strategy (BT396-safe, fixed timing).""

    params = dict(
        response_to_up=None,
        response_to_dn=None,
        stake_policy="max_over_close",  # "fixed" or "max_over_close"
        fixed_stake=1.0,
        printlog=False,
    )

    def log(self, txt):
        if self.p.printlog and len(self.datas) > 0:
            dt = self.datas[0].datetime.date(0)
            print(f"{dt} | {txt}")

    def start(self):
        n = len(self.datas)
        if n == 0:
            raise ValueError("No data feeds loaded for condpr strategy.")

        # Ensure response arrays exist and are correct length
        if self.p.response_to_up is None:
            self.p.response_to_up = [0] * n
        if self.p.response_to_dn is None:
            self.p.response_to_dn = [0] * n
        if len(self.p.response_to_up) < n:
            self.p.response_to_up += [0] * (n - len(self.p.response_to_up))
        if len(self.p.response_to_dn) < n:
            self.p.response_to_dn += [0] * (n - len(self.p.response_to_dn))

        # Flag to track daily phase: flatten first, then trade next day
        self._flatten_phase = True

        self.log(f"Initialised condpr strategy with {n} feeds.")

    def _stake(self, d):
        if self.p.stake_policy == "fixed":
            return float(self.p.fixed_stake)
        close_px = float(d.close[0])
        if close_px <= 0:
            return 0.0
        closes_now = [float(di.close[0]) for di in self.datas if len(di)]
        return max(closes_now) / close_px

    def next(self):
        # --- Phase 1: Flatten yesterday’s positions ---
        if self._flatten_phase:
            intents = []
            for d in self.datas:
                pos = self.getposition(d).size
                if pos != 0:
                    intents.append((d, -pos))
            if intents:
                if not self.overspend_guard(intents):
                    self.log("OVRSPEND: skipping flatten basket")
                else:
                    for d, delta in intents:
                        self.place_market(d, delta)
                        self.log(f"{getattr(d, '_name', 'series')} FLATTEN {delta:+.2f}")
            # Switch to trading phase for next bar
            self._flatten_phase = False
            return

        # --- Phase 2: Place new trades based on yesterday’s move ---
        new_intents = []
        for i, d in enumerate(self.datas):
            if len(d) < 2:
                continue
            went_up_yday = float(d.close[-1]) > float(d.open[-1])
            resp = self.p.response_to_up[i] if went_up_yday else self.p.response_to_dn[i]
            if resp == 0:
                continue

            qty = self._stake(d)
            if qty <= 0:
                continue

            signed = qty if resp > 0 else -qty
            new_intents.append((d, signed))

        if new_intents and not self.overspend_guard(new_intents):
            self.log("OVRSPEND: skipping new entries")
            return

        for d, qty in new_intents:
            self.place_market(d, qty)
            self.log(f"{getattr(d, '_name', 'series')} NEW trade size={qty:+.2f}")

        # Switch back to flatten phase for next bar
        self._flatten_phase = True

    def notify_order(self, order):
        if order.status == order.Completed:
            side = "BUY" if order.isbuy() else "SELL"
            self.log(
                f"{getattr(order.data, '_name', 'series')} "
                f"{side} filled size={order.executed.size:+.2f} @ {order.executed.price:.2f}"
            )
        elif order.status in (order.Canceled, order.Margin, order.Rejected):
            self.log(
                f"{getattr(order.data, '_name', 'series')} "
                f"ORDER {order.getstatusname().upper()}"
            )
