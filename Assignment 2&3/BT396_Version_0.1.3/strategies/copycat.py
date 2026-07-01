# strategies/copycat.py
import backtrader as bt

class TeamStrategy(bt.Strategy):
    """
    For each instrument (data feed):
      - If yesterday's Close > yesterday's Open: target position = +stake
      - Else:                                      target position = -stake
    We place a single market order for the delta so the next-open fill
    adjusts the position to the desired target.

    Notes (BT396 harness):
      - Market orders are buffered and filled at the *next* open; the
        wrapper enforces overspend guard & 20% gap slippage model.
      - You can change 'stake' if you want more than 1 unit per series.
    """
    params = dict(
        stake=1,          # size (+/-) to target per instrument
        printlog=False,
    )

    def log(self, txt):
        if self.p.printlog:
            dt = self.datas[0].datetime.date(0)
            print(f"{dt} | {txt}")

    def next(self):
        # Build intents across all series first -> single overspend check
        intents = []
        deltas = []  # (data, delta) we will place if guard passes

        for d in self.datas:
            # Need yesterday's bar to compare O[-1], C[-1]
            if len(d) < 2:
                continue

            y_open  = float(d.open[-1])
            y_close = float(d.close[-1])

            target = self.p.stake if (y_close > y_open) else -self.p.stake

            pos = self.getposition(d)
            current = pos.size if pos else 0.0
            delta = target - current

            if abs(delta) > 0:  # only if we need to adjust
                deltas.append((d, delta))
                # For the guard: buys are positive, sells negative
                intents.append((d, delta))

        # Overspend guard (framework cancels ALL market orders today if it fails)
        if intents and not self.overspend_guard(intents):
            self.log("OVRSPEND: cancelling all new market orders today")
            return

        # Place the queued market orders
        for d, delta in deltas:
            self.place_market(d, delta)
            side = "BUY" if delta > 0 else "SELL"
            self.log(f"{side} {abs(delta):.0f} → target {self.p.stake if delta>0 else -self.p.stake} on {getattr(d, '_name', 'data')}")

    def notify_order(self, order):
        if order.status == order.Completed:
            act = "BUY" if order.isbuy() else "SELL"
            self.log(f"{act} filled @ {order.executed.price:.4f} size {order.executed.size:.0f}")
