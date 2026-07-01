# ==============================================================
# strategies/basic_demo.py
# --------------------------------------------------------------
# A *minimal* BT396 strategy that:
#   - Buys 1 unit of the first data series on Day 1.
#   - Does nothing afterwards.
#
# This file is designed to show the structure and typical
# components of a BT396-compatible strategy.
#
# ==============================================================
import backtrader as bt


# --------------------------------------------------------------
# Every BT396 strategy file must define a class called
# `TeamStrategy`.  The loader in the framework expects this name.
# --------------------------------------------------------------
class TeamStrategy(bt.Strategy):
    """
    Very simple "buy-once" example strategy.
    Demonstrates the structure of a BT396 strategy file.
    """

    # ----------------------------------------------------------
    # 1. Parameters section
    # ----------------------------------------------------------
    # The `params` dict defines configurable values that can be
    # passed in via --strategy-args or overridden in YAML.
    # Every parameter here becomes self.p.<name> inside the code.
    params = dict(
        printlog=True,  # if True, show diagnostic output
    )

    # ----------------------------------------------------------
    # 2. __init__() — called once at the start
    # ----------------------------------------------------------
    # Use this for setting up indicators or internal variables.
    def __init__(self):
        # Internal flag so we only buy once
        self._did_buy = False

        # In more complex strategies, this is where you'd create
        # indicators such as:
        #   self.sma = bt.indicators.SMA(self.datas[0].close, period=20)
        #
        # In this simple demo we don't need any indicators.
        pass

    # ----------------------------------------------------------
    # 3. log() — helper for formatted output
    # ----------------------------------------------------------
    # Optional but common in all BT396 strategies. It makes
    # diagnostic printing easier and consistent.
    def log(self, txt, dt=None):
        if self.p.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            print(f"{dt} {txt}")

    # ----------------------------------------------------------
    # 4. next() — core trading logic
    # ----------------------------------------------------------
    # This method runs once per bar (typically one day).
    # This is where the strategy decides what to do: buy, sell,
    # hold, place limit orders, etc.
    #
    # In BT396, you should *always* place orders via the safe
    # wrappers (place_market, place_limit1, place_limit2, etc.)
    # provided by the COMP396Base class — not by self.buy().
    #
    # The framework executes all market orders at the NEXT bar's
    # open, applying slippage and overspend checks automatically.
    def next(self):
        d = self.datas[0]  # the first (and only) data feed

        # Check if we've already bought — we only want to buy once
        if not self._did_buy:
            size = 1.0  # number of units to buy

            # Before sending orders, we can use overspend_guard()
            # to ensure we have enough cash to execute safely.
            intents = [(d, size)]
            if not self.overspend_guard(intents):
                self.log("OVRSPEND: skipping initial buy (not enough cash)")
                return

            # Place a buffered market order.
            # This will execute at *next bar open* with slippage applied.
            self.place_market(d, size)
            self.log(f"Submitting initial BUY for {d._name} size={size:.2f}")

            # Set flag so we don't buy again
            self._did_buy = True

        else:
            # After the first buy, we do nothing else.
            self.log("Holding position; no further action.")

    # ----------------------------------------------------------
    # 5. notify_order() — optional feedback when orders fill
    # ----------------------------------------------------------
    # This function is called automatically whenever the broker
    # reports a change in order status (Submitted, Completed, etc.)
    def notify_order(self, order):
        d = order.data
        st = order.getstatusname()

        # Only log completed fills to keep it clean
        if order.status == order.Completed:
            side = "BUY" if order.isbuy() else "SELL"
            self.log(
                f"[{d._name}] {side} filled "
                f"@{order.executed.price:.4f} "
                f"size={order.executed.size:+.2f} "
                f"value={order.executed.value:.2f}"
            )
        elif order.status in (order.Canceled, order.Margin, order.Rejected):
            self.log(f"[{d._name}] ORDER {st.upper()}")
