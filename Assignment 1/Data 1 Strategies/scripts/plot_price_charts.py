#!/usr/bin/env python3
# scripts/plot_price_charts.py
"""
Generate combined price chart for all 10 series using Close prices only.
No individual charts - just the consolidated view.
"""

import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')


def plot_combined_price_chart(data_dir='DATA/PART1', output_dir='output/analysis'):
    """Plot all series in one combined chart using Close prices."""

    data_path = Path(data_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    print("\nGenerating combined price chart...")

    fig, axes = plt.subplots(5, 2, figsize=(18, 16))
    axes = axes.flatten()

    for i in range(1, 11):
        filename = f"{i:02d}.csv"
        filepath = data_path / filename

        if not filepath.exists():
            continue

        df = pd.read_csv(filepath, index_col=0, parse_dates=True)
        series_name = f'Series_{i:02d}'

        idx = i - 1
        axes[idx].plot(df.index, df['Close'], linewidth=1.2, color='#1f77b4')
        axes[idx].set_title(series_name, fontsize=12, fontweight='bold')
        axes[idx].set_xlabel('Date', fontsize=9)
        axes[idx].set_ylabel('Close Price', fontsize=9)
        axes[idx].grid(True, alpha=0.3, linestyle='--')
        axes[idx].tick_params(labelsize=8)

        # Add price change percentage
        start_price = df['Close'].iloc[0]
        end_price = df['Close'].iloc[-1]
        pct_change = ((end_price - start_price) / start_price) * 100

        color = 'green' if pct_change > 0 else 'red'
        axes[idx].text(0.02, 0.98, f'{pct_change:+.1f}%',
                      transform=axes[idx].transAxes,
                      fontsize=10,
                      verticalalignment='top',
                      color=color,
                      fontweight='bold',
                      bbox=dict(boxstyle='round', facecolor='white',
                               edgecolor=color, alpha=0.7))

    plt.suptitle('All Series - Close Price Evolution',
                 fontsize=18, fontweight='bold', y=0.995)
    plt.tight_layout(rect=[0, 0, 1, 0.99])

    output_file = output_path / 'all_series_price_evolution.png'
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()

    print(f"✓ Saved all_series_price_evolution.png")


def main():
    """Generate combined price chart."""
    print("=" * 80)
    print("GENERATING COMBINED PRICE CHART (Close Prices Only)")
    print("=" * 80)
    plot_combined_price_chart()
    print("\n✓ Price chart generation complete!\n")


if __name__ == '__main__':
    main()
