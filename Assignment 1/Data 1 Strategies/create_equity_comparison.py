#!/usr/bin/env python3
"""
Create cumulative return time series comparison charts for all strategies
"""

import json
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path
import pandas as pd
from datetime import datetime
import numpy as np

# Configure matplotlib font display (English only)
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False

def load_equity_curve(output_dir):
    """Load equity curve data from run_summary.json"""
    summary_file = Path(output_dir) / "run_summary.json"
    if summary_file.exists():
        with open(summary_file, 'r') as f:
            data = json.load(f)
            return data
    return None

def create_cumulative_return_comparison():
    """Create cumulative return time series comparison chart"""

    # Strategy configuration
    strategies = [
        {
            "name": "S1: Dual MA Strategy",
            "dir": "output/individual_strategies/s1_dual_ma",
            "color": "#1f77b4",
            "linestyle": "-",
            "linewidth": 2
        },
        {
            "name": "S2: Buy and Hold",
            "dir": "output/individual_strategies/s2_buy_hold",
            "color": "#2ca02c",
            "linestyle": "-",
            "linewidth": 2
        },
        {
            "name": "S3: Mean Reversion",
            "dir": "output/individual_strategies/s3_mean_reversion",
            "color": "#ff7f0e",
            "linestyle": "-",
            "linewidth": 2
        },
        {
            "name": "Combined Strategy (CVaR)",
            "dir": "output/combined_strategy",
            "color": "#d62728",
            "linestyle": "-",
            "linewidth": 3
        }
    ]

    # Detect actual data length from first strategy
    max_days = 0
    for strat in strategies:
        data = load_equity_curve(strat["dir"])
        if data and "equity_curve" in data:
            equity_curve = data["equity_curve"]
            max_days = max(max_days, len(equity_curve))

    # Determine title based on data length
    if max_days > 900:
        title_period = "Full Period Days 1-1000"
    elif max_days > 250:
        title_period = f"Test Period Days 701-1000 ({max_days} trading days)"
    else:
        title_period = f"{max_days} trading days"

    # Create chart
    fig, ax = plt.subplots(figsize=(14, 8))
    fig.suptitle(f'BT396 Strategy Cumulative Return Comparison ({title_period})',
                 fontsize=16, fontweight='bold', y=0.98)

    ax.set_title('Time Series Cumulative Return Curves', fontsize=13, fontweight='bold', pad=15)
    ax.set_xlabel('Trading Days', fontsize=11)
    ax.set_ylabel('Cumulative Return (%)', fontsize=11)
    ax.grid(True, alpha=0.3, linestyle='--')

    # Load and plot equity curve for each strategy
    for strat in strategies:
        data = load_equity_curve(strat["dir"])
        if data and "equity_curve" in data:
            equity_curve = data["equity_curve"]

            # Calculate cumulative returns
            initial_value = equity_curve[0]
            cumulative_returns = [(v / initial_value - 1) * 100 for v in equity_curve]

            # Create trading day sequence
            trading_days = list(range(1, len(cumulative_returns) + 1))

            # Plot curve
            ax.plot(trading_days, cumulative_returns,
                   label=strat["name"],
                   color=strat["color"],
                   linestyle=strat["linestyle"],
                   linewidth=strat["linewidth"],
                   alpha=0.9)

            # Annotate final return at endpoint
            final_return = cumulative_returns[-1]
            ax.annotate(f'{final_return:.2f}%',
                       xy=(trading_days[-1], final_return),
                       xytext=(10, 0),
                       textcoords='offset points',
                       fontsize=9,
                       fontweight='bold',
                       color=strat["color"],
                       bbox=dict(boxstyle='round,pad=0.3',
                                facecolor='white',
                                edgecolor=strat["color"],
                                alpha=0.8))

    # Add zero line
    ax.axhline(y=0, color='gray', linestyle='--', alpha=0.5, linewidth=1)

    # Set legend
    ax.legend(loc='upper left', fontsize=11, framealpha=0.9)

    # Optimize x-axis display based on actual data length
    ax.set_xlim(0, max_days + 10)

    plt.tight_layout()

    # Save chart
    output_path = Path("output/all_strategies_equity_comparison.png")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"\nEquity comparison chart generated: {output_path}")

    plt.close()

def create_detailed_comparison_dashboard():
    """Create detailed strategy comparison dashboard"""

    # Strategy configuration
    strategies = [
        {
            "name": "S1: Dual MA",
            "dir": "output/individual_strategies/s1_dual_ma",
            "color": "#1f77b4"
        },
        {
            "name": "S2: Buy & Hold",
            "dir": "output/individual_strategies/s2_buy_hold",
            "color": "#2ca02c"
        },
        {
            "name": "S3: Mean Rev",
            "dir": "output/individual_strategies/s3_mean_reversion",
            "color": "#ff7f0e"
        },
        {
            "name": "Combined",
            "dir": "output/combined_strategy",
            "color": "#d62728"
        }
    ]

    # Load all strategy data
    strategy_data = []
    for strat in strategies:
        data = load_equity_curve(strat["dir"])
        if data:
            strat["data"] = data
            strategy_data.append(strat)

    # Create 2x2 dashboard
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('BT396 Strategy Performance Dashboard', fontsize=16, fontweight='bold')

    # Subplot 1: Total returns comparison
    ax1.set_title('Total Returns', fontsize=12, fontweight='bold')
    names = [s["name"] for s in strategy_data]
    returns = [s["data"]["total_return"] * 100 for s in strategy_data]
    colors = [s["color"] for s in strategy_data]

    bars = ax1.bar(range(len(names)), returns, color=colors, alpha=0.7, edgecolor='black')
    ax1.set_xticks(range(len(names)))
    ax1.set_xticklabels(names, rotation=15, ha='right')
    ax1.set_ylabel('Return (%)', fontsize=10)
    ax1.grid(True, alpha=0.3, axis='y')

    for bar, ret in zip(bars, returns):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{ret:.2f}%', ha='center', va='bottom', fontsize=9, fontweight='bold')

    # Subplot 2: Sharpe ratio comparison
    ax2.set_title('Annualized Sharpe Ratio', fontsize=12, fontweight='bold')
    sharpe_ratios = [s["data"]["annualized_sharpe"] for s in strategy_data]

    bars = ax2.bar(range(len(names)), sharpe_ratios, color=colors, alpha=0.7, edgecolor='black')
    ax2.set_xticks(range(len(names)))
    ax2.set_xticklabels(names, rotation=15, ha='right')
    ax2.set_ylabel('Sharpe Ratio', fontsize=10)
    ax2.grid(True, alpha=0.3, axis='y')
    ax2.axhline(y=0, color='gray', linestyle='--', alpha=0.5)

    for bar, sharpe in zip(bars, sharpe_ratios):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{sharpe:.3f}', ha='center', va='bottom', fontsize=9, fontweight='bold')

    # Subplot 3: Maximum drawdown comparison
    ax3.set_title('Maximum Drawdown', fontsize=12, fontweight='bold')
    max_drawdowns = [s["data"]["max_drawdown_pct"] * 100 for s in strategy_data]

    bars = ax3.bar(range(len(names)), max_drawdowns, color=colors, alpha=0.7, edgecolor='black')
    ax3.set_xticks(range(len(names)))
    ax3.set_xticklabels(names, rotation=15, ha='right')
    ax3.set_ylabel('Max Drawdown (%)', fontsize=10)
    ax3.grid(True, alpha=0.3, axis='y')

    for bar, dd in zip(bars, max_drawdowns):
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2., height,
                f'{dd:.2f}%', ha='center', va='bottom', fontsize=9, fontweight='bold')

    # Subplot 4: Risk-Return scatter plot
    ax4.set_title('Risk-Return Profile (Sharpe vs Drawdown)', fontsize=12, fontweight='bold')
    ax4.set_xlabel('Max Drawdown (%)', fontsize=10)
    ax4.set_ylabel('Annualized Sharpe Ratio', fontsize=10)
    ax4.grid(True, alpha=0.3)

    for strat in strategy_data:
        sharpe = strat["data"]["annualized_sharpe"]
        drawdown = strat["data"]["max_drawdown_pct"] * 100

        ax4.scatter(drawdown, sharpe,
                   color=strat["color"],
                   s=250,
                   alpha=0.7,
                   edgecolor='black',
                   linewidth=1.5,
                   label=strat["name"])

        ax4.annotate(strat["name"],
                    xy=(drawdown, sharpe),
                    xytext=(10, 10),
                    textcoords='offset points',
                    fontsize=8,
                    bbox=dict(boxstyle='round,pad=0.4',
                             facecolor=strat["color"],
                             alpha=0.3,
                             edgecolor='black'))

    ax4.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
    ax4.axvline(x=0, color='gray', linestyle='--', alpha=0.5)

    plt.tight_layout()

    # Save chart
    output_path = Path("output/all_strategies_dashboard.png")
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"Dashboard generated: {output_path}")

    plt.close()

if __name__ == "__main__":
    print("\n" + "="*60)
    print("  Creating Strategy Comparison Charts")
    print("="*60 + "\n")

    create_cumulative_return_comparison()
    create_detailed_comparison_dashboard()

    print("\n" + "="*60)
    print("  All comparison charts generated successfully!")
    print("="*60 + "\n")

    print("Generated files:")
    print("  1. output/all_strategies_equity_comparison.png - Time series cumulative returns")
    print("  2. output/all_strategies_dashboard.png - Comprehensive dashboard")
    print("\n")
