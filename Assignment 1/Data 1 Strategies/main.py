#!/usr/bin/env python3
# main.py
import argparse
import json
import os
import sys
from pathlib import Path

import backtrader as bt

from framework.plotting import (
    save_equity_plot, save_per_series_pd, save_per_series_plots,
    save_equity_dashboard, save_all_series_equity, save_portfolio_underwater, save_realized_equity_plot, save_combined_equity_dashboard
)


# Optional YAML config (falls back to JSON if YAML not installed)
DEFAULT_CONFIG = {
    "starting_cash": 1_000_000,
    "commission": 0.0,
    "s_mult": 1.0,               # scales 20% gap slippage for market orders
    "plot": True,
    "data_dir": "./DATA/PART1",
    "output_dir": "./output",
    "end_policy": "liquidate",    # or "hold"
    "strategy": "example_buy_and_hold",  # module (file) under /strategies
    "strategy_class": None,       # if None, auto-pick the first Strategy class
    "strategy_params": {}         # dict passed to strategy
}

def load_config(path: Path) -> dict:
    cfg = DEFAULT_CONFIG.copy()
    if not path.exists():
        return cfg
    try:
        import yaml  # type: ignore
        with path.open("r") as f:
            cfg.update(yaml.safe_load(f) or {})
        return cfg
    except Exception:
        # try JSON
        try:
            with path.open("r") as f:
                cfg.update(json.load(f))
        except Exception:
            pass
        return cfg

# --- Strategy param parsing helpers (CLI overrides only) ----------------------
TRUE_SET = {"true", "yes", "on", "1"}
FALSE_SET = {"false", "no", "off", "0"}

def _coerce_value(s: str):
    # Try JSON first for lists/dicts/null/bools
    try:
        if s.startswith("[") or s.startswith("{"):
            return json.loads(s)
    except Exception:
        pass
    # Booleans
    low = s.strip().lower()
    if low in TRUE_SET:
        return True
    if low in FALSE_SET:
        return False
    # Int / float
    try:
        if low.startswith("0") and low != "0" and not low.startswith("0."):
            # keep leading-zero strings as-is
            raise ValueError
        return int(s)
    except Exception:
        try:
            return float(s)
        except Exception:
            pass
    # Comma-separated list -> try to coerce each item
    if "," in s:
        parts = [p.strip() for p in s.split(",")]
        return [_coerce_value(p) for p in parts]
    return s

def parse_param_args(param_items: list[str]) -> dict:
    params = {}
    for item in param_items or []:
        if "=" not in item:
            continue
        k, v = item.split("=", 1)
        k = k.strip()
        v = v.strip()
        if not k:
            continue
        params[k] = _coerce_value(v)
    return params

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def parse_args():
    ap = argparse.ArgumentParser(
        description="BT396 Backtrader harness"
    )
    ap.add_argument("--config", default="config.yaml", help="Path to config file (YAML or JSON).")
    ap.add_argument("--strategy", help="Strategy module name in /strategies (e.g. bankrupt).")
    ap.add_argument("--strategy-class", help="Specific Strategy class to use (optional).")
    ap.add_argument("--cash", type=float, help="Starting cash (default 1,000,000).")
    ap.add_argument("--commission", type=float, help="Commission, decimal (e.g. 0.001).")
    ap.add_argument("--s-mult", type=float, help="Slippage multiplier for 20% gap slippage.")
    ap.add_argument("--no-plot", action="store_true", help="Disable plotting.")
    ap.add_argument("--data-dir", help="Folder with 10 CSVs.")
    ap.add_argument("--output-dir", help="Folder to write artifacts.")
    ap.add_argument("--end-policy", choices=["liquidate", "hold"], help="Final-day policy.")
    # Strategy parameter overrides (do NOT use YAML for per-strategy params anymore)
    ap.add_argument(
        "--param",
        action="append",
        default=[],
        help=("Strategy parameter override in key=value form. Repeatable. "
              "Values are parsed as int/float/bool/JSON or comma-separated lists.")
    )
    # NEW: verbose framework logging (orders, fills, slippage, trade PnL)
    ap.add_argument("--debug", action="store_true",
                    help="Enable verbose framework logging (orders, fills, slippage, trade PnL).")
    # NEW: test period option for out-of-sample testing
    ap.add_argument("--test-period", action="store_true",
                    help="Use only test period data (last 30%% / days 701-1000) for out-of-sample validation.")
    return ap.parse_args()

def main():
    args = parse_args()
    cfg = load_config(Path(args.config))

    # CLI overrides
    if args.strategy:       cfg["strategy"] = args.strategy
    if args.strategy_class: cfg["strategy_class"] = args.strategy_class
    if args.cash is not None:        cfg["starting_cash"] = args.cash
    if args.commission is not None:  cfg["commission"] = args.commission
    if args.s_mult is not None:      cfg["s_mult"] = args.s_mult
    if args.no_plot:                  cfg["plot"] = False
    if args.data_dir:                 cfg["data_dir"] = args.data_dir
    if args.output_dir:               cfg["output_dir"] = args.output_dir
    if args.end_policy:               cfg["end_policy"] = args.end_policy

    # Honor either --debug or the pytest env variable
    debug_flag = bool(args.debug or os.environ.get("PYTEST_CURRENT_TEST"))

    root = Path(__file__).resolve().parent
    sys.path.insert(0, str(root))  # allow `framework` and `strategies` imports

    from framework.data_loader import add_10_csv_feeds
    from framework.strategies_loader import load_strategy_class
    from framework.analyzers import OpenOpenPnL, RealizedPnL, PDRatio, Activity, PerformanceMetrics
    from framework.plotting import save_equity_plot, save_per_series_pd
    from framework.strategy_base import COMP396BrokerConfig

    data_dir = (root / cfg["data_dir"]).resolve()
    output_dir = (root / cfg["output_dir"]).resolve()
    ensure_dir(output_dir)

    # Cerebro
    cerebro = bt.Cerebro(stdstats=False, preload=True, runonce=True)
    cerebro.broker.setcash(cfg["starting_cash"])
    if cfg["commission"] and cfg["commission"] > 0:
        cerebro.broker.setcommission(commission=cfg["commission"])

    # Determine date range for test period (out-of-sample)
    fromdate = None
    todate = None
    if args.test_period:
        # Test period: days 701-1000 (last 30% of data)
        # Based on analysis: test period starts from 2071-11-08
        from datetime import datetime
        fromdate = datetime(2071, 11, 8)  # Start of test period (day 701)
        print(f"\n🔬 TEST PERIOD MODE: Using out-of-sample data from {fromdate.strftime('%Y-%m-%d')} onwards\n")

    # Add 10 aligned CSV feeds
    datas = add_10_csv_feeds(cerebro, data_dir, fromdate=fromdate, todate=todate)

    # Load student strategy
    StrategyClass = load_strategy_class(cfg["strategy"], cfg["strategy_class"]) 

    # Strategy parameters now come from defaults in the strategy class and can be
    # overridden via CLI --param key=value (repeatable). YAML no longer carries
    # per-strategy params.
    params = parse_param_args(args.param)

    strategy_name = args.strategy or cfg["strategy"]

    print("\n=== Backtest Configuration ===")
    print(f"Strategy: {strategy_name}")
    print("Parameters (CLI overrides):")
    if params:
        for k, v in params.items():
            print(f"  {k}: {v}")
    else:
        print("  <using strategy defaults>")
    print("================================\n")

    # broker-level shared config (used by COMP396Base)
    params["_comp396"] = COMP396BrokerConfig(
        s_mult=float(cfg["s_mult"]),
        end_policy=str(cfg["end_policy"]).lower(),
        output_dir=str(output_dir),
        debug=debug_flag,  # <-- wire CLI/env to framework debug logging
    )

    if debug_flag:
        print("Debug logging ENABLED (orders, fills, slippage, trade PnL)")

    cerebro.addstrategy(StrategyClass, **params)

    # Analyzers
    cerebro.addanalyzer(OpenOpenPnL, _name="oopnl")
    cerebro.addanalyzer(PDRatio, _name="pd")
    cerebro.addanalyzer(Activity, _name="activity")
    cerebro.addanalyzer(RealizedPnL, _name="realpnl")
    cerebro.addanalyzer(PerformanceMetrics, _name="perf")

    # Run
    strat = cerebro.run(maxcpus=1)[0]

    # Collect analyzer outputs
    oopnl = strat.analyzers.oopnl.get_analysis()
    pdres = strat.analyzers.pd.get_analysis()
    act   = strat.analyzers.activity.get_analysis()
    realpnl = strat.analyzers.realpnl.get_analysis()
    perf = strat.analyzers.perf.get_analysis()

    # Calculate equity curve from portfolio cumulative PnL
    portfolio_cum_pnl = oopnl.get("portfolio_cum", [])
    initial_cash = cfg["starting_cash"]
    equity_curve = [initial_cash + pnl for pnl in portfolio_cum_pnl]

    # Persist enhanced summary with performance metrics
    summary = {
        "final_value": float(cerebro.broker.getvalue()),
        "bankrupt": bool(oopnl.get("bankrupt", False)),
        "pd_ratio_portfolio": pdres.get("portfolio", {}).get("pd_ratio"),
        "activity_pct": act.get("activity_pct"),
        "end_policy": cfg["end_policy"],
        "s_mult": cfg["s_mult"],
        # 新增关键财务指标
        "total_return": perf.get("total_return", 0),
        "annualized_return": perf.get("annualized_return", 0),
        "max_drawdown_pct": perf.get("max_drawdown_pct", 0),
        "annualized_sharpe": perf.get("annualized_sharpe", 0),
        "win_rate": perf.get("win_rate", 0),
        "trading_days": perf.get("trading_days", 0),
        # Equity curve for visualization
        "equity_curve": equity_curve
    }
    with (output_dir / "run_summary.json").open("w") as f:
        json.dump(summary, f, indent=2)

    # Per-series PD table
    save_per_series_pd(pdres, output_dir)

    # Plots
    if cfg["plot"]:
        # Existing single portfolio and per-series files
        save_equity_plot(oopnl, pdres, act, output_dir)
        save_per_series_plots(oopnl, output_dir)
        save_combined_equity_dashboard(oopnl, realpnl, pdres, act, output_dir)

        # NEW: dashboard + all-in-one + underwater
        save_equity_dashboard(oopnl, pdres, act, output_dir)
        save_all_series_equity(oopnl, output_dir)
        save_portfolio_underwater(oopnl, output_dir)
        save_realized_equity_plot(realpnl, output_dir)

        # cerebro.plot(style='candlestick')

    print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    # If called with no parameters, display the version and release date and exit
    if len(sys.argv) <= 1:
        from framework import __version__ as BT396_VERSION, __release_date__ as BT396_DATE
        print(f"{BT396_VERSION} ({BT396_DATE})")
    else:
        main()
