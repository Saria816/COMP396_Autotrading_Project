"""
Generate supplementary charts for the analysis report
Output to research/figures/ directory
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
plt.rcParams['font.size'] = 11
plt.rcParams['figure.dpi'] = 150

from pathlib import Path

# Path settings
DATA_PATH = Path('../BT396_Version_0.1.3/DATA/PART2')
FIGURES_PATH = Path('./figures')
ROBUSTNESS_PATH = Path('./robustness_results')
FIGURES_PATH.mkdir(exist_ok=True)


def load_all_data():
    """Load all 10 asset data"""
    data = {}
    for i in range(1, 11):
        df = pd.read_csv(DATA_PATH / f'{i:02d}.csv')
        date_col = 'Index' if 'Index' in df.columns else 'Date'
        df[date_col] = pd.to_datetime(df[date_col])
        df.set_index(date_col, inplace=True)
        df.sort_index(inplace=True)
        data[f'series_{i}'] = df
    return data


# ============================================================
# Chart 1: Asset Classification Scatter Plot
# ============================================================
def plot_asset_classification():
    """Generate asset classification scatter plot: Total Return vs |Max Drawdown|, colored by classification"""
    df = pd.read_csv(FIGURES_PATH / 'asset_classification.csv')

    # Strategy label mapping
    label_map = {
        'Trend/Momentum': 'Trend/Momentum',
        'Mean Reversion': 'Mean Reversion',
        'Short/Defensive': 'Short/Defensive'
    }
    colors = {
        'Trend/Momentum': '#2196F3',
        'Mean Reversion': '#FF9800',
        'Short/Defensive': '#F44336'
    }
    markers = {
        'Trend/Momentum': 'o',
        'Mean Reversion': 's',
        'Short/Defensive': 'v'
    }

    fig, ax = plt.subplots(figsize=(10, 7))

    for strategy in df['Strategy'].unique():
        sub = df[df['Strategy'] == strategy]
        ax.scatter(
            sub['Max_DD%'].abs(), sub['Total_Return%'],
            c=colors.get(strategy, 'gray'),
            marker=markers.get(strategy, 'o'),
            s=120, label=label_map.get(strategy, strategy),
            edgecolors='black', linewidth=0.8, zorder=3
        )

    # Annotate asset names
    for _, row in df.iterrows():
        ax.annotate(
            row['Series'],
            (abs(row['Max_DD%']), row['Total_Return%']),
            textcoords='offset points', xytext=(8, 5),
            fontsize=9, color='#333333'
        )

    # Draw threshold line: Return/|MaxDD| = 1.1 -> Return = 1.1 * |MaxDD|
    x_line = np.linspace(0, 55, 100)
    ax.plot(x_line, 1.1 * x_line, 'k--', alpha=0.5, linewidth=1.2,
            label='Threshold: Ratio = 1.1')
    ax.plot(x_line, 0 * x_line, 'k-', alpha=0.3, linewidth=0.8)

    ax.set_xlabel('|Maximum Drawdown| (%)', fontsize=12)
    ax.set_ylabel('Total Return (%)', fontsize=12)
    ax.set_title('Asset Classification by Return/Drawdown Ratio', fontsize=14)
    ax.legend(loc='upper left', fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.set_xlim(-2, 55)
    ax.set_ylim(-35, 95)

    plt.tight_layout()
    plt.savefig(FIGURES_PATH / 'asset_classification_scatter.png', bbox_inches='tight')
    plt.close()
    print('✓ asset_classification_scatter.png')


# ============================================================
# Chart 2: Strategy Signal Examples (3 representative assets)
# ============================================================
def plot_strategy_signals(data):
    """Generate strategy signal examples for 3 representative assets"""
    fig, axes = plt.subplots(3, 1, figsize=(14, 12))

    # --- series_4: MA Crossover (ma_crossover, fast=10, slow=30) ---
    ax = axes[0]
    df = data['series_4']
    close = df['Close']
    sma_fast = close.rolling(10).mean()
    sma_slow = close.rolling(30).mean()

    ax.plot(close.index, close.values, color='#555555', linewidth=0.8, alpha=0.7, label='Price')
    ax.plot(close.index, sma_fast.values, color='#2196F3', linewidth=1.2, label='SMA(10)')
    ax.plot(close.index, sma_slow.values, color='#FF9800', linewidth=1.2, label='SMA(30)')

    # Generate golden cross / death cross signals
    buy_dates, buy_prices, sell_dates, sell_prices = [], [], [], []
    for i in range(30, len(close)):
        if sma_fast.iloc[i] > sma_slow.iloc[i] and sma_fast.iloc[i-1] <= sma_slow.iloc[i-1]:
            buy_dates.append(close.index[i])
            buy_prices.append(close.iloc[i])
        elif sma_fast.iloc[i] < sma_slow.iloc[i] and sma_fast.iloc[i-1] >= sma_slow.iloc[i-1]:
            sell_dates.append(close.index[i])
            sell_prices.append(close.iloc[i])

    ax.scatter(buy_dates, buy_prices, marker='^', color='#4CAF50', s=80, zorder=4, label='Buy (Golden Cross)')
    ax.scatter(sell_dates, sell_prices, marker='v', color='#F44336', s=80, zorder=4, label='Sell (Death Cross)')
    ax.set_title('series_4 — MA Crossover Strategy (fast=10, slow=30)', fontsize=12, fontweight='bold')
    ax.legend(loc='upper left', fontsize=9)
    ax.grid(True, alpha=0.3)
    ax.set_ylabel('Price')

    # --- series_2: Z-Score (lookback=20, entry_z=2.0, exit_z=0.0) ---
    ax = axes[1]
    df = data['series_2']
    close = df['Close']
    rolling_mean = close.rolling(20).mean()
    rolling_std = close.rolling(20).std()
    zscore = (close - rolling_mean) / rolling_std

    ax.plot(close.index, close.values, color='#555555', linewidth=0.8, alpha=0.7, label='Price')
    ax.plot(close.index, rolling_mean.values, color='#9C27B0', linewidth=1.2, label='SMA(20)')

    # Z-Score buy/sell signals
    buy_dates, buy_prices, sell_dates, sell_prices = [], [], [], []
    in_position = False
    for i in range(20, len(close)):
        z = zscore.iloc[i]
        if not in_position and z < -2.0:
            buy_dates.append(close.index[i])
            buy_prices.append(close.iloc[i])
            in_position = True
        elif in_position and z > 0.0:
            sell_dates.append(close.index[i])
            sell_prices.append(close.iloc[i])
            in_position = False

    ax.scatter(buy_dates, buy_prices, marker='^', color='#4CAF50', s=80, zorder=4, label='Buy (Z < -2.0)')
    ax.scatter(sell_dates, sell_prices, marker='v', color='#F44336', s=80, zorder=4, label='Sell (Z > 0.0)')
    ax.set_title('series_2 — Z-Score Mean Reversion Strategy (lookback=20, entry=-2.0)', fontsize=12, fontweight='bold')
    ax.legend(loc='upper left', fontsize=9)
    ax.grid(True, alpha=0.3)
    ax.set_ylabel('Price')

    # --- series_5: RSI Short (period=7, overbought=75, oversold=40) ---
    ax = axes[2]
    df = data['series_5']
    close = df['Close']

    # Calculate RSI
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(7).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(7).mean()
    rs = gain / (loss + 1e-10)
    rsi = 100 - (100 / (1 + rs))

    ax.plot(close.index, close.values, color='#555555', linewidth=0.8, alpha=0.7, label='Price')

    # RSI short signals
    short_dates, short_prices, cover_dates, cover_prices = [], [], [], []
    in_short = False
    for i in range(8, len(close)):
        r = rsi.iloc[i]
        if not in_short and r > 75:
            short_dates.append(close.index[i])
            short_prices.append(close.iloc[i])
            in_short = True
        elif in_short and (r < 40 or r < 50):
            cover_dates.append(close.index[i])
            cover_prices.append(close.iloc[i])
            in_short = False

    ax.scatter(short_dates, short_prices, marker='v', color='#F44336', s=80, zorder=4, label='Short (RSI > 75)')
    ax.scatter(cover_dates, cover_prices, marker='^', color='#4CAF50', s=80, zorder=4, label='Cover (RSI < 50)')
    ax.set_title('series_5 — RSI Short Strategy (period=7, overbought=75)', fontsize=12, fontweight='bold')
    ax.legend(loc='upper left', fontsize=9)
    ax.grid(True, alpha=0.3)
    ax.set_ylabel('Price')
    ax.set_xlabel('Date')

    plt.tight_layout()
    plt.savefig(FIGURES_PATH / 'strategy_signals_example.png', bbox_inches='tight')
    plt.close()
    print('✓ strategy_signals_example.png')


# ============================================================
# Chart 3: Rolling Window Return Bar Chart
# ============================================================
def plot_rolling_window():
    """Generate rolling window return bar chart"""
    df = pd.read_csv(ROBUSTNESS_PATH / 'rolling_window_test.csv')

    fig, ax = plt.subplots(figsize=(10, 5.5))

    windows = df['Window'].values
    returns = df['Return(%)'].values
    colors = ['#F44336' if r < 0 else '#4CAF50' for r in returns]

    bars = ax.bar(windows, returns, color=colors, edgecolor='black', linewidth=0.5, width=0.6)

    # Annotate values on top of bars
    for bar, ret in zip(bars, returns):
        y = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, y + 0.3,
                f'{ret:.1f}%', ha='center', va='bottom', fontsize=9)

    ax.axhline(y=0, color='black', linewidth=0.8)

    # Mark mean line
    mean_ret = np.mean(returns)
    ax.axhline(y=mean_ret, color='#2196F3', linewidth=1.5, linestyle='--',
               label=f'Mean: {mean_ret:.1f}%')

    ax.set_xlabel('Rolling Window (6 months)', fontsize=12)
    ax.set_ylabel('Return (%)', fontsize=12)
    ax.set_title('Rolling Window Test Results (6-Month Windows)', fontsize=14)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    plt.savefig(FIGURES_PATH / 'rolling_window_returns.png', bbox_inches='tight')
    plt.close()
    print('✓ rolling_window_returns.png')


# ============================================================
# Chart 4: Allocation Sensitivity Analysis
# ============================================================
def plot_allocation_sensitivity():
    """Generate PD Ratio and Return dual-axis line chart"""
    df = pd.read_csv(ROBUSTNESS_PATH / 'allocation_sensitivity.csv')

    # Extract trend allocation percentages
    trend_pcts = []
    for val in df['Trend Allocation']:
        trend_pcts.append(int(val.replace('%', '')))

    fig, ax1 = plt.subplots(figsize=(9, 5.5))

    color_return = '#2196F3'
    color_pd = '#FF9800'

    # Left axis: Return
    ax1.set_xlabel('Trend Allocation (%)', fontsize=12)
    ax1.set_ylabel('Return (%)', fontsize=12, color=color_return)
    line1 = ax1.plot(trend_pcts, df['Return(%)'].values, 'o-',
                     color=color_return, linewidth=2, markersize=8, label='Return (%)')
    ax1.tick_params(axis='y', labelcolor=color_return)

    # Annotate current allocation
    current_idx = df[df['Allocation'].str.contains('Current')].index[0]
    ax1.annotate('Current\n(70/30)',
                 xy=(trend_pcts[current_idx], df['Return(%)'].iloc[current_idx]),
                 xytext=(trend_pcts[current_idx] - 8, df['Return(%)'].iloc[current_idx] + 3),
                 arrowprops=dict(arrowstyle='->', color='gray'),
                 fontsize=10, color='gray', fontweight='bold')

    # Right axis: PD Ratio
    ax2 = ax1.twinx()
    ax2.set_ylabel('True PD Ratio', fontsize=12, color=color_pd)
    line2 = ax2.plot(trend_pcts, df['True PD Ratio'].values, 's--',
                     color=color_pd, linewidth=2, markersize=8, label='True PD Ratio')
    ax2.tick_params(axis='y', labelcolor=color_pd)
    pd_min = df['True PD Ratio'].min()
    pd_max = df['True PD Ratio'].max()
    ax2.set_ylim(pd_min - 0.1, pd_max + 0.1)

    # Merge legends
    lines = line1 + line2
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc='center left', fontsize=10)

    ax1.set_title('Allocation Sensitivity: Return vs PD Ratio', fontsize=14)
    ax1.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(FIGURES_PATH / 'allocation_sensitivity.png', bbox_inches='tight')
    plt.close()
    print('✓ allocation_sensitivity.png')


# ============================================================
# Chart 5: Strategy Component Test Comparison
# ============================================================
def plot_component_test():
    """Generate strategy component comparison bar chart"""
    df = pd.read_csv(ROBUSTNESS_PATH / 'component_test.csv')

    labels = ['Trend Only', 'Others Only', '70/30 Mix\n(Current)']
    returns = df['Return(%)'].values
    pd_ratios = df['True PD Ratio'].values

    x = np.arange(len(labels))
    width = 0.35

    fig, ax1 = plt.subplots(figsize=(9, 5.5))

    bars1 = ax1.bar(x - width/2, returns, width, label='Return (%)',
                    color='#2196F3', edgecolor='black', linewidth=0.5)
    ax1.set_ylabel('Return (%)', fontsize=12, color='#2196F3')
    ax1.tick_params(axis='y', labelcolor='#2196F3')

    # Annotate values on top of bars
    for bar, val in zip(bars1, returns):
        y = bar.get_height()
        offset = 0.5 if y >= 0 else -1.5
        ax1.text(bar.get_x() + bar.get_width()/2, y + offset,
                 f'{val:.1f}%', ha='center', va='bottom', fontsize=10, fontweight='bold')

    ax2 = ax1.twinx()
    bars2 = ax2.bar(x + width/2, pd_ratios, width, label='True PD Ratio',
                    color='#FF9800', edgecolor='black', linewidth=0.5)
    ax2.set_ylabel('True PD Ratio', fontsize=12, color='#FF9800')
    ax2.tick_params(axis='y', labelcolor='#FF9800')

    for bar, val in zip(bars2, pd_ratios):
        y = bar.get_height()
        offset = 0.05 if y >= 0 else -0.15
        ax2.text(bar.get_x() + bar.get_width()/2, y + offset,
                 f'{val:.2f}', ha='center', va='bottom', fontsize=10, fontweight='bold')

    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, fontsize=11)
    ax1.set_title('Strategy Component Test: Return and PD Ratio', fontsize=14)
    ax1.axhline(y=0, color='black', linewidth=0.8)

    # Merge legends to upper center
    handles1, labels1 = ax1.get_legend_handles_labels()
    handles2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(handles1 + handles2, labels1 + labels2,
               loc='upper center', fontsize=10, ncol=2,
               bbox_to_anchor=(0.5, 0.95))

    ax1.grid(True, alpha=0.3, axis='y')
    plt.tight_layout()
    plt.savefig(FIGURES_PATH / 'component_test_comparison.png', bbox_inches='tight')
    plt.close()
    print('✓ component_test_comparison.png')


# ============================================================
# Main
# ============================================================
def main():
    print('='*60)
    print('Generating Supplementary Report Charts')
    print('='*60)

    data = load_all_data()
    print(f'Loaded {len(data)} asset data\n')

    plot_asset_classification()
    plot_strategy_signals(data)
    plot_rolling_window()
    plot_allocation_sensitivity()
    plot_component_test()

    print(f'\nAll charts saved to {FIGURES_PATH}/')


if __name__ == '__main__':
    main()
