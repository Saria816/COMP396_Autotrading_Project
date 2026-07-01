# tests/test_rules.py
import backtrader as bt
import pandas as pd
from pathlib import Path

from framework.strategy_base import COMP396BrokerConfig
from framework.analyzers import OpenOpenPnL
from framework.strategies_loader import _wrap_with_comp396

# ---- tiny helpers -----------------------------------------------------------

def mk_df(dates, opens, highs, lows, closes, vols=None):
    vols = vols or [0]*len(dates)
    df = pd.DataFrame({
        "Date": pd.to_datetime(dates),
        "Open": opens, "High": highs, "Low": lows, "Close": closes, "Volume": vols
    }).drop_duplicates(subset=["Date"]).sort_values("Date").set_index("Date")
    return df

def mk_feed(df, name="series_1"):
    data = bt.feeds.PandasData(
        dataname=df,
        datetime=None, open="Open", high="High", low="Low", close="Close", volume="Volume",
        timeframe=bt.TimeFrame.Days, compression=1,
    )
    data._name = name
    return data

def mk_cerebro(cash=1_000_000, commission=0.0):
    cerebro = bt.Cerebro(stdstats=False, preload=True, runonce=True)
    cerebro.broker.setcash(cash)
    if commission:
        cerebro.broker.setcommission(commission=commission)
    return cerebro

# ---- test 1: market slippage on next-open fills -----------------------------

class MarketOnce(bt.Strategy):
    params = (('size', 100),)

    def __init__(self):
        self._sent = False

    def next(self):
        if not self._sent:
            intents = [(self.data0, self.p.size)]
            if not self.overspend_guard(intents):
                return
            self.place_market(self.data0, self.p.size)  # buffered; flushed by wrapper
            self._sent = True

def test_gap_slippage_market_buy():
    # Day0 close=100, Day1 open=110 => gap=10, slippage=0.2*10=2 per unit
    df = mk_df(
        ["2020-01-01","2020-01-02","2020-01-03"],
        opens=[100,110,111], highs=[101,111,112], lows=[99,109,110], closes=[100,110,111]
    )
    cb = mk_cerebro(cash=1_000_000)
    feed = mk_feed(df)
    cb.adddata(feed)

    cfg = COMP396BrokerConfig(s_mult=1.0, end_policy="hold", output_dir=".")
    cb.addstrategy(_wrap_with_comp396(MarketOnce), _comp396=cfg, size=10)

    start_cash = cb.broker.getcash()
    cb.run(maxcpus=1)
    end_cash = cb.broker.getcash()

    # Buy 10 at next open (110) costs 110*10=1100; slippage extra 2*10=20.
    assert round(start_cash - end_cash, 6) == 1120.0

# ---- test 2: overspend guard (cancel all) -----------------------------------

class OverspendTryBuy(bt.Strategy):
    params = (('size', 10_000_000),)

    def next(self):
        intents = [(self.data0, self.p.size)]  # huge buy
        assert not self.overspend_guard(intents)  # should fail
        # Since guard failed, do not place the order

def test_overspend_cancel_all():
    df = mk_df(
        ["2020-01-01","2020-01-02"],
        opens=[100,100], highs=[100,100], lows=[100,100], closes=[100,100]
    )
    cb = mk_cerebro(cash=1_000)  # tiny cash
    cb.adddata(mk_feed(df))
    cfg = COMP396BrokerConfig(s_mult=1.0, end_policy="hold", output_dir=".")
    cb.addstrategy(_wrap_with_comp396(OverspendTryBuy), _comp396=cfg)
    cb.run(maxcpus=1)
    # No exception means guard behaved; position must be zero
    assert cb.broker.getvalue() == cb.broker.getcash() == 1000

# ---- test 3: final-day liquidation at last open (submit on penultimate) -----

class BuyAndHoldThenAutoLiquidate(bt.Strategy):
    params = (('size', 1),)

    def __init__(self):
        self._b = False

    def next(self):
        if not self._b:
            intents = [(self.data0, self.p.size)]
            if self.overspend_guard(intents):
                self.place_market(self.data0, self.p.size)
                self._b = True

def test_final_day_liquidation_penultimate_submit(tmp_path: Path):
    df = mk_df(
        ["2020-01-01","2020-01-02","2020-01-03"],
        opens=[100,105,110], highs=[100,105,110], lows=[100,105,110], closes=[100,105,110]
    )
    cb = mk_cerebro(cash=1_000)
    cb.adddata(mk_feed(df))
    cfg = COMP396BrokerConfig(s_mult=0.0, end_policy="liquidate", output_dir=str(tmp_path))
    cb.addstrategy(_wrap_with_comp396(BuyAndHoldThenAutoLiquidate), _comp396=cfg, size=1)
    cb.addanalyzer(OpenOpenPnL, _name="oopnl")
    res = cb.run(maxcpus=1)[0]

    # Buy 1 at day2 open=105; auto-liquidate at final-day open=110 (submitted on penultimate)
    # Cash: start 1000 - 105 + 110 = 1005
    assert round(cb.broker.getvalue(), 6) == 1005.0
    # sanity: analyzer has no bankrupt flag
    assert res.analyzers.oopnl.get_analysis().get("bankrupt") is False

# ---- test 4: bankruptcy triggers liquidation and halt -----------------------

class GoShortAndDie(bt.Strategy):
    params = (('size', -100),)

    def __init__(self):
        self._sent = False

    def next(self):
        if not self._sent:
            intents = [(self.data0, self.p.size)]
            if self.overspend_guard(intents):
                self.place_market(self.data0, self.p.size)  # large short
                self._sent = True

def test_bankruptcy_triggers_liquidation_and_halt(tmp_path: Path):
    # Price rockets, making short massively negative
    df = mk_df(
        ["2020-01-01","2020-01-02","2020-01-03","2020-01-04"],
        opens=[100,200,400,800], highs=[100,200,400,800], lows=[100,200,400,800], closes=[100,200,400,800]
    )
    cb = mk_cerebro(cash=1_000)
    cb.adddata(mk_feed(df))
    cfg = COMP396BrokerConfig(s_mult=0.0, end_policy="hold", output_dir=str(tmp_path))
    cb.addstrategy(_wrap_with_comp396(GoShortAndDie), _comp396=cfg, size=-100)
    cb.addanalyzer(OpenOpenPnL, _name="oopnl")
    res = cb.run(maxcpus=1)[0]

    # Should have flagged bankrupt and stopped early
    assert res.analyzers.oopnl.get_analysis().get("bankrupt") is True

# ---- test 5: raw buy overspend -> cancel all --------------------------------

class RawBuysOverspend(bt.Strategy):
    params = tuple()

    def next(self):
        d = self.data0
        o = float(d.open[0])
        cash = self.broker.getcash()

        # First: try a market buy that uses ~60% of cash
        sz1 = int((0.60 * cash) // o)
        self.buy(data=d, size=sz1)  # raw buy (buffered by wrapper)

        # Second: try another market buy that would exceed remaining cash
        # This should trigger cancel-all of BOTH today's market orders.
        sz2 = int((0.50 * cash) // o)
        self.buy(data=d, size=sz2)  # raw buy -> overspend -> both dropped

def test_raw_buy_overspend_cancel_all():
    df = mk_df(
        ["2022-01-03", "2022-01-04", "2022-01-05"],
        opens=[100,100,100], highs=[100,100,100], lows=[100,100,100], closes=[100,100,100]
    )
    cb = mk_cerebro(cash=1_000)
    cb.adddata(mk_feed(df))
    cfg = COMP396BrokerConfig(s_mult=0.0, end_policy="hold", output_dir=".")
    cb.addstrategy(_wrap_with_comp396(RawBuysOverspend), _comp396=cfg)
    cb.run(maxcpus=1)

    # If cancel-all worked, cash/value unchanged (no orders should have filled next day)
    assert cb.broker.getcash() == 1_000
    assert cb.broker.getvalue() == 1_000
