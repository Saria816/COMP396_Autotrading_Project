# framework/analyzers.py
import backtrader as bt
import math
import collections


class OpenOpenPnL(bt.Analyzer):
    """
    Computes per-series and portfolio Open->Open P&L, cumulative PnL, and
    carries a 'bankrupt' flag read from strategy._comp396_state.
    """
    def start(self):
        self._dates = []
        self._per_inst_daily = {}   # name -> [pnls...]
        self._per_inst_cum   = {}
        self._portfolio_daily = []
        self._portfolio_cum   = []
        self._bankrupt = False

    def next(self):
        # Append date for this bar
        dt = self.datas[0].datetime.date(0)
        self._dates.append(dt)
        port_pnl = 0.0

        for d in self.datas:
            name = d._name or "data"
            if name not in self._per_inst_daily:
                self._per_inst_daily[name] = []
                self._per_inst_cum[name] = []

            # position held today
            pos = self.strategy.getposition(d)
            size = pos.size if pos else 0.0

            # Open→Open P&L requires look-ahead; if unavailable (last bar), treat as 0 P&L for this day
            try:
                o0 = float(d.open[0])
                o1 = float(d.open[1])  # may raise IndexError on the last bar
                pnl = (o1 - o0) * size
            except IndexError:
                pnl = 0.0

            self._per_inst_daily[name].append(pnl)
            cum = (self._per_inst_cum[name][-1] + pnl) if self._per_inst_cum[name] else pnl
            self._per_inst_cum[name].append(cum)
            port_pnl += pnl

        self._portfolio_daily.append(port_pnl)
        cum = (self._portfolio_cum[-1] + port_pnl) if self._portfolio_cum else port_pnl
        self._portfolio_cum.append(cum)

        # bankrupt flag from strategy
        self._bankrupt = bool(getattr(self.strategy, "_comp396_state", {}).get("bankrupt", False))

        # record bankruptcy date if first detected
        if self._bankrupt and not hasattr(self, "_bankrupt_date"):
            self._bankrupt_date = dt  # record the first day bankruptcy occurs

    def get_analysis(self):
        return {
            "dates": self._dates,
            "per_instrument_daily": self._per_inst_daily,
            "per_instrument_cum": self._per_inst_cum,
            "portfolio_daily": self._portfolio_daily,
            "portfolio_cum": self._portfolio_cum,
            "bankrupt": self._bankrupt,
            "bankrupt_date": getattr(self, "_bankrupt_date", None),
        }


class PDRatio(bt.Analyzer):
    """
    PD = Final CumPnL / MaxDrawdown (based on CumPnL) per series and portfolio.
    """
    def start(self):
        self._res = {"portfolio": {}, "per_instrument": {}}

    def stop(self):
        # Gather from OpenOpenPnL analyzer
        oop = self.strategy.analyzers.oopnl.get_analysis()
        def pd_of(series):
            if not series:
                return dict(pd_ratio=None, final=None, maxdd=None)
            cum = series
            run_max = float("-inf")
            maxdd = 0.0
            for v in cum:
                run_max = max(run_max, v)
                maxdd   = max(maxdd, run_max - v)
            final = cum[-1]
            pd = (final / maxdd) if (maxdd and not math.isclose(maxdd, 0.0)) else None
            return dict(pd_ratio=pd, final=final, maxdd=maxdd)

        # Portfolio
        self._res["portfolio"] = pd_of(oop["portfolio_cum"])

        # Per instrument
        for name, cum in oop["per_instrument_cum"].items():
            self._res["per_instrument"][name] = pd_of(cum)

    def get_analysis(self):
        return self._res

class Activity(bt.Analyzer):
    """
    % of days with any non-zero position across the portfolio.
    """
    def start(self):
        self._days = 0
        self._active = 0

    def next(self):
        if len(self.datas[0]) < 1:
            return
        self._days += 1
        active = False
        for d in self.datas:
            if self.strategy.getposition(d).size != 0:
                active = True
                break
        if active:
            self._active += 1

    def get_analysis(self):
        pct = (100.0 * self._active / self._days) if self._days else 0.0
        return {"activity_pct": pct, "days": self._days, "active_days": self._active}


class RealizedPnL(bt.Analyzer):
    """
    Date-aligned realized PnL:
    - Accumulates all realized trade PnL for the *current bar*.
    - On next(), appends one value per date (0 if no trades that day).
    - Produces arrays whose lengths always match 'dates'.
    """

    def start(self):
        self._dates = []
        self._per_inst_daily = collections.defaultdict(list)  # name -> [daily pnl...]
        self._per_inst_cum   = collections.defaultdict(list)
        self._portfolio_daily = []
        self._portfolio_cum   = []
        self._today_by_name = collections.defaultdict(float)  # per-instrument realized pnl this bar
        self._bankrupt = False

        # Cache names in a stable order so we can append zeros for quiet days
        self._names = []
        for d in self.datas:
            nm = d._name or "data"
            self._names.append(nm)

    def notify_trade(self, trade):
        # Only realized PnL when a trade is closed
        if not trade.isclosed:
            return
        name = trade.data._name or "data"
        self._today_by_name[name] += float(trade.pnlcomm)

    def next(self):
        # one entry per bar/date
        dt = self.datas[0].datetime.date(0)
        self._dates.append(dt)

        # daily portfolio pnl for this bar
        day_port_pnl = 0.0

        # commit today's per-instrument pnl (0.0 if none)
        for name in self._names:
            day = float(self._today_by_name.get(name, 0.0))
            day_port_pnl += day

            # daily list
            dl = self._per_inst_daily[name]
            dl.append(day)

            # cum list
            cl = self._per_inst_cum[name]
            cum = (cl[-1] + day) if cl else day
            cl.append(cum)

        # portfolio daily/cum
        self._portfolio_daily.append(day_port_pnl)
        port_cum = (self._portfolio_cum[-1] + day_port_pnl) if self._portfolio_cum else day_port_pnl
        self._portfolio_cum.append(port_cum)

        # reset day accumulator
        self._today_by_name.clear()

    def get_analysis(self):
        return {
            "dates": self._dates,
            "per_instrument_daily": dict(self._per_inst_daily),
            "per_instrument_cum": dict(self._per_inst_cum),
            "portfolio_daily": self._portfolio_daily,
            "portfolio_cum": self._portfolio_cum,
            "bankrupt": self._bankrupt,
        }


    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        dt = trade.data.datetime.date(0)
        name = trade.data._name or "data"

        # record realized PnL
        pnl = trade.pnlcomm

        # init structures
        if name not in self._per_inst_daily:
            self._per_inst_daily[name] = []
            self._per_inst_cum[name] = []

        # append
        self._per_inst_daily[name].append(pnl)
        cum = (self._per_inst_cum[name][-1] + pnl) if self._per_inst_cum[name] else pnl
        self._per_inst_cum[name].append(cum)

        # portfolio
        if len(self._portfolio_daily) < len(self._dates):
            # already had a date entry
            self._portfolio_daily[-1] += pnl
            self._portfolio_cum[-1] += pnl
        else:
            self._portfolio_daily.append(pnl)
            cum_port = (self._portfolio_cum[-1] + pnl) if self._portfolio_cum else pnl
            self._portfolio_cum.append(cum_port)

    def next(self):
        dt = self.datas[0].datetime.date(0)
        self._dates.append(dt)
        # ensure portfolio entry exists for this bar
        if len(self._portfolio_daily) < len(self._dates):
            self._portfolio_daily.append(0.0)
            cum = self._portfolio_cum[-1] if self._portfolio_cum else 0.0
            self._portfolio_cum.append(cum)

    def get_analysis(self):
        return {
            "dates": self._dates,
            "per_instrument_daily": self._per_inst_daily,
            "per_instrument_cum": self._per_inst_cum,
            "portfolio_daily": self._portfolio_daily,
            "portfolio_cum": self._portfolio_cum,
            "bankrupt": self._bankrupt,
        }

# framework/analyzers.py (append this)

import math
import backtrader as bt

class TruePortfolioPD(bt.Analyzer):

    # PD ratio based on total broker equity (cash + holdings).
    # Records the true daily equity curve including slippage and final liquidation.


    def start(self):
        self._values = []   # daily broker.getvalue()
        self._dates = []

    def next(self):
        value = float(self.strategy.broker.getvalue())
        dt = self.strategy.datas[0].datetime.date(0)
        self._values.append(value)
        self._dates.append(dt)

    def stop(self):
        if not self._values:
            self._res = dict(pd_ratio=None, final=None, maxdd=None)
            return

        start = self._values[0]
        cum = [v - start for v in self._values]

        run_max = float("-inf")
        maxdd = 0.0
        for v in cum:
            run_max = max(run_max, v)
            maxdd = max(maxdd, run_max - v)

        final = cum[-1]
        pd = (final / maxdd) if (maxdd and not math.isclose(maxdd, 0.0)) else None

        # Get bankruptcy date from strategy state
        bankrupt_date = getattr(self.strategy, "_comp396_state", {}).get("bankrupt_date", None)

        # Include the date in the result dictionary
        self._res = dict(
            pd_ratio=pd,
            final_equity=self._values[-1],
            start_equity=start,
            final_profit=final,
            max_drawdown=maxdd,
            dates=self._dates,
            values=self._values,
            bankrupt_date=bankrupt_date
        )

    def get_analysis(self):
        return self._res
