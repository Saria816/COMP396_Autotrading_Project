# =============================================================================
# framework/plotting.py
# =============================================================================
# Purpose:
#   - Centralised plotting utilities for BT396.
#   - Consumes analyzer outputs (OpenOpenPnL, RealizedPnL, TruePortfolioPD,
#     PDRatio, Activity) and writes static matplotlib PNGs to disk.
# Notes:
#   - Functions are called from main.py after a backtest run completes.
#   - This file intentionally avoids changing any analyzer data; it only reads.
#   - Styling uses seaborn v0_8 preset for reasonable defaults.
# =============================================================================

from pathlib import Path
import json
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
plt.style.use("seaborn-v0_8")  # global style (kept minimal; callers can override if needed)

from pathlib import Path  # duplicate import retained intentionally (unchanged)
import matplotlib.pyplot as plt  # duplicate import retained intentionally (unchanged)
from datetime import date  # sometimes useful for type hints / clarity in annotations

# =============================================================================
# --- Helper Utilities (internal use; kept minimal per request)
# =============================================================================

def _max_drawdown_window(cum):
    # Compute (max drawdown depth, peak index, trough index) for a cumulative series.
    # Given a list of cumulative PnL (cum), return:
    #  maxdd (float), peak_idx (int), trough_idx (int)
    # where maxdd = max(runmax - cum), and the window is [peak_idx .. trough_idx].

    if not cum:
        return 0.0, None, None

    runmax = []
    peak_idx_trace = []
    mx = float("-inf")
    mx_idx = -1
    for i, v in enumerate(cum):
        if v > mx:
            mx, mx_idx = v, i
        runmax.append(mx)
        peak_idx_trace.append(mx_idx)

    dd = [rm - v for rm, v in zip(runmax, cum)]
    if not dd:
        return 0.0, None, None

    trough_idx = max(range(len(dd)), key=lambda i: dd[i])
    peak_idx = peak_idx_trace[trough_idx]
    maxdd = dd[trough_idx]
    return maxdd, peak_idx, trough_idx


# =============================================================================
# --- Portfolio-Level Plots
# =============================================================================

def save_equity_plot(oopnl: dict, pdres: dict, act: dict, outdir: Path, truepd: dict | None = None):
    # Primary frictionless (Open->Open) portfolio curve; overlays PD metrics, activity, drawdown shading.
    dates = oopnl.get("dates", [])
    eq = oopnl.get("portfolio_cum", [])

    # --- Extract ratios and activity ---
    pnl_pd = pdres.get("portfolio", {}).get("pd_ratio")
    true_pd = truepd.get("pd_ratio") if truepd else None
    act_pct = act.get("activity_pct", 0.0)

    # Compute max drawdown window
    maxdd, i_peak, i_trough = _max_drawdown_window(eq)

    plt.figure(figsize=(12, 6))
    plt.plot(dates, eq, label="Portfolio CumPnL", color="blue")

    # --- Zero-profit baseline ---
    plt.axhline(0, color="black", linestyle="--", linewidth=1, alpha=0.7, label="Break-even")

    # --- Shade max DD region if valid indices ---
    if i_peak is not None and i_trough is not None and 0 <= i_peak < len(dates) and 0 <= i_trough < len(dates):
        x0, x1 = dates[i_peak], dates[i_trough]
        y0, y1 = eq[i_peak], eq[i_trough]
        plt.axvspan(x0, x1, alpha=0.20, label="Max DD window")
        plt.scatter([x0, x1], [y0, y1], zorder=3, color="red")
        plt.annotate(f"Peak\n{y0:.2f}", (x0, y0), xytext=(10, 10), textcoords="offset points", fontsize=9)
        plt.annotate(f"Trough\n{y1:.2f}", (x1, y1), xytext=(10, -15), textcoords="offset points", fontsize=9)

    # --- Title with both PDs & activity & maxDD ---
    if pnl_pd is not None and true_pd is not None:
        title = f"Portfolio Open→Open CumPnL | PnL_PD={pnl_pd:.3f} | True_PD={true_pd:.3f} | Activity={act_pct:.1f}% | MaxDD={maxdd:.2f}"
    elif pnl_pd is not None:
        title = f"Portfolio Open→Open CumPnL | PnL_PD={pnl_pd:.3f} | True_PD=NA | Activity={act_pct:.1f}% | MaxDD={maxdd:.2f}"
    elif true_pd is not None:
        title = f"Portfolio Open→Open CumPnL | PnL_PD=NA | True_PD={true_pd:.3f} | Activity={act_pct:.1f}% | MaxDD={maxdd:.2f}"
    else:
        title = f"Portfolio Open→Open CumPnL | PD=NA | Activity={act_pct:.1f}% | MaxDD={maxdd:.2f}"

    plt.title(title)
    plt.xlabel("Date")
    plt.ylabel("CumPnL")
    plt.legend(loc="best")
    plt.tight_layout()

    # --- Mark bankruptcy date if present ---
    bankrupt_date = oopnl.get("bankrupt_date")
    if bankrupt_date is not None:
        plt.axvline(bankrupt_date, color="red", linestyle="--", linewidth=1.2, label="Bankruptcy")
        plt.text(bankrupt_date, eq[0], "Bankruptcy", color="red", rotation=90, va="bottom", ha="right", fontsize=9)

    fp = outdir / "equity_curve.png"
    plt.savefig(fp)
    plt.close()


# =============================================================================
# --- Alignment / Underwater Helpers
# =============================================================================

def _align_by_date(dates_a, vals_a, dates_b, vals_b):
    # Align two sequences (dates, values) to common dates; returns the intersection series.
    import math  # retained import for parity with original file (no functional change)
    A = {d: v for d, v in zip(dates_a, vals_a)}
    B = {d: v for d, v in zip(dates_b, vals_b)}
    common = sorted(set(A.keys()).intersection(B.keys()))
    return common, [A[d] for d in common], [B[d] for d in common]


def _underwater_curve(cum):
    # Convert cumulative series to underwater (drawdown) values vs running max.
    runmax = []
    m = float("-inf")
    for v in cum:
        m = v if v > m else m
        runmax.append(m)
    return [v - rm for v, rm in zip(cum, runmax)]  # negative or zero


# =============================================================================
# --- Combined Portfolio Dashboards
# =============================================================================

def save_combined_equity_dashboard(oopnl: dict, realpnl: dict, pdres: dict, act: dict, outdir: Path, truepd: dict | None = None):
    # Two-panel dashboard: (top) Open→Open vs Realized CumPnL, (bottom) Realized underwater.
    # Extract
    oo_dates = list(oopnl.get("dates", []))
    oo_cum = list(oopnl.get("portfolio_cum", []))

    r_dates = list(realpnl.get("dates", []))
    r_cum = list(realpnl.get("portfolio_cum", []))

    # Align by common dates (robust if either analyzer differs slightly)
    dates, oo_aligned, r_aligned = _align_by_date(oo_dates, oo_cum, r_dates, r_cum)

    # Defensive clamp if empty
    if not dates:
        # Fall back to whichever has data
        dates = r_dates or oo_dates
        oo_aligned = oo_cum[:len(dates)]
        r_aligned = r_cum[:len(dates)]

    # Underwater from realized
    uw = _underwater_curve(r_aligned)

    # --- PD ratios and meta info ---
    pnl_pd = pdres.get("portfolio", {}).get("pd_ratio")
    true_pd = None
    if truepd:
        true_pd = truepd.get("pd_ratio")

    act_pct = act.get("activity_pct", 0.0)

    if pnl_pd is not None and true_pd is not None:
        title_pd = f"PnL_PD={pnl_pd:.3f} | True_PD={true_pd:.3f}"
    elif pnl_pd is not None:
        title_pd = f"PnL_PD={pnl_pd:.3f} | True_PD=NA"
    elif true_pd is not None:
        title_pd = f"PnL_PD=NA | True_PD={true_pd:.3f}"
    else:
        title_pd = "PD=NA"

    # --- Figure setup ---
    import matplotlib.pyplot as plt
    fig = plt.figure(figsize=(14, 8), constrained_layout=True)
    gs = fig.add_gridspec(nrows=2, ncols=1, height_ratios=[3, 1])

    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[1, 0], sharex=ax1)

    # Top: two equity curves
    ax1.plot(dates, oo_aligned, label="Open→Open MTM CumPnL")
    ax1.plot(dates, r_aligned, label="Realized CumPnL (fills)")
    ax1.axhline(0, linestyle="--", linewidth=1, alpha=0.7)
    ax1.set_ylabel("CumPnL")
    ax1.set_title(f"Portfolio CumPnL — MTM vs Realized | {title_pd} | Activity={act_pct:.1f}%")

    # Highlight max DD window on realized (optional)
    maxdd, i_peak, i_trough = _max_drawdown_window(r_aligned)
    if i_peak is not None and i_trough is not None and 0 <= i_peak < len(dates) and 0 <= i_trough < len(dates):
        ax1.axvspan(dates[i_peak], dates[i_trough], alpha=0.20, label="Realized Max DD window")
        ax1.scatter([dates[i_peak], dates[i_trough]], [r_aligned[i_peak], r_aligned[i_trough]])

    ax1.legend(loc="best")

    # Bottom: realized underwater
    ax2.plot(dates, uw, label="Realized Underwater")
    ax2.axhline(0, linestyle="--", linewidth=1, alpha=0.7)
    ax2.set_ylabel("Underwater")
    ax2.set_xlabel("Date")
    ax2.legend(loc="best")

    fp = outdir / "equity_dashboard_combined.png"
    fig.savefig(fp, dpi=120)
    plt.close(fig)


def save_realized_equity_plot(realpnl: dict, outdir: Path):
    # Single-curve realized PnL plot (closed trades only); ignores slippage effects beyond fills.
    dates = list(realpnl.get("dates", []))
    eq = list(realpnl.get("portfolio_cum", []))

    # defensive clamp
    n = min(len(dates), len(eq))
    dates = dates[:n]
    eq = eq[:n]

    plt.figure(figsize=(12, 6))
    plt.plot(dates, eq, label="Portfolio Realized CumPnL")
    plt.axhline(0, linestyle="--", linewidth=1, alpha=0.7)
    plt.title("Portfolio Realized CumPnL (from fills, incl. limit-order scalps)")
    plt.xlabel("Date")
    plt.ylabel("CumPnL")
    plt.legend(loc="best")
    plt.tight_layout()
    plt.savefig(outdir / "realized_equity_curve.png")
    plt.close()


def save_equity_plot1(oopnl: dict, pdres: dict, act: dict, outdir: Path):
    # Legacy/basic Open->Open portfolio plot; retained for compatibility and quick checks.
    dates = oopnl["dates"]
    eq = oopnl["portfolio_cum"]

    plt.figure()
    plt.plot(dates, eq)
    pd_val = pdres.get("portfolio", {}).get("pd_ratio")
    act_pct = act.get("activity_pct", 0.0)
    title = f"Portfolio Open→Open CumPnL | PD={pd_val:.3f} | Activity={act_pct:.1f}%"
    if pd_val is None:
        title = f"Portfolio Open→Open CumPnL | PD=NA | Activity={act_pct:.1f}%"
    plt.title(title)
    plt.xlabel("Date")
    plt.ylabel("CumPnL")
    plt.tight_layout()
    fp = outdir / "equity_curve.png"
    plt.savefig(fp)
    plt.close()


# =============================================================================
# --- Per-Series Outputs
# =============================================================================

def save_per_series_pd(pdres: dict, outdir: Path, truepd: dict | None = None):
    # Export per-instrument PD table and portfolio summary to JSON (for dashboards/inspection).
    rows = []
    for name, d in pdres.get("per_instrument", {}).items():
        row = {
            "series": name,
            "pnl_pd_ratio": d.get("pd_ratio"),
            "final_cumPnL": d.get("final"),
            "max_drawdown": d.get("maxdd"),
        }
        rows.append(row)

    # Add portfolio-level Equity PD if available (for completeness)
    portfolio_row = {
        "series": "portfolio",
        "pnl_pd_ratio": pdres.get("portfolio", {}).get("pd_ratio"),
        "true_pd_ratio": truepd.get("pd_ratio") if truepd else None,
    }
    rows.append(portfolio_row)

    with (outdir / "per_series_pd.json").open("w") as f:
        json.dump(rows, f, indent=2)


def save_per_series_plots(oopnl: dict, outdir: Path):
    # Generate per-instrument Open->Open cumulative PnL plots (1 PNG per series).
    dates = oopnl["dates"]
    for name, cum in oopnl["per_instrument_cum"].items():
        plt.figure()
        plt.plot(dates, cum, label=f"{name} cumPnL")
        plt.title(f"{name} Open→Open Cumulative PnL")
        plt.xlabel("Date")
        plt.ylabel("CumPnL")
        plt.legend()
        plt.tight_layout()
        plt.savefig(outdir / f"{name}_cumPnL.png")
        plt.close()


# =============================================================================
# --- Advanced Dashboards & Drawdown Visualizations
# =============================================================================

from matplotlib import gridspec
import numpy as np  # currently unused for plotting but retained for parity with original file

def _running_max(x):
    # Running maximum helper used for drawdown computations.
    rm = []
    m = float("-inf")
    for v in x:
        m = max(m, v)
        rm.append(m)
    return rm


def _underwater(cum):
    # Convert cumulative series to drawdown depth (running max - value).
    rm = _running_max(cum)
    return [rm_i - v for rm_i, v in zip(rm, cum)]


def _max_dd_cycle_indices(cum):
    # Return indices for deepest drawdown cycle: (peak_idx, trough_idx, recovery_idx).

    if not cum:
        return None, None, None
    # Find peak->trough of max depth
    maxdd, i_peak, i_trough = _max_drawdown_window(cum)
    if i_peak is None or i_trough is None:
        return None, None, None
    # Find recovery: first i >= trough with cum[i] >= cum[peak]
    rec = None
    peak_val = cum[i_peak]
    for i in range(i_trough, len(cum)):
        if cum[i] >= peak_val:
            rec = i
            break
    if rec is None:
        rec = len(cum) - 1
    return i_peak, i_trough, rec


def save_equity_dashboard(oopnl: dict, pdres: dict, act: dict, outdir: Path, truepd: dict | None = None):
    # Big dashboard figure:
    #   - Top: portfolio curve with peak→recovery duration shaded and peak/trough markers.
    #   - Bottom: grid of per-instrument curves (2 columns x 5 rows), each annotated with PDs.
    dates = oopnl.get("dates", [])
    eq = oopnl.get("portfolio_cum", [])
    per = oopnl.get("per_instrument_cum", {})

    # --- layout
    fig = plt.figure(figsize=(14, 16), constrained_layout=True)
    gs = gridspec.GridSpec(nrows=6, ncols=2,
                           height_ratios=[2, 1, 1, 1, 1, 1],
                           hspace=0.45, wspace=0.15)

    # Common date formatting (applied to all axes)
    locator = mdates.AutoDateLocator()
    formatter = mdates.ConciseDateFormatter(locator)

    # --- (A) Portfolio at top
    ax_top = fig.add_subplot(gs[0, :])
    ax_top.plot(dates, eq, label="Portfolio CumPnL", linewidth=1.8)

    # Break-even (red dashed)
    ax_top.axhline(0, color="red", linestyle="--", linewidth=1, alpha=0.9, label="Break-even")

    # Highlight max DD *duration* (peak -> recovery) and mark trough
    i_peak, i_trough, i_rec = _max_dd_cycle_indices(eq)
    if i_peak is not None and i_rec is not None:
        x_peak, x_trough, x_rec = dates[i_peak], dates[i_trough], dates[i_rec]
        y_peak, y_trough = eq[i_peak], eq[i_trough]

        # Shade peak -> recovery (duration)
        ax_top.axvspan(x_peak, x_rec, alpha=0.15, label="Max DD duration")
        # Emphasize peak -> trough inside the duration
        ax_top.axvspan(x_peak, x_trough, alpha=0.20, label="Max DD (peak→trough)")

        # Markers & annotations
        ax_top.scatter([x_peak, x_trough], [y_peak, y_trough], color="red", zorder=3)
        ax_top.annotate(f"Peak\n{y_peak:.2f}", (x_peak, y_peak), xytext=(10, 10),
                        textcoords="offset points", fontsize=9)
        ax_top.annotate(f"Trough\n{y_trough:.2f}", (x_trough, y_trough), xytext=(10, -15),
                        textcoords="offset points", fontsize=9)

        # Duration bracket
        ax_top.annotate(
            "", xy=(x_peak, ax_top.get_ylim()[0]), xytext=(x_rec, ax_top.get_ylim()[0]),
            arrowprops=dict(arrowstyle="<->", shrinkA=0, shrinkB=0, lw=1.2, alpha=0.9)
        )
        dur_days = (i_rec - i_peak)  # index-count duration (bars)
        ax_top.text(dates[(i_peak + i_rec) // 2], ax_top.get_ylim()[0],
                    f"Duration: {dur_days} bars", ha="center", va="top", fontsize=9)

    pd_val = pdres.get("portfolio", {}).get("pd_ratio")
    act_pct = act.get("activity_pct", 0.0)
    uw = _underwater(eq) if eq else []
    maxdd_depth = max(uw) if uw else 0.0

    # NEW: include True PD (Equity PD) if available
    true_pd_val = None
    if truepd:
        true_pd_val = truepd.get("pd_ratio")

    if pd_val is not None and true_pd_val is not None:
        title = (f"Portfolio Open→Open CumPnL | PnL_PD={pd_val:.3f} | "
                 f"True_PD={true_pd_val:.3f} | Activity={act_pct:.1f}% | "
                 f"MaxDD={maxdd_depth:.2f}")
    elif pd_val is not None:
        title = (f"Portfolio Open→Open CumPnL | PnL_PD={pd_val:.3f} | "
                 f"True_PD=NA | Activity={act_pct:.1f}% | MaxDD={maxdd_depth:.2f}")
    elif true_pd_val is not None:
        title = (f"Portfolio Open→Open CumPnL | PnL_PD=NA | "
                 f"True_PD={true_pd_val:.3f} | Activity={act_pct:.1f}% | "
                 f"MaxDD={maxdd_depth:.2f}")
    else:
        title = (f"Portfolio Open→Open CumPnL | PD=NA | Activity={act_pct:.1f}% | "
                 f"MaxDD={maxdd_depth:.2f}")
    ax_top.set_title(title)
    ax_top.set_xlabel("Date")
    ax_top.set_ylabel("CumPnL")
    ax_top.legend(loc="best")
    ax_top.xaxis.set_major_locator(locator)
    ax_top.xaxis.set_major_formatter(formatter)

    # --- (B) 10 small multiples (2 cols x 5 rows)
    names_sorted = sorted(per.keys())[:10]  # ensure consistent order
    rows = 5
    cols = 2
    for k, name in enumerate(names_sorted):
        r = 1 + (k // cols)  # rows 1..5 in the GridSpec (row 0 was top panel)
        c = (k % cols)
        ax = fig.add_subplot(gs[r, c], sharex=None)  # not sharing x so each shows its own dates
        series_cum = per[name]
        ax.plot(dates, series_cum, linewidth=1.2)

        # Zero line (red dashed)
        ax.axhline(0, color="red", linestyle="--", linewidth=1, alpha=0.9)

        # --- PnL_PD and true_pd per instrument in title ---
        pnl_pd_inst = pdres.get("per_instrument", {}).get(name, {}).get("pd_ratio")
        equity_pd_inst = None
        if truepd and "per_instrument" in truepd:
            equity_pd_inst = truepd["per_instrument"].get(name, {}).get("pd_ratio")

        pnl_txt = "NA" if pnl_pd_inst is None else f"{pnl_pd_inst:.3f}"
        eq_txt = "NA" if equity_pd_inst is None else f"{equity_pd_inst:.3f}"
        ax.set_title(f"{name} | PnL_PD={pnl_txt} | True_PD={eq_txt}")

        ax.grid(True, alpha=0.15)
        ax.set_xlabel("Date")
        ax.set_ylabel("CumPnL")

        # Date ticks/labels on every subplot
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(formatter)
        for label in ax.get_xticklabels():
            label.set_rotation(0)  # ConciseDateFormatter is compact; keep horizontal

    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fig.tight_layout()

    fp = outdir / "equity_dashboard.png"
    fig.savefig(fp, dpi=150)
    plt.close(fig)


# =============================================================================
# --- Aggregate Portfolio Views
# =============================================================================

def save_all_series_equity(oopnl: dict, outdir: Path):
    # Overlay all per-instrument Open->Open curves on a single axes (correlation/volatility glance).
    dates = oopnl.get("dates", [])
    per = oopnl.get("per_instrument_cum", {})
    if not per:
        return
    plt.figure(figsize=(12, 7))
    for name, cum in sorted(per.items()):
        # Let the default color cycle handle colors; use distinct linestyles as backup variety
        plt.plot(dates, cum, label=name, linewidth=1.4)
    plt.axhline(0, linestyle="--", linewidth=1, alpha=0.7)
    plt.title("All Instruments — Cumulative Open→Open PnL")
    plt.xlabel("Date")
    plt.ylabel("CumPnL")
    plt.legend(ncol=2, frameon=False)
    plt.savefig(outdir / "all_equity_curves.png", dpi=150)
    plt.close()


def save_portfolio_underwater(oopnl: dict, outdir: Path):
    # Portfolio underwater chart (depth below running peak) for Open->Open curve.
    dates = oopnl.get("dates", [])
    eq = oopnl.get("portfolio_cum", [])
    if not dates or not eq:
        return
    dd = _underwater(eq)
    plt.figure(figsize=(12, 3.6))
    plt.fill_between(dates, [-d for d in dd], 0, step="pre", alpha=0.35)  # plot as negative (below zero)
    plt.plot(dates, [-d for d in dd], linewidth=1.2)
    plt.title("Portfolio Underwater (Drawdown)")
    plt.xlabel("Date")
    plt.ylabel("Drawdown")
    plt.axhline(0, linewidth=1, alpha=0.7)
    plt.tight_layout()
    plt.savefig(outdir / "portfolio_underwater.png", dpi=150)
    plt.close()


# =============================================================================
# --- True Equity Plot (broker.getvalue() curve)
# =============================================================================

def save_true_equity_plot(truepd: dict, outdir: Path):
    # True equity curve (cash and holdings) including slippage, liquidation; directly reflects broker value.
    # Plot the *actual* broker equity curve (cash and holdings), including
    # slippage and final liquidation. Ends exactly at final_value.
    dates = list(truepd.get("dates", []))
    values = list(truepd.get("values", []))
    if not dates or not values:
        return

    plt.figure(figsize=(12, 6))
    plt.plot(dates, values, label="True Portfolio Equity (cash + holdings)")
    plt.axhline(values[0], color="gray", linestyle="--", linewidth=1, alpha=0.7,
                label="Starting Equity")
    plt.title("True Portfolio Equity — Includes Slippage and Final Liquidation")
    bankrupt_date = truepd.get("bankrupt_date")
    if bankrupt_date:
        plt.axvline(bankrupt_date, color="red", linestyle="--", linewidth=1.2, label="Bankruptcy")
        plt.text(bankrupt_date, values[0], "Bankruptcy", color="red", rotation=90, va="bottom", ha="right", fontsize=9)

    plt.xlabel("Date")
    plt.ylabel("Portfolio Value")
    plt.legend(loc="best")
    plt.tight_layout()
    plt.savefig(outdir / "true_equity_curve.png", dpi=150)
    plt.close()
