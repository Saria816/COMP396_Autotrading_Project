"""
Mean reversion strategy parameter optimization script - individual asset optimization
Applicable assets: series_2, series_7, series_8, series_10 (Return/MaxDD Ratio < 1.1)
Train:Test = 7:3
"""

import pandas as pd
import numpy as np
from pathlib import Path
from itertools import product
from typing import Dict, List
import warnings
import json
warnings.filterwarnings('ignore')

# Path settings
DATA_PATH = Path('../BT396_Version_0.1.3/DATA/PART2')
RESULTS_PATH = Path('./optimization_results')
RESULTS_PATH.mkdir(exist_ok=True)

# Mean reversion strategy assets
MR_SERIES = ['series_2', 'series_7', 'series_8', 'series_10']


def load_data() -> Dict[str, pd.DataFrame]:
    """Load all 10 series data"""
    data = {}
    for i in range(1, 11):
        filename = f'{i:02d}.csv'
        filepath = DATA_PATH / filename
        df = pd.read_csv(filepath)

        date_col = 'Index' if 'Index' in df.columns else 'Date'
        df[date_col] = pd.to_datetime(df[date_col])
        df.set_index(date_col, inplace=True)
        df.sort_index(inplace=True)

        data[f'series_{i}'] = df

    return data


class SimpleBacktest:
    """Simplified backtesting engine"""

    def __init__(self, df: pd.DataFrame, initial_cash: float = 100000):
        self.df = df.copy()
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.position = 0
        self.equity_curve = []
        self.trades = []

    def run(self, signals: pd.Series) -> Dict:
        """Run backtest"""
        self.cash = self.initial_cash
        self.position = 0
        self.equity_curve = []
        self.trades = []

        close = self.df['Close'].values

        for i in range(len(self.df)):
            price = close[i]
            signal = signals.iloc[i] if i < len(signals) else 0

            if signal == 1 and self.position <= 0:
                if self.position < 0:
                    self.cash += self.position * price
                shares = int(self.cash * 0.95 / price)
                if shares > 0:
                    self.position = shares
                    self.cash -= shares * price
                    self.trades.append({'type': 'buy', 'price': price, 'day': i})

            elif signal == -1 and self.position > 0:
                self.cash += self.position * price
                self.trades.append({'type': 'sell', 'price': price, 'day': i})
                self.position = 0

            equity = self.cash + self.position * price
            self.equity_curve.append(equity)

        # Final liquidation
        final_price = close[-1]
        if self.position != 0:
            self.cash += self.position * final_price
            self.position = 0

        return self._calculate_metrics()

    def _calculate_metrics(self) -> Dict:
        """Calculate backtest metrics"""
        equity = np.array(self.equity_curve)
        returns = np.diff(equity) / equity[:-1]

        total_return = (equity[-1] / self.initial_cash - 1) * 100
        sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0

        cummax = np.maximum.accumulate(equity)
        drawdown = (equity - cummax) / cummax
        max_drawdown = np.min(drawdown) * 100

        n_trades = len([t for t in self.trades if t['type'] == 'buy'])

        return {
            'total_return': total_return,
            'sharpe': sharpe,
            'max_drawdown': max_drawdown,
            'n_trades': n_trades,
            'final_equity': equity[-1]
        }


# ============================================================
# Strategy 1: Z-score Mean Reversion
# ============================================================
def generate_mr_signals_zscore(df: pd.DataFrame, lookback: int,
                                entry_zscore: float, exit_zscore: float) -> pd.Series:
    """Z-score mean reversion: buy on oversold, close on reversion"""
    close = df['Close']

    ma = close.rolling(lookback).mean()
    std = close.rolling(lookback).std()
    zscore = (close - ma) / std

    signals = pd.Series(0, index=df.index)
    position = 0

    for i in range(lookback, len(df)):
        z = zscore.iloc[i]

        if position == 0:
            if z < -entry_zscore:
                signals.iloc[i] = 1
                position = 1
        elif position == 1:
            if z > exit_zscore or z > entry_zscore:
                signals.iloc[i] = -1
                position = 0

    return signals


# ============================================================
# Strategy 2: RSI Mean Reversion
# ============================================================
def generate_mr_signals_rsi(df: pd.DataFrame, rsi_period: int,
                            oversold: float, overbought: float) -> pd.Series:
    """RSI mean reversion: buy on oversold, close when RSI reverts to 50 or overbought"""
    close = df['Close']

    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(rsi_period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(rsi_period).mean()
    rs = gain / (loss + 1e-10)
    rsi = 100 - (100 / (1 + rs))

    signals = pd.Series(0, index=df.index)
    position = 0

    for i in range(rsi_period + 1, len(df)):
        r = rsi.iloc[i]

        if position == 0:
            if r < oversold:
                signals.iloc[i] = 1
                position = 1
        elif position == 1:
            if r > 50 or r > overbought:
                signals.iloc[i] = -1
                position = 0

    return signals


# ============================================================
# Strategy 3: Bollinger Band Mean Reversion
# ============================================================
def generate_mr_signals_bollinger(df: pd.DataFrame, lookback: int,
                                   std_mult: float, exit_mult: float) -> pd.Series:
    """Bollinger band mean reversion: buy below lower band, close at middle band"""
    close = df['Close']

    ma = close.rolling(lookback).mean()
    std = close.rolling(lookback).std()
    lower = ma - std_mult * std

    signals = pd.Series(0, index=df.index)
    position = 0

    for i in range(lookback, len(df)):
        price = close.iloc[i]
        mid = ma.iloc[i]

        if position == 0:
            if price < lower.iloc[i]:
                signals.iloc[i] = 1
                position = 1
        elif position == 1:
            if price > mid:
                signals.iloc[i] = -1
                position = 0

    return signals


# ============================================================
# Strategy 4: Dual MA Deviation Mean Reversion
# ============================================================
def generate_mr_signals_ma_deviation(df: pd.DataFrame, fast_period: int,
                                      slow_period: int, threshold: float) -> pd.Series:
    """Dual MA deviation: reverse trade when fast MA deviates excessively from slow MA"""
    close = df['Close']

    fast_ma = close.rolling(fast_period).mean()
    slow_ma = close.rolling(slow_period).mean()
    deviation = (fast_ma - slow_ma) / slow_ma * 100

    signals = pd.Series(0, index=df.index)
    position = 0

    for i in range(slow_period, len(df)):
        dev = deviation.iloc[i]

        if position == 0:
            if dev < -threshold:
                signals.iloc[i] = 1
                position = 1
        elif position == 1:
            if dev > 0:
                signals.iloc[i] = -1
                position = 0

    return signals


# ============================================================
# Single asset optimization function
# ============================================================
def optimize_mr_single_asset(df: pd.DataFrame, series_name: str, train_end: int) -> pd.DataFrame:
    """Iterate all MR strategy types and parameter combinations for a single asset"""
    results = []

    # ============================================================
    # Strategy 1: Z-score
    # ============================================================
    ZSCORE_PARAM_GRID = {
        'lookback': [5, 10, 15, 20, 25, 30, 40, 50],
        'entry_zscore': [1.0, 1.5, 2.0, 2.5, 3.0],
        'exit_zscore': [-0.5, -0.25, 0.0, 0.25, 0.5]
    }

    for lookback, entry_z, exit_z in product(
        ZSCORE_PARAM_GRID['lookback'],
        ZSCORE_PARAM_GRID['entry_zscore'],
        ZSCORE_PARAM_GRID['exit_zscore']
    ):
        try:
            signals = generate_mr_signals_zscore(df, lookback, entry_z, exit_z)

            bt_train = SimpleBacktest(df.iloc[:train_end])
            train_result = bt_train.run(signals.iloc[:train_end])

            bt_valid = SimpleBacktest(df.iloc[train_end:])
            valid_result = bt_valid.run(signals.iloc[train_end:])

            score = (
                0.3 * np.clip(train_result['sharpe'], -2, 2) / 2 +
                0.3 * np.clip(valid_result['sharpe'], -2, 2) / 2 +
                0.2 * np.clip(valid_result['total_return'], -50, 100) / 100 +
                0.2 * (1 - abs(np.clip(valid_result['max_drawdown'], -50, 0)) / 50)
            )

            results.append({
                'strategy': 'zscore',
                'params': f'lookback={lookback},entry_z={entry_z},exit_z={exit_z}',
                'train_return': train_result['total_return'],
                'train_sharpe': train_result['sharpe'],
                'valid_return': valid_result['total_return'],
                'valid_sharpe': valid_result['sharpe'],
                'valid_maxdd': valid_result['max_drawdown'],
                'valid_trades': valid_result['n_trades'],
                'score': score
            })
        except:
            continue

    # ============================================================
    # Strategy 2: RSI
    # ============================================================
    RSI_PARAM_GRID = {
        'rsi_period': [7, 10, 14, 20, 25],
        'oversold': [20, 25, 30, 35],
        'overbought': [65, 70, 75, 80]
    }

    for rsi_period, oversold, overbought in product(
        RSI_PARAM_GRID['rsi_period'],
        RSI_PARAM_GRID['oversold'],
        RSI_PARAM_GRID['overbought']
    ):
        try:
            signals = generate_mr_signals_rsi(df, rsi_period, oversold, overbought)

            bt_train = SimpleBacktest(df.iloc[:train_end])
            train_result = bt_train.run(signals.iloc[:train_end])

            bt_valid = SimpleBacktest(df.iloc[train_end:])
            valid_result = bt_valid.run(signals.iloc[train_end:])

            score = (
                0.3 * np.clip(train_result['sharpe'], -2, 2) / 2 +
                0.3 * np.clip(valid_result['sharpe'], -2, 2) / 2 +
                0.2 * np.clip(valid_result['total_return'], -50, 100) / 100 +
                0.2 * (1 - abs(np.clip(valid_result['max_drawdown'], -50, 0)) / 50)
            )

            results.append({
                'strategy': 'rsi',
                'params': f'rsi_period={rsi_period},oversold={oversold},overbought={overbought}',
                'train_return': train_result['total_return'],
                'train_sharpe': train_result['sharpe'],
                'valid_return': valid_result['total_return'],
                'valid_sharpe': valid_result['sharpe'],
                'valid_maxdd': valid_result['max_drawdown'],
                'valid_trades': valid_result['n_trades'],
                'score': score
            })
        except:
            continue

    # ============================================================
    # Strategy 3: Bollinger Band
    # ============================================================
    BOLLINGER_PARAM_GRID = {
        'lookback': [10, 15, 20, 25, 30, 40],
        'std_mult': [1.5, 2.0, 2.5, 3.0],
        'exit_mult': [-0.5, 0.0, 0.5, 1.0]
    }

    for lookback, std_mult, exit_mult in product(
        BOLLINGER_PARAM_GRID['lookback'],
        BOLLINGER_PARAM_GRID['std_mult'],
        BOLLINGER_PARAM_GRID['exit_mult']
    ):
        try:
            signals = generate_mr_signals_bollinger(df, lookback, std_mult, exit_mult)

            bt_train = SimpleBacktest(df.iloc[:train_end])
            train_result = bt_train.run(signals.iloc[:train_end])

            bt_valid = SimpleBacktest(df.iloc[train_end:])
            valid_result = bt_valid.run(signals.iloc[train_end:])

            score = (
                0.3 * np.clip(train_result['sharpe'], -2, 2) / 2 +
                0.3 * np.clip(valid_result['sharpe'], -2, 2) / 2 +
                0.2 * np.clip(valid_result['total_return'], -50, 100) / 100 +
                0.2 * (1 - abs(np.clip(valid_result['max_drawdown'], -50, 0)) / 50)
            )

            results.append({
                'strategy': 'bollinger',
                'params': f'lookback={lookback},std_mult={std_mult},exit_mult={exit_mult}',
                'train_return': train_result['total_return'],
                'train_sharpe': train_result['sharpe'],
                'valid_return': valid_result['total_return'],
                'valid_sharpe': valid_result['sharpe'],
                'valid_maxdd': valid_result['max_drawdown'],
                'valid_trades': valid_result['n_trades'],
                'score': score
            })
        except:
            continue

    # ============================================================
    # Strategy 4: Dual MA Deviation
    # ============================================================
    MA_DEV_PARAM_GRID = {
        'fast_period': [5, 10, 15, 20],
        'slow_period': [20, 30, 40, 50, 60],
        'threshold': [1.0, 2.0, 3.0, 4.0, 5.0]
    }

    for fast_period, slow_period, threshold in product(
        MA_DEV_PARAM_GRID['fast_period'],
        MA_DEV_PARAM_GRID['slow_period'],
        MA_DEV_PARAM_GRID['threshold']
    ):
        if fast_period >= slow_period:
            continue

        try:
            signals = generate_mr_signals_ma_deviation(df, fast_period, slow_period, threshold)

            bt_train = SimpleBacktest(df.iloc[:train_end])
            train_result = bt_train.run(signals.iloc[:train_end])

            bt_valid = SimpleBacktest(df.iloc[train_end:])
            valid_result = bt_valid.run(signals.iloc[train_end:])

            score = (
                0.3 * np.clip(train_result['sharpe'], -2, 2) / 2 +
                0.3 * np.clip(valid_result['sharpe'], -2, 2) / 2 +
                0.2 * np.clip(valid_result['total_return'], -50, 100) / 100 +
                0.2 * (1 - abs(np.clip(valid_result['max_drawdown'], -50, 0)) / 50)
            )

            results.append({
                'strategy': 'ma_deviation',
                'params': f'fast={fast_period},slow={slow_period},threshold={threshold}',
                'train_return': train_result['total_return'],
                'train_sharpe': train_result['sharpe'],
                'valid_return': valid_result['total_return'],
                'valid_sharpe': valid_result['sharpe'],
                'valid_maxdd': valid_result['max_drawdown'],
                'valid_trades': valid_result['n_trades'],
                'score': score
            })
        except:
            continue

    # Sort and return
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('score', ascending=False)

    return results_df


def extract_variant_best(results_df: pd.DataFrame, series_name: str) -> List[Dict]:
    """Extract best parameter combination for each strategy variant from full results"""
    variant_results = []
    for strategy in results_df['strategy'].unique():
        sub = results_df[results_df['strategy'] == strategy]
        best_idx = sub['score'].idxmax()
        best = sub.loc[best_idx]
        variant_results.append({
            'series': series_name,
            'strategy': best['strategy'],
            'params': best['params'],
            'train_return': float(best['train_return']),
            'valid_return': float(best['valid_return']),
            'valid_sharpe': float(best['valid_sharpe']),
            'valid_maxdd': float(best['valid_maxdd']),
            'score': float(best['score'])
        })
    variant_results.sort(key=lambda x: x['score'], reverse=True)
    return variant_results


def main():
    print('='*80)
    print('Mean Reversion Strategy Parameter Optimization - Individual Asset')
    print('='*80)

    # Load data
    data = load_data()
    print(f'Loaded {len(data)} series')

    # 7:3 split
    TOTAL_DAYS = len(data['series_1'])
    TRAIN_END = int(TOTAL_DAYS * 0.7)
    print(f'Train set: {TRAIN_END} days, Test set: {TOTAL_DAYS - TRAIN_END} days')
    print(f'Mean reversion assets: {MR_SERIES}')

    # Store optimal params for each asset
    optimal_params = {}
    summary_results = []
    variant_summary_results = []

    for series_name in MR_SERIES:
        print(f'\n{"="*60}')
        print(f'Optimizing {series_name}...')
        print(f'{"="*60}')

        df = data[series_name]
        results_df = optimize_mr_single_asset(df, series_name, TRAIN_END)

        # Save full results
        results_df.to_csv(RESULTS_PATH / f'mr_{series_name}_all_params.csv', index=False)

        # Get best result
        best = results_df.iloc[0]

        print(f'\nSearched {len(results_df)} parameter combinations')
        print(f'\n{series_name} Best Strategy:')
        print(f'  Strategy type: {best["strategy"]}')
        print(f'  Parameters: {best["params"]}')
        print(f'  Train return: {best["train_return"]:.2f}%')
        print(f'  Valid return: {best["valid_return"]:.2f}%')
        print(f'  Valid Sharpe: {best["valid_sharpe"]:.2f}')
        print(f'  Valid MaxDD: {best["valid_maxdd"]:.2f}%')
        print(f'  Composite score: {best["score"]:.4f}')

        # Show Top 5 strategies
        print(f'\n{series_name} Top 5 Strategies:')
        for idx, row in results_df.head(5).iterrows():
            print(f'  {row["strategy"]}: valid_return={row["valid_return"]:.2f}%, Sharpe={row["valid_sharpe"]:.2f}, Score={row["score"]:.4f}')

        # Extract best result for each variant
        variant_results = extract_variant_best(results_df, series_name)
        variant_summary_results.extend(variant_results)

        print(f'\n{series_name} Best Result per Variant:')
        for vr in variant_results:
            print(f'  {vr["strategy"]:15s} | Score={vr["score"]:.4f} | valid_return={vr["valid_return"]:.2f}% | valid_sharpe={vr["valid_sharpe"]:.2f} | valid_maxdd={vr["valid_maxdd"]:.2f}%')

        # Save optimal params
        optimal_params[series_name] = {
            'strategy': best['strategy'],
            'params': best['params'],
            'train_return': float(best['train_return']),
            'valid_return': float(best['valid_return']),
            'valid_sharpe': float(best['valid_sharpe']),
            'valid_maxdd': float(best['valid_maxdd'])
        }

        summary_results.append({
            'series': series_name,
            'strategy': best['strategy'],
            'params': best['params'],
            'train_return': best['train_return'],
            'valid_return': best['valid_return'],
            'valid_sharpe': best['valid_sharpe'],
            'valid_maxdd': best['valid_maxdd'],
            'score': best['score']
        })

    # ============================================================
    # Summary
    # ============================================================
    print('\n' + '='*80)
    print('All Assets Optimal Parameters Summary')
    print('='*80)

    summary_df = pd.DataFrame(summary_results)
    print('\n')
    print(summary_df.to_string(index=False))

    # Calculate average returns
    avg_train = summary_df['train_return'].mean()
    avg_valid = summary_df['valid_return'].mean()
    print(f'\nAverage train return: {avg_train:.2f}%')
    print(f'Average valid return: {avg_valid:.2f}%')

    # Save results
    summary_df.to_csv(RESULTS_PATH / 'mr_individual_summary.csv', index=False)

    with open(RESULTS_PATH / 'optimal_mr_individual_params.json', 'w') as f:
        json.dump(optimal_params, f, indent=2, default=str)

    # Save best result summary for each variant
    variant_summary_df = pd.DataFrame(variant_summary_results)
    variant_summary_df.to_csv(RESULTS_PATH / 'mr_variant_summary.csv', index=False)

    print('\n' + '='*80)
    print('All Assets All Variants Best Results Summary')
    print('='*80)
    print(variant_summary_df.to_string(index=False))

    print(f'\nResults saved to {RESULTS_PATH}')

    # ============================================================
    # Full data backtest verification
    # ============================================================
    print('\n' + '='*80)
    print('Full Data Backtest Verification (1000 days)')
    print('='*80)

    for series_name in MR_SERIES:
        df = data[series_name]
        best_info = optimal_params[series_name]
        strategy = best_info['strategy']
        params_str = best_info['params']

        # Parse parameters
        params = {}
        for item in params_str.split(','):
            key, val = item.split('=')
            params[key] = float(val) if '.' in val else int(val)

        # Generate signals
        if strategy == 'zscore':
            signals = generate_mr_signals_zscore(df, params['lookback'], params['entry_z'], params['exit_z'])
        elif strategy == 'rsi':
            signals = generate_mr_signals_rsi(df, params['rsi_period'], params['oversold'], params['overbought'])
        elif strategy == 'bollinger':
            signals = generate_mr_signals_bollinger(df, params['lookback'], params['std_mult'], params['exit_mult'])
        elif strategy == 'ma_deviation':
            signals = generate_mr_signals_ma_deviation(df, params['fast'], params['slow'], params['threshold'])

        # Full backtest
        bt = SimpleBacktest(df)
        result = bt.run(signals)

        # Buy-Hold benchmark
        buy_hold_return = (df['Close'].iloc[-1] / df['Close'].iloc[0] - 1) * 100

        print(f'\n{series_name} ({strategy}):')
        print(f'  Strategy return: {result["total_return"]:.2f}%')
        print(f'  Buy-Hold: {buy_hold_return:.2f}%')
        print(f'  Excess return: {result["total_return"] - buy_hold_return:.2f}%')
        print(f'  Max drawdown: {result["max_drawdown"]:.2f}%')
        print(f'  Number of trades: {result["n_trades"]}')


if __name__ == '__main__':
    main()
