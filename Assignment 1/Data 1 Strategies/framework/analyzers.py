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

    def get_analysis(self):
        return {
            "dates": self._dates,
            "per_instrument_daily": self._per_inst_daily,
            "per_instrument_cum": self._per_inst_cum,
            "portfolio_daily": self._portfolio_daily,
            "portfolio_cum": self._portfolio_cum,
            "bankrupt": self._bankrupt,
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


class PerformanceMetrics(bt.Analyzer):
    """
    计算年化收益率、最大回撤率、年化夏普比率等关键财务指标
    """
    
    def start(self):
        self._portfolio_values = []
        self._returns = []
        self._dates = []
        self._initial_value = None
        
    def next(self):
        # 记录组合价值和日期
        dt = self.datas[0].datetime.date(0)
        self._dates.append(dt)
        
        value = self.strategy.broker.getvalue()
        self._portfolio_values.append(value)
        
        if self._initial_value is None:
            self._initial_value = value
            
        # 计算日收益率
        if len(self._portfolio_values) > 1:
            ret = (value - self._portfolio_values[-2]) / self._portfolio_values[-2]
            self._returns.append(ret)
        else:
            self._returns.append(0.0)
    
    def get_analysis(self):
        if len(self._portfolio_values) < 2:
            return {}
            
        # 基本计算
        final_value = self._portfolio_values[-1]
        total_return = (final_value - self._initial_value) / self._initial_value
        
        # 计算交易日数和年数
        trading_days = len(self._portfolio_values)
        years = trading_days / 252.0  # 假设每年252个交易日
        
        # 年化收益率
        annualized_return = (final_value / self._initial_value) ** (1/years) - 1 if years > 0 else 0
        
        # 最大回撤
        running_max = self._portfolio_values[0]
        max_drawdown = 0.0
        max_dd_pct = 0.0
        
        for value in self._portfolio_values:
            running_max = max(running_max, value)
            drawdown = running_max - value
            drawdown_pct = drawdown / running_max if running_max > 0 else 0
            max_drawdown = max(max_drawdown, drawdown)
            max_dd_pct = max(max_dd_pct, drawdown_pct)
        
        # 计算夏普比率
        if len(self._returns) > 1:
            import statistics
            mean_return = statistics.mean(self._returns)
            std_return = statistics.stdev(self._returns) if len(self._returns) > 1 else 0
            
            # 年化夏普比率 (假设无风险利率为0)
            annualized_sharpe = (mean_return * 252) / (std_return * (252 ** 0.5)) if std_return > 0 else 0
        else:
            annualized_sharpe = 0
            
        # 胜率计算
        winning_days = sum(1 for r in self._returns if r > 0)
        win_rate = winning_days / len(self._returns) if self._returns else 0
        
        return {
            'total_return': total_return,
            'annualized_return': annualized_return,
            'max_drawdown_abs': max_drawdown,
            'max_drawdown_pct': max_dd_pct,
            'annualized_sharpe': annualized_sharpe,
            'win_rate': win_rate,
            'trading_days': trading_days,
            'final_value': final_value,
            'initial_value': self._initial_value
        }
