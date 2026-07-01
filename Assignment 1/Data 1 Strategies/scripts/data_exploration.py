#!/usr/bin/env python3
# scripts/data_exploration.py
"""
Data exploration and analysis for BT001 trading strategies.
Analyzes 10 CSV files to identify market characteristics for strategy selection.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from scipy import stats
from statsmodels.tsa.stattools import adfuller, acf
import warnings
warnings.filterwarnings('ignore')

# Set style
sns.set_style('whitegrid')
plt.rcParams['figure.figsize'] = (15, 10)

class DataExplorer:
    """Explore and analyze trading data to identify strategy opportunities."""

    def __init__(self, data_dir='DATA/PART1', output_dir='output/analysis'):
        self.data_dir = Path(data_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.data_dict = {}
        self.analysis_results = {}

    def load_data(self):
        """Load all 10 CSV files."""
        print("=" * 80)
        print("LOADING DATA")
        print("=" * 80)

        for i in range(1, 11):
            filename = f"{i:02d}.csv"
            filepath = self.data_dir / filename

            if filepath.exists():
                df = pd.read_csv(filepath, index_col=0, parse_dates=True)
                self.data_dict[f'Series_{i:02d}'] = df
                print(f"✓ Loaded {filename}: {len(df)} rows, "
                      f"Date range: {df.index[0]} to {df.index[-1]}")
            else:
                print(f"✗ File not found: {filename}")

        print(f"\nTotal series loaded: {len(self.data_dict)}\n")
        return self

    def calculate_returns(self):
        """Calculate daily returns for all series."""
        print("Calculating daily returns...")
        for name, df in self.data_dict.items():
            df['Returns'] = df['Close'].pct_change()
            df['Log_Returns'] = np.log(df['Close'] / df['Close'].shift(1))
        print("✓ Returns calculated\n")
        return self

    def basic_statistics(self):
        """Calculate basic statistics for each series."""
        print("=" * 80)
        print("BASIC STATISTICS")
        print("=" * 80)

        stats_list = []
        for name, df in self.data_dict.items():
            returns = df['Returns'].dropna()

            stat = {
                'Series': name,
                'Count': len(df),
                'Mean_Return': returns.mean() * 100,  # percentage
                'Std_Return': returns.std() * 100,
                'Sharpe_Ratio': (returns.mean() / returns.std() * np.sqrt(252)) if returns.std() > 0 else 0,
                'Min_Price': df['Close'].min(),
                'Max_Price': df['Close'].max(),
                'Price_Range': df['Close'].max() - df['Close'].min(),
                'Skewness': returns.skew(),
                'Kurtosis': returns.kurtosis(),
            }
            stats_list.append(stat)

        stats_df = pd.DataFrame(stats_list)
        print(stats_df.to_string(index=False))
        print()

        # Save to CSV
        stats_df.to_csv(self.output_dir / 'basic_statistics.csv', index=False)
        self.analysis_results['basic_stats'] = stats_df
        return self

    def test_mean_reversion(self):
        """Test for mean-reversion using ADF test and Hurst exponent."""
        print("=" * 80)
        print("MEAN-REVERSION TESTS")
        print("=" * 80)

        results_list = []
        for name, df in self.data_dict.items():
            prices = df['Close'].dropna()

            # ADF test (lower p-value = more stationary = mean-reverting)
            adf_result = adfuller(prices, autolag='AIC')
            adf_pvalue = adf_result[1]
            is_stationary = adf_pvalue < 0.05

            # Hurst exponent (H < 0.5 = mean-reverting, H > 0.5 = trending)
            hurst = self._calculate_hurst(prices.values)

            # Half-life of mean reversion
            half_life = self._calculate_half_life(prices.values)

            result = {
                'Series': name,
                'ADF_Statistic': adf_result[0],
                'ADF_pValue': adf_pvalue,
                'Is_Stationary': is_stationary,
                'Hurst_Exponent': hurst,
                'Mean_Reverting': hurst < 0.5,
                'Half_Life': half_life,
            }
            results_list.append(result)

        mr_df = pd.DataFrame(results_list)
        print(mr_df.to_string(index=False))
        print()

        # Identify mean-reverting series
        mr_series = mr_df[mr_df['Hurst_Exponent'] < 0.5]['Series'].tolist()
        print(f"Mean-reverting series (Hurst < 0.5): {mr_series}\n")

        mr_df.to_csv(self.output_dir / 'mean_reversion_tests.csv', index=False)
        self.analysis_results['mean_reversion'] = mr_df
        return self

    def test_trend_following(self):
        """Test for trend-following characteristics using autocorrelation."""
        print("=" * 80)
        print("TREND-FOLLOWING TESTS")
        print("=" * 80)

        results_list = []
        for name, df in self.data_dict.items():
            returns = df['Returns'].dropna()

            # Autocorrelation at different lags
            acf_values = acf(returns, nlags=20, fft=False)
            acf_1 = acf_values[1]  # lag 1
            acf_5 = acf_values[5]  # lag 5
            acf_10 = acf_values[10]  # lag 10

            # Momentum: avg return when previous return was positive
            momentum_score = self._calculate_momentum(returns)

            result = {
                'Series': name,
                'ACF_Lag1': acf_1,
                'ACF_Lag5': acf_5,
                'ACF_Lag10': acf_10,
                'Momentum_Score': momentum_score,
                'Trend_Potential': acf_1 > 0.05 or momentum_score > 0,
            }
            results_list.append(result)

        trend_df = pd.DataFrame(results_list)
        print(trend_df.to_string(index=False))
        print()

        # Identify trending series
        trend_series = trend_df[trend_df['Trend_Potential'] == True]['Series'].tolist()
        print(f"Trending series (positive ACF or momentum): {trend_series}\n")

        trend_df.to_csv(self.output_dir / 'trend_following_tests.csv', index=False)
        self.analysis_results['trend_following'] = trend_df
        return self

    def analyze_volatility(self):
        """Analyze volatility patterns."""
        print("=" * 80)
        print("VOLATILITY ANALYSIS")
        print("=" * 80)

        results_list = []
        for name, df in self.data_dict.items():
            returns = df['Returns'].dropna()

            # Rolling volatility
            df['Rolling_Vol_20'] = returns.rolling(window=20).std()

            result = {
                'Series': name,
                'Avg_Volatility': returns.std() * 100 * np.sqrt(252),  # annualized
                'Max_Volatility': df['Rolling_Vol_20'].max() * 100 * np.sqrt(252),
                'Min_Volatility': df['Rolling_Vol_20'].min() * 100 * np.sqrt(252),
                'Vol_of_Vol': df['Rolling_Vol_20'].std() * 100,
            }
            results_list.append(result)

        vol_df = pd.DataFrame(results_list)
        print(vol_df.to_string(index=False))
        print()

        vol_df.to_csv(self.output_dir / 'volatility_analysis.csv', index=False)
        self.analysis_results['volatility'] = vol_df
        return self

    def create_visualizations(self):
        """Create comprehensive visualization plots."""
        print("=" * 80)
        print("CREATING VISUALIZATIONS")
        print("=" * 80)

        # 1. Price evolution for all series
        self._plot_price_evolution()

        # 2. Returns distribution
        self._plot_returns_distribution()

        # 3. Correlation matrix
        self._plot_correlation_matrix()

        # 4. Hurst exponent comparison
        self._plot_hurst_comparison()

        print("✓ All visualizations saved to output/analysis/\n")
        return self

    def generate_summary_report(self):
        """Generate summary recommendations for strategy selection."""
        print("=" * 80)
        print("STRATEGY RECOMMENDATIONS")
        print("=" * 80)

        mr_df = self.analysis_results.get('mean_reversion')
        trend_df = self.analysis_results.get('trend_following')
        vol_df = self.analysis_results.get('volatility')

        # Mean-reversion candidates
        mr_candidates = mr_df[mr_df['Hurst_Exponent'] < 0.5].sort_values('Hurst_Exponent')
        print("\n1. MEAN-REVERSION STRATEGY CANDIDATES:")
        print(f"   Best series: {mr_candidates['Series'].head(3).tolist()}")
        print(f"   (Lowest Hurst exponents: mean-reverting behavior)")

        # Trend-following candidates
        trend_candidates = trend_df[trend_df['ACF_Lag1'] > 0].sort_values('ACF_Lag1', ascending=False)
        print("\n2. TREND-FOLLOWING STRATEGY CANDIDATES:")
        print(f"   Best series: {trend_candidates['Series'].head(3).tolist()}")
        print(f"   (Positive autocorrelation: momentum/trend persistence)")

        # High volatility for volatility-based strategies
        vol_candidates = vol_df.sort_values('Avg_Volatility', ascending=False)
        print("\n3. VOLATILITY-BASED STRATEGY CANDIDATES:")
        print(f"   High volatility series: {vol_candidates['Series'].head(3).tolist()}")
        print(f"   (Higher volatility: more opportunities for breakout/range strategies)")

        print("\n" + "=" * 80)
        print("ANALYSIS COMPLETE")
        print("=" * 80)
        print(f"Results saved to: {self.output_dir.absolute()}\n")

        return self

    # Helper methods
    def _calculate_hurst(self, prices):
        """Calculate Hurst exponent using R/S analysis."""
        if len(prices) < 100:
            return np.nan

        lags = range(2, min(100, len(prices) // 2))
        tau = []
        for lag in lags:
            std = np.std(prices[:lag])
            if std == 0:
                continue
            rs = (np.max(prices[:lag]) - np.min(prices[:lag])) / std
            tau.append(rs)

        if len(tau) < 2:
            return np.nan

        # Linear regression on log-log plot
        lags_used = lags[:len(tau)]
        poly = np.polyfit(np.log(lags_used), np.log(tau), 1)
        return poly[0]

    def _calculate_half_life(self, prices):
        """Calculate half-life of mean reversion."""
        if len(prices) < 2:
            return np.nan

        lag_prices = np.roll(prices, 1)
        lag_prices[0] = 0
        ret = prices - lag_prices
        ret[0] = 0

        lag_prices_no_zero = lag_prices[1:]
        ret_no_zero = ret[1:]

        if len(lag_prices_no_zero) == 0:
            return np.nan

        # OLS regression: ret = lambda * lag_prices + intercept
        slope, intercept = np.polyfit(lag_prices_no_zero, ret_no_zero, 1)

        if slope >= 0:
            return np.nan

        half_life = -np.log(2) / slope
        return half_life if half_life > 0 else np.nan

    def _calculate_momentum(self, returns):
        """Calculate momentum score."""
        returns_arr = returns.values
        positive_following = returns_arr[1:][(returns_arr[:-1] > 0)]
        negative_following = returns_arr[1:][(returns_arr[:-1] < 0)]

        pos_mean = positive_following.mean() if len(positive_following) > 0 else 0
        neg_mean = negative_following.mean() if len(negative_following) > 0 else 0

        return pos_mean - neg_mean

    def _plot_price_evolution(self):
        """Plot price evolution for all series."""
        fig, axes = plt.subplots(5, 2, figsize=(15, 12))
        axes = axes.flatten()

        for idx, (name, df) in enumerate(self.data_dict.items()):
            axes[idx].plot(df.index, df['Close'], linewidth=1)
            axes[idx].set_title(name, fontsize=10)
            axes[idx].set_xlabel('Date', fontsize=8)
            axes[idx].set_ylabel('Price', fontsize=8)
            axes[idx].tick_params(labelsize=7)
            axes[idx].grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(self.output_dir / 'price_evolution.png', dpi=150)
        plt.close()
        print("✓ Price evolution plot saved")

    def _plot_returns_distribution(self):
        """Plot returns distribution for all series."""
        fig, axes = plt.subplots(5, 2, figsize=(15, 12))
        axes = axes.flatten()

        for idx, (name, df) in enumerate(self.data_dict.items()):
            returns = df['Returns'].dropna() * 100
            axes[idx].hist(returns, bins=50, alpha=0.7, edgecolor='black')
            axes[idx].axvline(returns.mean(), color='red', linestyle='--',
                             label=f'Mean: {returns.mean():.3f}%')
            axes[idx].set_title(f'{name} Returns Distribution', fontsize=10)
            axes[idx].set_xlabel('Daily Return (%)', fontsize=8)
            axes[idx].set_ylabel('Frequency', fontsize=8)
            axes[idx].legend(fontsize=7)
            axes[idx].tick_params(labelsize=7)
            axes[idx].grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(self.output_dir / 'returns_distribution.png', dpi=150)
        plt.close()
        print("✓ Returns distribution plot saved")

    def _plot_correlation_matrix(self):
        """Plot correlation matrix of returns."""
        # Create returns matrix
        returns_dict = {}
        for name, df in self.data_dict.items():
            returns_dict[name] = df['Returns']

        returns_df = pd.DataFrame(returns_dict)
        corr_matrix = returns_df.corr()

        plt.figure(figsize=(12, 10))
        sns.heatmap(corr_matrix, annot=True, fmt='.2f', cmap='coolwarm',
                    center=0, square=True, linewidths=1)
        plt.title('Correlation Matrix of Daily Returns', fontsize=14, fontweight='bold')
        plt.tight_layout()
        plt.savefig(self.output_dir / 'correlation_matrix.png', dpi=150)
        plt.close()
        print("✓ Correlation matrix plot saved")

    def _plot_hurst_comparison(self):
        """Plot Hurst exponent comparison."""
        mr_df = self.analysis_results.get('mean_reversion')
        if mr_df is None:
            return

        plt.figure(figsize=(12, 6))

        # Sort by Hurst exponent
        mr_sorted = mr_df.sort_values('Hurst_Exponent')

        colors = ['green' if h < 0.5 else 'red' for h in mr_sorted['Hurst_Exponent']]

        plt.barh(mr_sorted['Series'], mr_sorted['Hurst_Exponent'], color=colors, alpha=0.7)
        plt.axvline(0.5, color='black', linestyle='--', linewidth=2,
                    label='H=0.5 (Random Walk)')
        plt.xlabel('Hurst Exponent', fontsize=12)
        plt.ylabel('Series', fontsize=12)
        plt.title('Hurst Exponent by Series\n(H < 0.5: Mean-Reverting, H > 0.5: Trending)',
                  fontsize=14, fontweight='bold')
        plt.legend()
        plt.grid(True, alpha=0.3, axis='x')
        plt.tight_layout()
        plt.savefig(self.output_dir / 'hurst_comparison.png', dpi=150)
        plt.close()
        print("✓ Hurst comparison plot saved")


def main():
    """Run complete data exploration analysis."""
    explorer = DataExplorer()

    (explorer
     .load_data()
     .calculate_returns()
     .basic_statistics()
     .test_mean_reversion()
     .test_trend_following()
     .analyze_volatility()
     .create_visualizations()
     .generate_summary_report())


if __name__ == '__main__':
    main()
