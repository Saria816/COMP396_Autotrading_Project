================================================================================
COMP396 TEAM02 README
================================================================================

*All command-line instructions in this guide are written for Visual Studio Code with its integrated terminal. 
Two points should be noted regarding cross-platform compatibility. 
First, multi-line commands using the backslash (\) as a line-continuation character work in macOS and Linux terminals,
as well as in Git Bash on Windows. If the integrated terminal is running PowerShell or the Windows Command Prompt, 
the backslash should be removed and the command entered as a single line. 
Second, all commands can be executed in any standard terminal environment outside VS Code, including the system terminal, 
PyCharm's terminal, or a standalone PowerShell window. The choice of editor does not affect the execution of any script in this project, 
provided that Python and the listed dependencies are correctly installed.

================================================================================
1. Project Overview
================================================================================

This project develops a combined trading strategy based on the BT396 backtesting 
framework, integrating three sub-strategy types across 10 assets:

- Trend/Momentum  - series_1, 3, 4, 6, 9   (5 assets, 70% allocation)
- Mean Reversion  - series_2, 7, 8, 10         (4 assets, 24% allocation)
- Short/Defensive - series_5                        (1 asset,   6% allocation)

Capital allocation: Trend assets 70% + Other assets 30% (equal-weight within each group).

Key results on Part 2 data:  Total Return:      19.55%
                             True PD Ratio:     2.44
                             Activity:          96.90%
                             Final Value:       1,195,452.14 GBP

================================================================================
2. Files Included
================================================================================

team2/                                    Note：
|
|-- README.txt                            # This file
|
|-- BT396_Version_0.1.3/                  # Backtesting framework
|   |-- main.py                           
|   |-- config.yaml                       
|   |-- requirements.txt                  
|   |-- framework/                        
|   |   |-- strategy_base.py              
|   |   |-- strategies_loader.py          
|   |   |-- data_loader.py                
|   |   |-- analyzers.py                  
|   |   +-- plotting.py                   
|   |-- strategies/
|   |   +-- Team2.py                      # * Main strategy file (TeamStrategy)
|   |-- DATA/
|       |-- PART2/ 
|       |-- PART3/                      
|   +-- output/                           # Backtest output (charts + JSON)
|   +-- output_part3/
|
+-- Strategy_Research_and_Development/    # Research & analysis code
    |-- DATA/
    |-- data_analysis.ipynb               # Data exploration & asset classification
    |-- parameter_optimization.ipynb      # Parameter optimization (interactive)
    |-- optimize_trend_individual.py      # Trend strategy parameter search
    |-- optimize_mr_individual.py         # Mean reversion parameter search
    |-- optimize_short_individual.py      # Short strategy parameter search
    |-- robustness_test.py                # Robustness tests (4 types)
    |-- test_atr_stoploss.py              # ATR stop-loss comparison test
    |-- generate_report_figures.py        # Report figure generation (5 charts)
    |-- generate_part3_figures.py         # Report figure generation on part 3 data
    |-- figures/                          # Analysis charts & data (CSV + PNG)
    |-- figures_part3/                    # Analysis charts & data on part 3 data (CSV + PNG)
    |-- optimization_results/             # Optimization results (CSV + JSON)
    +-- robustness_results/               # Robustness test results (CSV + MD)

================================================================================
3. Environment and Dependencies
================================================================================

Python version: Python 3.8+

Backtest framework (BT396_Version_0.1.3):
  - backtrader
  - pandas
  - numpy
  - matplotlib
  - mplfinance
  - pyyaml              (for loading config.yaml)

Research notebooks (Strategy_Research_and_Development/):
  - seaborn              (data_analysis.ipynb)
  - scipy                (data_analysis.ipynb)
  - statsmodels          (data_analysis.ipynb)

Install framework dependencies:

  pip install -r BT396_Version_0.1.3/requirements.txt

Install all dependencies (framework + research):

  pip install -r BT396_Version_0.1.3/requirements.txt \
              seaborn scipy statsmodels pyyaml

================================================================================
4. How to Run the Final Strategy
================================================================================

4.1  Basic run (with chart output)
----------------------------------

  cd BT396_Version_0.1.3
  python main.py --strategy Team2 --data-dir ./DATA/PART2

4.2  Fast run (no charts)
-------------------------

  cd BT396_Version_0.1.3
  python main.py --strategy Team2 --data-dir ./DATA/PART2 --no-plot

4.3  Run with date range
-------------------------

  cd BT396_Version_0.1.3
  python main.py --strategy Team2 --data-dir ./DATA/PART2 \
                 --fromdate 2073-01-01 --todate 2074-12-31

4.4  Debug mode (verbose logging)
----------------------------------

  cd BT396_Version_0.1.3
  python main.py --strategy Team2 --data-dir ./DATA/PART2 --debug

4.5  Run on a different dataset (e.g., Part 3)
-----------------------------------------------

  cd BT396_Version_0.1.3
  python main.py --strategy Team2 --data-dir ./DATA/PART3 --no-plot

  Data format requirements:
    - Directory must contain 10 CSV files: 01.csv, 02.csv, ..., 10.csv
    - Each CSV: Index (date), Open, High, Low, Close, Volume
    - All files should share the same date range

  Note: No code changes are needed; the framework automatically loads data from the specified directory.

4.6  Configuration (config.yaml)
---------------------------------

  Key settings in BT396_Version_0.1.3/config.yaml:

    starting_cash: 1000000         # Starting capital (1,000,000 GBP)
    commission: 0.0                # Commission rate (0%)
    s_mult: 2.0                    # Slippage multiplier
    plot: true                     # Generate charts
    data_dir: "./DATA/PART2"       # Data directory
    output_dir: "./output"         # Output directory
    end_policy: "liquidate"        # Liquidate all positions at end

  Note: s_mult and end_policy should remain at default values as required by the project grading criteria.

================================================================================
5. How to Reproduce the Research Process
================================================================================

The Strategy_Research_and_Development pipeline has 6 steps. Steps 1-4 are independent and can run in parallel; 
step 5 depends on steps 1 and 3; step 6 can run independently.

  Step 1 --+--> Step 5
  Step 2   |
  Step 3 --+
  Step 4
  Step 6  (independent, can run anytime)

Note: pip install jupyter nbconvert ipykernel (if environment do not have jupter)
      If the `jupyter` command is not recognised due to local PATH configuration, 
      please use `python -m pip install jupyter nbconvert ipykernel` instead.

Step 1: Data Analysis & Asset Classification 
Note: To access to the required environment, you can creat a cell at the top of the data_analysis.ipynb file and run: 
      %pip install pandas numpy matplotlib seaborn scipy statsmodels
---------------------------------------------
  cd Strategy_Research_and_Development
  jupyter nbconvert --to notebook --execute --inplace \ --ExecutePreprocessor.timeout=600 data_analysis.ipynb
  (or python -m jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=600 data_analysis.ipynb)

  What it does:
    - Computes basic statistics (mean, std, skewness, kurtosis) for all 10 assets
    - Classifies assets into Trend/Momentum, Mean Reversion, or Short/Defensive based on Return/MaxDD ratio (threshold = 1.1)
    - Generates price charts, return distributions, and correlation matrix

  Output -> figures/:
    - basic_statistics.csv          # Basic stats for all 10 assets
    - correlation_matrix.csv        # 10x10 asset correlation matrix
    - asset_classification.csv      # Asset classification results
    - all_series_prices.png         # Price time series (10 assets)
    - normalized_prices.png         # Normalized price comparison
    - returns_distribution.png      # Daily return histograms
    - correlation_matrix.png        # Correlation heatmap
    - rolling_volatility.png        # Rolling 20-day volatility

Step 2: Parameter Optimization (3 scripts, can run in parallel)
----------------------------------------------------------------
  cd Strategy_Research_and_Development
  python optimize_trend_individual.py
  python optimize_mr_individual.py
  python optimize_short_individual.py

  What it does:
    - Grid search over full parameter space for each asset
    - Tests 4 strategy variants per category: 
            Trend:  ma_crossover, breakout, macd, above_ma
            MR:     zscore, rsi, bollinger, ma_deviation
            Short:  trend_short, ma_cross_short, rsi_short, bollinger_short
    - Train/test split: first 700 days (70%) / last 300 days (30%)
    - Scoring: 0.3*train_sharpe + 0.3*test_sharpe + 0.2*test_return + 0.2*(1-|drawdown|)

  Output -> optimization_results/:
    From optimize_trend_individual.py:
      - trend_individual_summary.csv        # Best strategy per trend asset (5 rows)
      - trend_variant_summary.csv           # Best of each variant (5x4 = 20 rows)
      - trend_series_*_optimization.csv     # Full grid results per asset (5 files)
      - optimal_trend_params.json           # Optimal trend parameters

    From optimize_mr_individual.py:
      - mr_individual_summary.csv           # Best strategy per MR asset (4 rows)
      - mr_variant_summary.csv              # Best of each variant (4x4 = 16 rows)
      - mr_series_*_all_params.csv          # Full grid results per asset (4 files)
      - optimal_mr_individual_params.json   # Optimal MR parameters

    From optimize_short_individual.py:
      - short_variant_summary.csv           # Best of each variant (1x4 = 4 rows)
      - short_series_5_all_params.csv       # Full grid results for series_5
      - optimal_short_params.json           # Optimal short parameters

  Note: parameter_optimization.ipynb provides an interactive version of the same optimization logic and additionally produces
  trend_series_*_all_params.csv, short_all_params.csv, and all_optimal_params.json. Running the three .py scripts is sufficient
  for reproducing all key results.

Step 3: Robustness Testing
---------------------------
  cd Strategy_Research_and_Development
  python robustness_test.py

  What it does:
    - Time period test: splits data into two halves, runs backtest on each
    - Allocation sensitivity: tests 50/50, 60/40, 70/30, 80/20, 90/10
    - Rolling window test: 10 overlapping 6-month windows
    - Component test: runs trend-only, other-only, and combined strategies

  Output -> robustness_results/:
    - time_period_test.csv                # Time period split results
    - allocation_sensitivity.csv          # Allocation ratio sensitivity
    - rolling_window_test.csv             # Rolling window results (10 windows)
    - component_test.csv                  # Strategy component comparison
    - robustness_report.md                # Summary report (auto-generated)

Step 4: ATR Stop-Loss Comparison
---------------------------------
  cd Strategy_Research_and_Development
  python test_atr_stoploss.py

  What it does:
    - Compares signal-driven exits vs ATR fixed stop-loss (x2.0 and x3.5)
    - Uses simplified backtest methodology (no slippage) across all 10 assets

  Output -> robustness_results/:
    - atr_stop_loss_test.csv              # Exit method comparison (3 scenarios)

Step 5: Generate Report Figures (depends on steps 1 and 3)
-----------------------------------------------------------
  cd Strategy_Research_and_Development
  python generate_report_figures.py

  What it does:
    - Reads asset_classification.csv (from step 1) and robustness test CSVs (from step 3) to produce 5 report-ready figures

  Output -> figures/:
    - asset_classification_scatter.png    # Asset classification scatter plot
    - strategy_signals_example.png        # Trading signal examples (3 types)
    - rolling_window_returns.png          # Rolling window return bar chart
    - allocation_sensitivity.png          # Allocation sensitivity dual-axis
    - component_test_comparison.png       # Strategy component comparison

Step 6: Run Final Backtest
---------------------------
  cd BT396_Version_0.1.3
  python main.py --strategy Team2 --data-dir ./DATA/PART2

  Output -> output/:
    - run_summary.json                    # Key performance metrics
    - per_series_pd.json                  # Per-asset PD ratios
    - true_equity_curve.png               # True equity curve (with costs)
    - portfolio_underwater.png            # Drawdown underwater chart
    - equity_dashboard.png                # Performance dashboard
    - series_*_cumPnL.png                 # Per-asset cumulative PnL (10 files)
    - (and additional charts, 19 PNG files total)

  Output -> output_part3/:
    - run_summary.json                    # Key performance metrics
    - per_series_pd.json                  # Per-asset PD ratios
    - true_equity_curve.png               # True equity curve (with costs)
    - portfolio_underwater.png            # Drawdown underwater chart
    - equity_dashboard.png                # Performance dashboard
    - series_*_cumPnL.png                 # Per-asset cumulative PnL (10 files)
    - (and additional charts, 17 PNG files total)

Quick-start: run all research in one go
-----------------------------------------
  # From the project root directory:

  cd Strategy_Research_and_Development

  # Steps 1-4 in parallel (takes a few minutes)
  jupyter nbconvert --to notebook --execute --inplace \
      --ExecutePreprocessor.timeout=600 data_analysis.ipynb &
  python optimize_trend_individual.py &
  python optimize_mr_individual.py &
  python optimize_short_individual.py &
  python robustness_test.py &
  python test_atr_stoploss.py &
  wait

  # Step 5 (depends on steps 1 and 3)
  python generate_report_figures.py

  # Step 6: final backtest
  cd ../BT396_Version_0.1.3
  python main.py --strategy Team2 --data-dir ./DATA/PART2

================================================================================
6. Output Files
================================================================================

6.1  Backtest output: BT396_Version_0.1.3/output/
---------------------------------------------------

  JSON:
    run_summary.json                  # Final metrics (value, PD ratio, activity)
    per_series_pd.json                # Per-asset PD ratios

  Charts (PNG):
    true_equity_curve.png             # True equity curve (includes slippage)
    equity_curve.png                  # Equity curve (open PnL)
    portfolio_underwater.png          # Drawdown underwater chart
    equity_dashboard.png              # Performance dashboard
    equity_dashboard_combined.png     # Combined dashboard view
    realized_equity_curve.png         # Realized PnL curve
    all_equity_curves.png             # All 10 series equity curves
    series_1_cumPnL.png               # Per-asset cumulative PnL
      ...                             (10 files: series_1 through series_10)
    series_10_cumPnL.png
    input_data_plot.png               # Raw input price data
    input_data_plot_normalised.png    # Normalized input data

6.2  Research figures: Strategy_Research_and_Development/figures/
----------------------------------------

  CSV (from data_analysis.ipynb):
    basic_statistics.csv              # Descriptive stats for 10 assets
    correlation_matrix.csv            # 10x10 correlation matrix
    asset_classification.csv          # Classification: strategy type & rationale

  Charts from data_analysis.ipynb:
    all_series_prices.png             # Price time series for all 10 assets
    normalized_prices.png             # Normalized price comparison
    returns_distribution.png          # Daily return histograms
    correlation_matrix.png            # Correlation heatmap
    rolling_volatility.png            # Rolling 20-day volatility

  Charts from generate_report_figures.py:
    asset_classification_scatter.png      # Return vs drawdown scatter by type
    strategy_signals_example.png          # Signal examples for 3 strategy types
    rolling_window_returns.png            # Rolling window return bar chart
    allocation_sensitivity.png            # Allocation sensitivity dual-axis
    component_test_comparison.png         # Strategy component comparison

6.3  Optimization results: Strategy_Research_and_Development/optimization_results/
----------------------------------------------------------

  Summary files (from .py scripts):
    trend_individual_summary.csv         # Global best per trend asset (5 rows)
    mr_individual_summary.csv            # Global best per MR asset (4 rows)
    trend_variant_summary.csv            # Best per variant per asset (20 rows)
    mr_variant_summary.csv               # Best per variant per asset (16 rows)
    short_variant_summary.csv            # Best per variant (4 rows)

  Parameter JSON (from .py scripts):
    optimal_trend_params.json            # Best trend parameters
    optimal_mr_individual_params.json    # Best MR parameters
    optimal_short_params.json            # Best short parameters

  Detailed grid search results (from .py scripts):
    trend_series_*_optimization.csv      # Full grid results per trend asset (5 files)
    mr_series_*_all_params.csv           # Full grid results per MR asset (4 files)
    short_series_5_all_params.csv        # Full grid results for series_5

  Additional files (from parameter_optimization.ipynb):
    trend_series_*_all_params.csv        # Trend grid results (5 files)
    short_all_params.csv                 # Short grid results
    all_optimal_params.json              # Combined optimal parameters

6.4  Robustness results: Strategy_Research_and_Development/robustness_results/
------------------------------------------------------

    time_period_test.csv            # Train/validation period comparison
    allocation_sensitivity.csv      # Allocation ratio sweep (5 configs)
    rolling_window_test.csv         # Rolling 6-month windows (10 windows)
    component_test.csv              # Strategy component isolation test
    atr_stop_loss_test.csv          # ATR stop-loss vs signal-driven exits
    robustness_report.md            # Auto-generated summary report

================================================================================
7. Strategy Parameters
================================================================================

Trend assets (14% each, 70% total):
  series_1:  breakout            # lookback=25
  series_3:  above_ma            # ma_period=20, confirm_days=3
  series_4:  ma_crossover        # fast=10, slow=30
  series_6:  above_ma            # ma_period=15, confirm_days=2
  series_9:  above_ma            # ma_period=15, confirm_days=2

Mean reversion assets (6% each, 24% total):
  series_2:  zscore              # lookback=20, entry_z=2.0, exit_z=0.0
  series_7:  bollinger           # lookback=15, std_mult=2.0
  series_8:  rsi                 # rsi_period=14, oversold=30
  series_10: zscore              # lookback=25, entry_z=2.5, exit_z=0.0

Short asset (6% total):
  series_5:  rsi_short      # rsi_period=7, overbought=75, oversold=40

================================================================================
End of Document
================================================================================
