# framework/strategy_base.py
import os
import backtrader as bt
from dataclasses import dataclass
from datetime import date

@dataclass
class COMP396BrokerConfig:
    """Holds framework-wide broker/config options used by the COMP396 engine (slippage scale, end-of-test policy, output paths, debug)."""
    s_mult: float = 1.0              # scales the 20% gap model
    end_policy: str = "liquidate"    # or "hold"
    output_dir: str = "./output"
    debug: bool = False              # verbose CLI logs (auto-on under pytest)


class COMP396Base:
    """
    Mixin for COMP396 rule enforcement:
    - Gap slippage (20% of overnight gap) on MARKET orders only.
    - Overspend guard: if today's *intended* market orders would make cash<0
      at next open (incl. slippage), cancel all new orders for the day.
    - Max 2 limit orders per series per day (1 per side).
    - Bankruptcy: if net worth < 0, force-liquidate all at current open (w/ slippage) and stop.
    - Final-day policy: liquidate all at last open if policy == 'liquidate'.
    - Open->Open accounting for analyzers (they read lines.open[-0] .. open[+1]).
    """

    def __init__(self, *args, **kwargs):
        # The child Strategy (bt.Strategy subclass) must declare _comp396 in its params.
        self._cfg = getattr(self.p, '_comp396', None)
        if self._cfg is None:
            raise ValueError("Strategy must declare params with ('_comp396', None) and main.py must pass it.")

        self._today: date | None = None
        self._limit_counts = {}  # (data, side) -> count today, side in {"buy","sell"}

        self._bankrupt = False
        self._all_datas = list(self.datas)

        # let analyzers read this
        self._comp396_state = {"bankrupt": False}

        # --- Debug / Verbose logging control ---
        # On if config.debug OR running under pytest (PYTEST_CURRENT_TEST env var present)
        cfg_debug = bool(getattr(self._cfg, "debug", False))
        self._debug = cfg_debug or bool(os.environ.get("PYTEST_CURRENT_TEST"))

    # ---------- Helpers: date handling ----------
    def _d(self, data):
        return data.datetime.date(0)

    def _is_new_day(self):
        d = self.data.datetime.date(0)
        if self._today != d:
            self._today = d
            self._limit_counts = {}
            self._today_market_orders = []
            self._today_intents = []
            self._pending_market_orders = []
            if self._debug:
                self.dlog("NEW DAY: reset counters / buffers")
            return True
        return False

    # ---------- Helpers: order placement ----------
    def place_market(self, data, size):
        """Queue a market order (executed next open)."""
        return self.buy(data=data, size=size) if size > 0 else self.sell(data=data, size=abs(size))

    def place_limit1(self, data, size, price):
        return self._place_limit(data, size, price)

    def place_limit2(self, data, size, price):
        return self._place_limit(data, size, price)

    def place_limit(self, data, size, price):
        return self._place_limit(data, size, price)

    def _place_limit(self, data, size, price):
        """
        Single source-of-truth enforcement:
        - Do NOT pre-increment caps here.
        - Delegate to buy/sell (which enforce and increment exactly once).
        """
        ex = bt.Order.Limit
        side = "BUY" if size > 0 else "SELL"
        self.dlog(f"LIMIT {side} queued {data._name} @ {price:.6g} size={abs(size)}")
        if size > 0:
            return self.buy(data=data, size=abs(size), price=price, exectype=ex)
        else:
            return self.sell(data=data, size=abs(size), price=price, exectype=ex)

    def _cancel_all_todays_market_orders(self):
        # Cancel orders we tracked
        self.dlog("OVRSPEND: cancelling ALL queued market orders for today")
        for o in list(getattr(self, "_today_market_orders", [])):
            try:
                self.cancel(o)
            except Exception:
                pass
        self._today_market_orders = []
        self._today_intents = []

        # Defensive sweep: cancel any still-open MARKET orders at the broker for this strategy
        try:
            for o in list(self.broker.get_orders_open()):
                if o.exectype == bt.Order.Market and o.owner is self:
                    try:
                        self.cancel(o)
                    except Exception:
                        pass
        except Exception:
            # some brokers may not expose get_orders_open; fail-quiet
            pass

    def _flush_pending_market_orders(self):
        # Build combined intents (ignore entries without size/data)
        intents = [(pm["data"], pm["signed"]) for pm in self._pending_market_orders
                   if pm["data"] is not None and pm["signed"] is not None]

        if self._pending_market_orders:
            pretty = ", ".join(
                f"{('BUY' if pm['is_buy'] else 'SELL')} {pm['data']._name} size={abs(pm['signed'])}"
                for pm in self._pending_market_orders if pm["data"] is not None and pm["signed"] is not None
            )
            self.dlog(f"FLUSH market orders: [{pretty}]")

        if intents and not self.overspend_guard(intents):
            # Reject ALL new market orders today
            self.log("OVRSPEND: cancelling ALL new market orders for today")
            self._pending_market_orders.clear()
            return

        # Submit buffered orders to broker; track for analysis
        for pm in self._pending_market_orders:
            if pm["is_buy"]:
                o = super(COMP396Base, self).buy(*pm["args"], **pm["kwargs"])
            else:
                o = super(COMP396Base, self).sell(*pm["args"], **pm["kwargs"])

            if o is not None and pm["data"] is not None and pm["signed"] is not None:
                # Track for cash forecast
                self._today_market_orders.append(o)
                self._today_intents.append((pm["data"], pm["signed"]))
                self.dlog(f"SUBMIT {('BUY' if pm['is_buy'] else 'SELL')} MARKET {pm['data']._name} size={abs(pm['signed'])}")

        self._pending_market_orders.clear()

    # These overrides intercept raw buy / sell and route them through the rules:
    def _is_market_ex(self, kwargs):
        ex = kwargs.get('exectype', bt.Order.Market)
        return ex in (bt.Order.Market, None)

    def _is_limit_ex(self, kwargs):
        return kwargs.get('exectype', None) == bt.Order.Limit

    def _extract_order_intent(self, is_buy, args, kwargs):
        data = kwargs.get('data', args[0] if args else (self.data0 if len(self.datas) else None))
        size = kwargs.get('size', None)
        if size is None:
            side = "BUY" if is_buy else "SELL"
            self.log(f"WARNING: raw {side} called without explicit 'size'. "
                     f"Overspend pre-check skipped for this order. Use place_market(...) or pass size=...")
            return data, None
        signed = +abs(size) if is_buy else -abs(size)
        return data, signed

    def _enforce_limit_cap(self, is_buy, data) -> bool:
        side = "buy" if is_buy else "sell"
        key = (data, side)
        count = self._limit_counts.get(key, 0)
        if count >= 1:
            self.log(f"Limit {side.upper()} rejected (max 1 per side/day) on {data._name} {self._d(data)}")
            return False
        self._limit_counts[key] = count + 1
        return True

    def buy(self, *args, **kwargs):
        # LIMITs: enforce per-side cap and place immediately
        if self._is_limit_ex(kwargs):
            data, _ = self._extract_order_intent(True, args, kwargs)
            if data is not None and not self._enforce_limit_cap(True, data):
                return None
            return super().buy(*args, **kwargs)

        # MARKETs: buffer for end-of-bar overspend check
        if self._is_market_ex(kwargs):
            data, signed = self._extract_order_intent(True, args, kwargs)
            if data is not None and signed is not None:
                self.dlog(f"QUEUE BUY  MARKET {data._name} size={abs(signed)}")
            self._pending_market_orders.append(
                {"is_buy": True, "args": args, "kwargs": kwargs, "data": data, "signed": signed}
            )
            return None

        # Other types: fall back
        return super().buy(*args, **kwargs)

    def sell(self, *args, **kwargs):
        if self._is_limit_ex(kwargs):
            data, _ = self._extract_order_intent(False, args, kwargs)
            if data is not None and not self._enforce_limit_cap(False, data):
                return None
            return super().sell(*args, **kwargs)

        if self._is_market_ex(kwargs):
            data, signed = self._extract_order_intent(False, args, kwargs)
            if data is not None and signed is not None:
                self.dlog(f"QUEUE SELL MARKET {data._name} size={abs(signed)}")
            self._pending_market_orders.append(
                {"is_buy": False, "args": args, "kwargs": kwargs, "data": data, "signed": signed}
            )
            return None

        return super().sell(*args, **kwargs)

    # ---------- Overspend guard for market orders ----------
    def overspend_guard(self, intents):
        """
        intents: list[(data, size)] for *market* orders planned today.
        Estimate cash at next open (k+1). If next open isn't available yet,
        fall back to today's open to avoid spurious cancels.
        """
        cash = self.broker.getcash()

        for (data, size) in intents:
            # Try next open; if unavailable (first bar), use today's open
            try:
                next_open = float(data.open[1])
            except IndexError:
                next_open = float(data.open[0])

            today_close = float(data.close[0])
            gap = abs(next_open - today_close)
            slip = self._cfg.s_mult * 0.2 * gap * abs(size)

            # buys consume cash; sells add cash (negative size => -size*price is +cash)
            cash -= size * next_open
            # slippage always reduces cash (modeled as extra cost / reduced proceeds)
            cash -= slip

        self.dlog(f"OVRSPEND forecast cash_next={cash:.6g}")
        return cash >= 0

    # ---------- Slippage application (post-fill) ----------
    def notify_order(self, order):
        # lifecycle logs
        if order.status == order.Submitted:
            self.dlog(f"ORDER Submitted id={order.ref} {order.data._name} type={order.exectype} size={order.created.size}")
        elif order.status == order.Accepted:
            self.dlog(f"ORDER Accepted  id={order.ref} {order.data._name}")
        elif order.status in [order.Canceled, order.Rejected]:
            self.dlog(f"ORDER {('Canceled' if order.status==order.Canceled else 'Rejected')} id={order.ref} {order.data._name}")

        if order.status in [order.Completed]:
            data = order.data
            action = "BUY" if order.isbuy() else "SELL"
            self.dlog(f"FILL {action} {data._name} px={order.executed.price:.6g} size={order.executed.size}")
            # Use the gap from (close[k] -> open[k+1]) that produced this fill
            # We are now at bar k+1 when completion fires.
            today_close = float(data.close[-1]) if len(data) >= 1 else float('nan')
            this_open = float(data.open[0])
            gap = abs(this_open - today_close)
            per_unit = self._cfg.s_mult * 0.2 * gap
            extra = per_unit * abs(order.executed.size)

            # Charge slippage (extra cost / reduced proceeds)
            self.broker.add_cash(-extra)
            if self._cfg.s_mult:
                self.dlog(f"SLIPPAGE charged={extra:.6g} (per_unit={per_unit:.6g}, gap={gap:.6g}, s_mult={self._cfg.s_mult})")

    def notify_trade(self, trade):
        """Log realized PnL when a position is closed/updated."""
        if not self._debug:
            return
        dname = trade.data._name if trade.data else "data"
        if trade.isclosed:
            self.dlog(f"TRADE CLOSED {dname} pnl_gross={trade.pnl:.6g} pnl_net={trade.pnlcomm:.6g} size={trade.size}")
        else:
            self.dlog(f"TRADE UPDATE {dname} size={trade.size} price={getattr(trade, 'price', 'NA')}")

    # ---------- Bankruptcy & final-day enforcement ----------
    def _net_worth(self):
        # cash + value of longs − value of shorts at current open
        cash = self.broker.getcash()
        val = 0.0
        for d in self._all_datas:
            pos = self.getposition(d)
            if pos.size != 0:
                px = float(d.open[0])
                if pos.size > 0:
                    val += pos.size * px
                else:
                    # short position is liability
                    val -= abs(pos.size) * px
        return cash + val

    def _force_liquidate_all(self, reason: str):
        # close all positions with market orders (slippage will be charged via notify_order)
        for d in self._all_datas:
            pos = self.getposition(d)
            if pos.size != 0:
                self.close(data=d)
        self._bankrupt = (reason == "bankrupt")
        self._comp396_state["bankrupt"] = self._bankrupt
        self.log(f"Forced liquidation ({reason}) at {self.data.datetime.date(0)}")
        self.dlog("... submitted CLOSE orders for all open positions")
        # After sending, let Backtrader execute; we can stop next bar.
        self._stop_after_liquidation = True

    def start(self):
        # Ensure config is present (Strategy must declare ('_comp396', None) in params)
        self._cfg = getattr(self.p, '_comp396', None)
        if self._cfg is None:
            raise ValueError("Strategy must declare params with ('_comp396', None) and main.py must pass it.")

        # (Re)initialize per-run state here because Backtrader *always* calls start()
        self._today = None  # current date marker
        self._limit_counts = {}  # (data, side)->count for today
        self._bankrupt = False
        self._all_datas = list(self.datas)
        self._comp396_state = {"bankrupt": False}
        self._stop_after_liquidation = False
        self._pending_market_orders = []  # list of dicts: {"is_buy": bool, "args": args, "kwargs": kwargs, "data": data, "signed": +/-size}

        # recompute debug flag in case config changed between init/start
        cfg_debug = bool(getattr(self._cfg, "debug", False))
        self._debug = cfg_debug or bool(os.environ.get("PYTEST_CURRENT_TEST"))
        if self._debug:
            self.dlog("DEBUG logging enabled")

    def next(self):
        is_new = self._is_new_day()

        if is_new:
            for o in list(self.broker.get_orders_open()):
                if o.exectype == bt.Order.Limit:
                    self.cancel(o)
            self.dlog("Cancelled any carry-over LIMIT orders at day start")

        if not self._bankrupt and self._net_worth() < 0:
            self._force_liquidate_all("bankrupt")

        if getattr(self, "_stop_after_liquidation", False):
            self.env.runstop()
            return

        if self._cfg.end_policy == "liquidate":
            # penultimate bar (len == buflen - 2): schedule liquidation
            if (len(self.data) == (self.data.buflen() - 2)):
                if any(self.getposition(d).size != 0 for d in self._all_datas):
                    self._force_liquidate_all("final_day")

        # >>> NOTE: _flush_pending_market_orders() should be called from the wrapper
        # after student next() so that market orders queued this bar are sent this bar.

    # ---------- Logging ----------
    def log(self, txt):
        dt = self.datas[0].datetime.date(0)
        print(f"{dt} | {txt}")

    def dlog(self, txt):
        """Debug log (prints only when debug mode is on)."""
        if self._debug:
            dt = self.datas[0].datetime.date(0)
            print(f"{dt} | {txt}")
