"""
Generate supplementary charts for Part 3 analysis report.
Output to research/figures_part3/ directory.

Charts generated:
  1. per_asset_pnl_bar.png       - Per-asset PnL contribution bar chart
  2. asset_return_comparison.png  - Part 2 vs Part 3 asset return comparison
  3. classification_drift.png    - Asset classification drift (Return/MaxDD Ratio)
  4. strategy_type_pie.png       - Strategy type PnL contribution pie chart
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
import json
matplotlib.use('Agg')
plt.rcParams['font.size'] = 11
plt.rcParams['figure.dpi'] = 150

from pathlib import Path

# Path settings
DATA_P2 = Path('../BT396_Version_0.1.3/DATA/PART2')
DATA_P3 = Path('../BT396_Version_0.1.3/DATA/PART3')
OUTPUT_P3 = Path('../BT396_Version_0.1.3/output_part3')
FIGURES_PATH = Path('./figures_part3')
FIGURES_PATH.mkdir(exist_ok=True)

# Asset config
TREND_ASSETS = ['series_1', 'series_3', 'series_4', 'series_6', 'series_9']
MR_ASSETS = ['series_2', 'series_7', 'series_8', 'series_10']
SHORT_ASSETS = ['series_5']

STRATEGY_MAP = {
    'series_1': 'breakout', 'series_2': 'zscore', 'series_3': 'above_ma',
    'series_4': 'ma_crossover', 'series_5': 'rsi_short', 'series_6': 'above_ma',
    'series_7': 'bollinger', 'series_8': 'rsi', 'series_9': 'above_ma',
    'series_10': 'zscore'
}


def load_per_series_pd():
    """Load Part 3 per-series PD data"""
    with open(OUTPUT_P3 / 'per_series_pd.json') as f:
        data = json.load(f)
    return {item['series']: item for item in data if item['series'] != 'portfolio'}


def load_asset_returns(data_path):
    """Load close prices and compute returns for all assets"""
    results = {}
    for i in range(1, 11):
        df = pd.read_csv(data_path / f'{i:02d}.csv')
        close = df['Close']
        total_return = (close.iloc[-1] / close.iloc[0] - 1) * 100
        cummax = close.cummax()
        max_dd = ((close - cummax) / cummax).min() * 100
        ratio = abs(total_return / max_dd) if max_dd != 0 else 0
        results[f'series_{i}'] = {
            'return': total_return,
            'max_dd': max_dd,
            'ratio': ratio
        }
    return results


def plot_per_asset_pnl():
    """Chart 1: Per-asset PnL contribution bar chart (waterfall style)"""
    pd_data = load_per_series_pd()

    # Sort by PnL descending
    sorted_assets = sorted(pd_data.keys(), key=lambda x: pd_data[x]['final_cumPnL'], reverse=True)
    names = [s.replace('series_', 'S') for s in sorted_assets]
    pnls = [pd_data[s]['final_cumPnL'] for s in sorted_assets]

    # Color by strategy type
    colors = []
    for s in sorted_assets:
        if s in TREND_ASSETS:
            colors.append('#2196F3' if pd_data[s]['final_cumPnL'] >= 0 else '#90CAF9')
        elif s in MR_ASSETS:
            colors.append('#4CAF50' if pd_data[s]['final_cumPnL'] >= 0 else '#A5D6A7')
        else:
            colors.append('#FF9800' if pd_data[s]['final_cumPnL'] >= 0 else '#FFCC80')

    fig, ax = plt.subplots(figsize=(10, 5.5))
    bars = ax.bar(names, [p / 1000 for p in pnls], color=colors, edgecolor='white', linewidth=0.5)

    # Add value labels
    for bar, pnl in zip(bars, pnls):
        y = bar.get_height()
        label = f'{pnl/1000:+.1f}k'
        va = 'bottom' if y >= 0 else 'top'
        offset = 2 if y >= 0 else -2
        ax.text(bar.get_x() + bar.get_width()/2, y + offset, label,
                ha='center', va=va, fontsize=9, fontweight='bold')

    ax.axhline(y=0, color='black', linewidth=0.8)
    ax.set_ylabel('PnL (thousands)')
    ax.set_title('Part 3: Per-Asset PnL Contribution')

    # Legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#2196F3', label='Trend/Momentum'),
        Patch(facecolor='#4CAF50', label='Mean Reversion'),
        Patch(facecolor='#FF9800', label='Short/Defensive'),
    ]
    ax.legend(handles=legend_elements, loc='upper right', fontsize=9)

    ax.set_xlabel('Asset')
    ax.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    plt.savefig(FIGURES_PATH / 'per_asset_pnl_bar.png')
    plt.close()
    print(f"  Saved: {FIGURES_PATH / 'per_asset_pnl_bar.png'}")


def plot_asset_return_comparison():
    """Chart 2: Part 2 vs Part 3 asset return comparison (grouped bar)"""
    p2_data = load_asset_returns(DATA_P2)
    p3_data = load_asset_returns(DATA_P3)

    assets = [f'series_{i}' for i in range(1, 11)]
    names = [s.replace('series_', 'S') for s in assets]
    p2_rets = [p2_data[s]['return'] for s in assets]
    p3_rets = [p3_data[s]['return'] for s in assets]

    x = np.arange(len(names))
    width = 0.35

    fig, ax = plt.subplots(figsize=(11, 5.5))
    bars1 = ax.bar(x - width/2, p2_rets, width, label='Part 2', color='#42A5F5', alpha=0.85)
    bars2 = ax.bar(x + width/2, p3_rets, width, label='Part 3', color='#EF5350', alpha=0.85)

    ax.set_ylabel('Total Return (%)')
    ax.set_title('Asset Total Returns: Part 2 vs Part 3')
    ax.set_xticks(x)
    ax.set_xticklabels(names)
    ax.legend(fontsize=10)
    ax.axhline(y=0, color='black', linewidth=0.8)
    ax.grid(axis='y', alpha=0.3)

    # Add value labels on bars
    for bar in bars1:
        h = bar.get_height()
        if abs(h) > 5:
            ax.text(bar.get_x() + bar.get_width()/2, h + (1.5 if h >= 0 else -4),
                    f'{h:.0f}%', ha='center', va='bottom' if h >= 0 else 'top', fontsize=7.5)
    for bar in bars2:
        h = bar.get_height()
        if abs(h) > 5:
            ax.text(bar.get_x() + bar.get_width()/2, h + (1.5 if h >= 0 else -4),
                    f'{h:.0f}%', ha='center', va='bottom' if h >= 0 else 'top', fontsize=7.5)

    # Extend y-axis lower bound to avoid label clipping at bottom edge
    ymin, ymax = ax.get_ylim()
    ax.set_ylim(ymin - 8, ymax)

    plt.tight_layout()
    plt.savefig(FIGURES_PATH / 'asset_return_comparison.png')
    plt.close()
    print(f"  Saved: {FIGURES_PATH / 'asset_return_comparison.png'}")


def plot_classification_drift():
    """Chart 3: Asset classification drift scatter (Return/MaxDD Ratio)"""
    p2_data = load_asset_returns(DATA_P2)
    p3_data = load_asset_returns(DATA_P3)

    assets = [f'series_{i}' for i in range(1, 11)]
    names = [s.replace('series_', 'S') for s in assets]

    p2_ratios = [p2_data[s]['ratio'] for s in assets]
    p3_ratios = [p3_data[s]['ratio'] for s in assets]

    x = np.arange(len(names))

    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.scatter(x, p2_ratios, s=100, c='#42A5F5', marker='o', label='Part 2', zorder=3, edgecolors='white')
    ax.scatter(x, p3_ratios, s=100, c='#EF5350', marker='D', label='Part 3', zorder=3, edgecolors='white')

    # Draw arrows showing drift
    for i in range(len(assets)):
        ax.annotate('', xy=(x[i], p3_ratios[i]), xytext=(x[i], p2_ratios[i]),
                     arrowprops=dict(arrowstyle='->', color='gray', alpha=0.5, lw=1.2))

    # Threshold line
    ax.axhline(y=1.1, color='green', linestyle='--', linewidth=1.5, alpha=0.7, label='Threshold = 1.1')

    # Highlight changed assets
    for i, s in enumerate(assets):
        p2_class = 'trend' if p2_ratios[i] >= 1.1 else 'other'
        p3_class = 'trend' if p3_ratios[i] >= 1.1 else 'other'
        if p2_class != p3_class:
            ax.axvspan(x[i] - 0.4, x[i] + 0.4, alpha=0.1, color='red')

    ax.set_xticks(x)
    ax.set_xticklabels(names)
    ax.set_ylabel('Return / |MaxDD| Ratio')
    ax.set_title('Asset Classification Drift: Part 2 → Part 3')
    ax.legend(fontsize=9, loc='upper left')
    ax.grid(axis='y', alpha=0.3)
    ax.set_ylim(bottom=-0.2)

    plt.tight_layout()
    plt.savefig(FIGURES_PATH / 'classification_drift.png')
    plt.close()
    print(f"  Saved: {FIGURES_PATH / 'classification_drift.png'}")


def plot_strategy_type_pie():
    """Chart 4: Strategy type PnL contribution pie chart"""
    pd_data = load_per_series_pd()

    trend_pnl = sum(pd_data[s]['final_cumPnL'] for s in TREND_ASSETS)
    mr_pnl = sum(pd_data[s]['final_cumPnL'] for s in MR_ASSETS)
    short_pnl = sum(pd_data[s]['final_cumPnL'] for s in SHORT_ASSETS)

    sizes = [abs(trend_pnl), abs(mr_pnl), abs(short_pnl)]
    colors = ['#2196F3', '#4CAF50', '#FF9800']
    explode = (0.05, 0, 0)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.5))

    # Left: Pie chart — use legend instead of inline labels to avoid overlap
    wedges, texts, autotexts = ax1.pie(sizes, colors=colors,
                                        explode=explode, autopct='',
                                        startangle=90)
    # External legend to avoid label overlap on tiny slices
    legend_labels = [
        f'Trend/Momentum: +{trend_pnl/1000:.1f}k (100.3%)',
        f'Mean Reversion: +{mr_pnl/1000:.1f}k (1.0%)',
        f'Short/Defensive: {short_pnl/1000:.1f}k (-1.3%)',
    ]
    ax1.legend(wedges, legend_labels, loc='lower center', bbox_to_anchor=(0.5, -0.15),
               fontsize=9, frameon=False)
    ax1.set_title('PnL by Strategy Type', fontsize=12)

    # Right: Stacked bar showing Part 2 component test vs Part 3 actual
    categories = ['Part 2\n(Component Test)', 'Part 3\n(Actual)']
    # Part 2 component test data (from robustness test)
    p2_trend_ret = 29.77
    p2_other_ret = -2.23
    # Part 3 actual
    total_pnl = trend_pnl + mr_pnl + short_pnl
    p3_trend_pct = trend_pnl / 10000  # approximate % of 1M
    p3_other_pct = (mr_pnl + short_pnl) / 10000

    bar_width = 0.5
    ax2.bar(categories, [p2_trend_ret, p3_trend_pct], bar_width,
            label='Trend', color='#2196F3', alpha=0.85)
    ax2.bar(categories, [p2_other_ret, p3_other_pct], bar_width,
            bottom=[p2_trend_ret, p3_trend_pct],
            label='MR + Short', color='#4CAF50', alpha=0.85)

    # Add total labels
    p2_total = p2_trend_ret + p2_other_ret
    p3_total = p3_trend_pct + p3_other_pct
    ax2.text(0, p2_total + 1, f'Total: {p2_total:.1f}%', ha='center', fontweight='bold', fontsize=9)
    ax2.text(1, p3_total + 1, f'Total: {p3_total:.1f}%', ha='center', fontweight='bold', fontsize=9)

    ax2.set_ylabel('Return Contribution (%)')
    ax2.set_title('Strategy Contribution: Part 2 vs Part 3', fontsize=12, pad=15)
    ax2.legend(fontsize=9)
    ax2.grid(axis='y', alpha=0.3)
    ax2.axhline(y=0, color='black', linewidth=0.5)

    # Extend y-axis upper bound to avoid bar/label clipping against top edge
    ymin, ymax = ax2.get_ylim()
    ax2.set_ylim(ymin, ymax + 8)

    plt.tight_layout()
    plt.savefig(FIGURES_PATH / 'strategy_type_pie.png')
    plt.close()
    print(f"  Saved: {FIGURES_PATH / 'strategy_type_pie.png'}")


def main():
    print("=" * 60)
    print("Part 3 Report Figure Generation")
    print(f"Output directory: {FIGURES_PATH.resolve()}")
    print("=" * 60)

    print("\n1. Per-asset PnL contribution bar chart...")
    plot_per_asset_pnl()

    print("\n2. Part 2 vs Part 3 asset return comparison...")
    plot_asset_return_comparison()

    print("\n3. Asset classification drift scatter...")
    plot_classification_drift()

    print("\n4. Strategy type PnL contribution...")
    plot_strategy_type_pie()

    print("\n" + "=" * 60)
    print(f"All 4 charts saved to: {FIGURES_PATH.resolve()}")
    print("=" * 60)


if __name__ == "__main__":
    main()
