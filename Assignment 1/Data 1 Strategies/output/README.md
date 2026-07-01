# Output Directory Structure

This directory contains all backtesting results organized by strategy type to prevent result overwrites and maintain clear separation.

## Directory Structure

```
output/
├── individual_strategies/           # Individual strategy results (Part 1)
│   ├── s1_dual_ma/                 # Strategy 1: Dual MA Crossover (Series 04)
│   ├── s2_buy_hold/                # Strategy 2: Buy and Hold (Series 05)
│   └── s3_mean_reversion/          # Strategy 3: Mean Reversion (Series 09)
├── combined_strategy/              # CVaR Combined Strategy results (Part 2)
├── comparison/                     # Strategy comparison analyses
├── analysis/                       # Data analysis and market condition studies
├── optimization/                   # Parameter optimization results
└── validation/                     # Strategy validation and testing reports
```

## Individual Strategy Results

### Strategy 1: Dual MA Crossover (Series 04)
- **Location**: `individual_strategies/s1_dual_ma/`
- **Performance**: +0.67% return, PD ratio: 0.44
- **Activity**: 9.4% (moderate trading frequency)
- **Key Files**: 
  - `run_summary.json`: Performance summary
  - `series_4_cumPnL.png`: Series 04 performance chart
  - `equity_dashboard.png`: Complete performance dashboard

### Strategy 2: Buy and Hold (Series 05)
- **Location**: `individual_strategies/s2_buy_hold/`
- **Performance**: +35.59% return, PD ratio: 2.89
- **Activity**: 99.6% (fully invested)
- **Key Files**:
  - `run_summary.json`: Performance summary
  - `series_5_cumPnL.png`: Series 05 performance chart
  - `equity_dashboard.png`: Complete performance dashboard

### Strategy 3: Mean Reversion (Series 09)
- **Location**: `individual_strategies/s3_mean_reversion/`
- **Performance**: -1.13% return, PD ratio: -0.74
- **Activity**: 6.6% (low trading frequency)
- **Key Files**:
  - `run_summary.json`: Performance summary
  - `series_9_cumPnL.png`: Series 09 performance chart
  - `equity_dashboard.png`: Complete performance dashboard

## Combined Strategy Results

### CVaR Portfolio Optimization (Part 2)
- **Location**: `combined_strategy/`
- **Performance**: +12.93% return, PD ratio: 3.35
- **Activity**: 93.9% (highly active portfolio)
- **Strategy**: Dynamic CVaR-based allocation across three strategies
- **Key Files**:
  - `run_summary.json`: Portfolio performance summary
  - `equity_dashboard.png`: Combined portfolio dashboard
  - `portfolio_underwater.png`: Drawdown analysis
  - Individual series performance charts

## File Types Explanation

### Core Result Files
- **`run_summary.json`**: Key performance metrics (return, PD ratio, activity, bankruptcy status)
- **`per_series_pd.json`**: Detailed per-series profit/drawdown ratios
- **`equity_curve.png`**: Portfolio equity evolution over time
- **`equity_dashboard.png`**: Multi-panel performance dashboard
- **`portfolio_underwater.png`**: Drawdown visualization
- **`realized_equity_curve.png`**: Realized P&L tracking

### Series-Specific Charts
- **`series_X_cumPnL.png`**: Cumulative P&L for individual series
- Shows trading activity and performance for each data series
- Active series show actual trading patterns
- Inactive series show flat lines (no trading)

## Performance Summary

| Strategy | Location | Return | PD Ratio | Activity | Status |
|----------|----------|--------|----------|----------|---------|
| S1: Dual MA | `s1_dual_ma/` | +0.67% | 0.44 | 9.4% | ✅ Positive |
| S2: Buy & Hold | `s2_buy_hold/` | +35.59% | 2.89 | 99.6% | ✅ Excellent |
| S3: Mean Reversion | `s3_mean_reversion/` | -1.13% | -0.74 | 6.6% | ❌ Negative |
| **Combined CVaR** | `combined_strategy/` | **+12.93%** | **3.35** | **93.9%** | ✅ **Superior** |

## Usage Notes

1. **Individual Strategy Analysis**: Use files in `individual_strategies/` for Part 1 report analysis
2. **Combined Strategy Analysis**: Use files in `combined_strategy/` for Part 2 report analysis
3. **Comparison Studies**: Files in `comparison/` for strategy performance comparisons
4. **Historical Data**: `optimization/` and `validation/` contain historical analysis and optimization results

## Data Integrity

- All results generated with identical framework settings (s_mult=2.0, liquidation policy)
- Individual strategies run independently to avoid cross-contamination
- CVaR combined strategy preserves excellent +12.93% performance
- Original data analysis preserved in `analysis/` directory
- Parameter optimization history maintained in `optimization/` directory

**Last Updated**: October 23, 2025
**Framework**: BT396 Backtrader-based backtesting system