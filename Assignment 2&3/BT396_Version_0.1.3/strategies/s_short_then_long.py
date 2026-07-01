# strategies/s_short_then_long.py
#
# Single-series “short then long” strategy (BT396-safe)
# -----------------------------------------------------
# - Day 1: SHORT the instrument with notional exposure = leverage.
# - Day 2: LONG the instrument using (cash − cash_buffer).
# - Then hold until liquidation.
#
# All orders go through COMP396Base.place_market() and overspend_guard()
# to ensure realistic execution and cash safety.

import backtrader as bt


class TeamStrategy(bt.Strategy):
    """Single-series two-phase demo: short on day one by fixed notional amount,
    then go long on day two with available cash (BT396-safe version)."""

    params = dict(
        leverage=8_000_000,    # notional to short on Day 1 (per feed)
        cash_buffer=1_000_000, # keep £1M unspent before going long on Day 2
        printlog=False,
    )

    def __init__(self):
        # Track progress per feed
        self._shorted = {d: False for d in self.datas}
        self._longed  = {d: False for d in self.datas}

    def log(self, txt, dt=None):
        if self.p.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            print(f"{dt} {txt}")

    def next(self):
        # Apply 2-phase logic independently for each feed
        for d in self.datas:
            opx = float(d.open[0])
            if opx <= 0:
                continue

            # --- Phase 1: SHORT on Day 1 ---
            if not self._shorted[d]:
                size = - float(self.p.leverage) / opx  # negative = short
                intents = [(d, size)]

                # Pre-check affordability for the single instrument
                if not self.overspend_guard(intents):
                    self.log(f"[{d._name}] OVRSPEND: skipping short (Day 1)")
                    self._shorted[d] = True
                    continue

                self.place_market(d, size)
                self.log(f"[{d._name}] SHORT @open≈{opx:.2f} size={size:.2f}")
                self._shorted[d] = True
                continue  # one phase per bar

            # --- Phase 2: LONG on Day 2 ---
            if self._shorted[d] and not self._longed[d]:
                cash = float(self.broker.getcash())
                to_spend = max(0.0, cash - float(self.p.cash_buffer))
                size = to_spend / opx if to_spend > 0 else 0.0
                if size <= 0:
                    self._longed[d] = True
                    continue

                intents = [(d, size)]
                if not self.overspend_guard(intents):
                    self.log(f"[{d._name}] OVRSPEND: skipping long (Day 2)")
                    self._longed[d] = True
                    continue

                self.place_market(d, size)
                self.log(f"[{d._name}] LONG  @open≈{opx:.2f} size={size:.2f}")
                self._longed[d] = True

        # --- After both phases: hold positions until end ---
        return
