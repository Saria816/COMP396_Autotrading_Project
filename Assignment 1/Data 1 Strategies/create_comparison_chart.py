#!/usr/bin/env python3
"""
创建所有策略的累计收益对比图
"""
import json
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path
import pandas as pd
from datetime import datetime
import numpy as np

# Configure matplotlib for English display
plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

def load_equity_data(output_dir):
    """从run_summary.json加载权益数据"""
    summary_file = Path(output_dir) / "run_summary.json"
    if summary_file.exists():
        with open(summary_file, 'r') as f:
            data = json.load(f)
            return data
    return None

def create_comparison_chart():
    """创建所有策略的对比图"""

    # Strategy configuration
    strategies = [
        {
            "name": "S1: Dual MA (Series 04)",
            "dir": "output/individual_strategies/s1_dual_ma",
            "color": "#1f77b4",
            "linestyle": "-"
        },
        {
            "name": "S2: Buy & Hold (Series 05)",
            "dir": "output/individual_strategies/s2_buy_hold",
            "color": "#2ca02c",
            "linestyle": "-"
        },
        {
            "name": "S3: Mean Reversion (Series 09)",
            "dir": "output/individual_strategies/s3_mean_reversion",
            "color": "#ff7f0e",
            "linestyle": "-"
        },
        {
            "name": "Combined Strategy (CVaR)",
            "dir": "output/combined_strategy",
            "color": "#d62728",
            "linestyle": "-",
            "linewidth": 2.5
        }
    ]

    # 加载所有策略数据
    strategy_data = []
    for strat in strategies:
        data = load_equity_data(strat["dir"])
        if data:
            strat["data"] = data
            strategy_data.append(strat)

    # Create charts
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
    fig.suptitle('BT396 Strategy Backtest Performance Comparison (Full Period Days 1-1000)', fontsize=16, fontweight='bold')

    # Subplot 1: Cumulative Return Comparison
    ax1.set_title('Cumulative Return Comparison', fontsize=13, fontweight='bold')
    ax1.set_xlabel('Strategy', fontsize=11)
    ax1.set_ylabel('Cumulative Return (%)', fontsize=11)
    ax1.grid(True, alpha=0.3, linestyle='--')

    # 绘制柱状图
    names = [s["name"] for s in strategy_data]
    returns = [s["data"]["total_return"] * 100 for s in strategy_data]
    colors = [s["color"] for s in strategy_data]

    bars = ax1.bar(range(len(names)), returns, color=colors, alpha=0.7, edgecolor='black', linewidth=1.5)
    ax1.set_xticks(range(len(names)))
    ax1.set_xticklabels(names, rotation=15, ha='right')

    # 在柱状图上显示数值
    for i, (bar, ret) in enumerate(zip(bars, returns)):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{ret:.2f}%',
                ha='center', va='bottom', fontsize=10, fontweight='bold')

    # Subplot 2: Risk-Adjusted Return Comparison (Sharpe Ratio vs Max Drawdown)
    ax2.set_title('Risk-Adjusted Return Comparison (Annualized Sharpe vs Max Drawdown)', fontsize=13, fontweight='bold')
    ax2.set_xlabel('Max Drawdown (%)', fontsize=11)
    ax2.set_ylabel('Annualized Sharpe Ratio', fontsize=11)
    ax2.grid(True, alpha=0.3, linestyle='--')

    # Draw scatter plot with smart label positioning using arrows
    # Define annotation offset strategies for each strategy to avoid overlaps
    annotation_offsets = {
        "S1: Dual MA (Series 04)": (-20, -50),        # Closer to the point
        "S2: Buy & Hold (Series 05)": (-30, -50),     # Closer to the point
        "S3: Mean Reversion (Series 09)": (15, -40),  # Right and down with arrow
        "Combined Strategy (CVaR)": (-20, -60)        # Closer to the point
    }

    for strat in strategy_data:
        sharpe = strat["data"]["annualized_sharpe"]
        drawdown = strat["data"]["max_drawdown_pct"] * 100

        ax2.scatter(drawdown, sharpe,
                   color=strat["color"],
                   s=200,
                   alpha=0.7,
                   edgecolor='black',
                   linewidth=1.5,
                   label=strat["name"])

        # Add labels with arrows connecting to points
        offset = annotation_offsets.get(strat["name"], (10, 10))
        ax2.annotate(f'{strat["name"]}\nSharpe:{sharpe:.3f}\nDD:{drawdown:.2f}%',
                    xy=(drawdown, sharpe),
                    xytext=offset,
                    textcoords='offset points',
                    fontsize=8,
                    bbox=dict(boxstyle='round,pad=0.5',
                             facecolor=strat["color"],
                             alpha=0.3,
                             edgecolor='black'),
                    arrowprops=dict(arrowstyle='->',
                                   connectionstyle='arc3,rad=0.2',
                                   color='black',
                                   lw=1.5,
                                   alpha=0.7),
                    ha='left' if offset[0] > 0 else 'right')

    ax2.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
    ax2.axvline(x=0, color='gray', linestyle='--', alpha=0.5)

    # Add margins to ensure all annotations are visible
    ax2.margins(x=0.15, y=0.15)

    plt.tight_layout()

    # Save chart
    output_path = Path("output/all_strategies_comparison.png")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"\n✅ Strategy comparison chart generated: {output_path}")

    plt.close()

    # Create detailed performance table
    create_performance_table(strategy_data)

def create_performance_table(strategy_data):
    """Create performance metrics comparison table"""

    fig, ax = plt.subplots(figsize=(14, 6))
    ax.axis('tight')
    ax.axis('off')

    # Prepare table data with abbreviated headers
    headers = ['Strategy Name', 'Final Value', 'Total\nReturn', 'Ann.\nReturn', 'Ann.\nSharpe', 'Max\nDrawdown', 'Trading\nDays']

    table_data = []
    for strat in strategy_data:
        data = strat["data"]
        row = [
            strat["name"],
            f"£{data['final_value']:,.0f}",
            f"{data['total_return']*100:.2f}%",
            f"{data['annualized_return']*100:.2f}%",
            f"{data['annualized_sharpe']:.3f}",
            f"{data['max_drawdown_pct']*100:.2f}%",
            f"{data['trading_days']}"
        ]
        table_data.append(row)

    # 创建表格
    table = ax.table(cellText=table_data,
                    colLabels=headers,
                    cellLoc='center',
                    loc='center',
                    colWidths=[0.25, 0.12, 0.11, 0.12, 0.13, 0.11, 0.10])

    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 2.5)

    # 设置表头样式
    for i in range(len(headers)):
        cell = table[(0, i)]
        cell.set_facecolor('#4472C4')
        cell.set_text_props(weight='bold', color='white')

    # 设置数据行样式
    colors = ['#E7E6E6', '#F2F2F2']
    for i, row in enumerate(table_data):
        for j in range(len(headers)):
            cell = table[(i+1, j)]
            cell.set_facecolor(colors[i % 2])
            cell.set_edgecolor('black')
            cell.set_linewidth(0.5)

    plt.title('BT396 Strategy Performance Comparison Table (Full Period Days 1-1000)',
             fontsize=14, fontweight='bold', pad=20)

    # Save table chart
    output_path = Path("output/all_strategies_performance_table.png")
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"✅ Performance table generated: {output_path}")

    plt.close()

if __name__ == "__main__":
    print("\n" + "="*60)
    print("  Creating All Strategies Comparison Charts")
    print("="*60 + "\n")

    create_comparison_chart()

    print("\n" + "="*60)
    print("  All comparison charts generated successfully!")
    print("="*60 + "\n")

    print("Generated files:")
    print("  1. output/all_strategies_comparison.png - Strategy performance comparison")
    print("  2. output/all_strategies_performance_table.png - Performance metrics table")
    print("\n")
