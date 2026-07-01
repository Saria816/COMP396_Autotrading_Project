# strategies/example_buy_and_hold.py
#
# Wrapped example: buy-and-hold a single instrument (data0).
# - Buys once (size units) after the COMP396 engine runs.
# - Uses overspend_guard and place_market injected by the wrapper.
# - Includes order/trade logging.

import backtrader as bt


class ExampleBuyAndHold(bt.Strategy):
    """Wrapped example strategy that buys a single instrument once and then holds it for the rest of the backtest."""
    params = dict(
        size=1,        # default units to buy on first opportunity
        printlog=True, # set False to silence logs
    )

    def __init__(self):
        self._did_buy = False

    # Optional banner
    def start(self):
        if getattr(self.p, "printlog", False):
            names = [d._name for d in self.datas]
            dt0 = self.datas[0].datetime.date(0) if len(self.datas) else "n/a"
            print(f"{dt0} === ExampleBuyAndHold (wrapped) wired ===")
            print(f"feeds={len(self.datas)} names={names} size={self.p.size}")

    def _log(self, msg):
        if getattr(self.p, "printlog", False) and len(self.datas):
            dt = self.datas[0].datetime.date(0)
            print(f"{dt} {msg}")

    def next(self):
        # COMP396Base.next() has already run (by the wrapper), so:
        # - Bankruptcy/final-day logic already applied
        # - Limit cancels handled
        # - We'll queue market orders here and the wrapper will flush same bar
        if self._did_buy:
            return

        d = self.data0
        intents = [(d, self.p.size)]
        if not self.overspend_guard(intents):
            self._log("OVRSPEND: cancelling new buy")
            return

        self.place_market(d, self.p.size)  # buffered; filled next open with slippage model
        self._did_buy = True
        self._log(f"[ORDER QUEUED] {d._name} buy size={self.p.size:+.4f}")

    # ---- logging hooks ----
    def notify_order(self, order):
        d = order.data
        st = order.getstatusname().upper()
        if order.status == order.Submitted:
            self._log(f"[ORDER SUBMITTED] {d._name} type={order.exectype} size={order.size:+.4f}")
        elif order.status == order.Accepted:
            self._log(f"[ORDER ACCEPTED]  {d._name} type={order.exectype} size={order.size:+.4f}")
        elif order.status == order.Completed:
            side = "BUY" if order.isbuy() else "SELL"
            self._log(
                f"[FILL] {side} {d._name} px={order.executed.price:.4f} "
                f"size={order.executed.size:+.4f} value={order.executed.value:.2f} "
                f"comm={order.executed.comm:.2f}"
            )
        elif order.status in [order.Canceled, order.Rejected, order.Margin]:
            self._log(f"[ORDER {st}] {d._name} size={order.size:+.4f}")

    def notify_trade(self, trade):
        if trade.isclosed:
            self._log(
                f"[TRADE CLOSED] {trade.data._name} pnl={trade.pnl:.2f} "
                f"pnl_comm={trade.pnlcomm:.2f} size={trade.size:+.4f}"
            )
        else:
            self._log(
                f"[TRADE UPDATE] {trade.data._name} size={trade.size:+.4f} "
                f"pnl={trade.pnl:.2f} pnl_comm={trade.pnlcomm:.2f}"
            )
