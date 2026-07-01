"""
Trend/Momentum Strategy Parameter Optimization Script - Independent Optimization per Asset
Applicable assets: series_1, series_3, series_4, series_6, series_9 (Return/MaxDD Ratio >= 1.1)
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

# Trend/momentum strategy assets
TREND_SERIES = ['series_1', 'series_3', 'series_4', 'series_6', 'series_9']


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
                    self.trades.append({'type': 'buy', 'price': price, 'shares': shares, 'day': i})

            elif signal == -1 and self.position > 0:
                self.cash += self.position * price
                self.trades.append({'type': 'sell', 'price': price, 'shares': self.position, 'day': i})
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

        pd_ratio = total_return / abs(max_drawdown) if max_drawdown != 0 else 0
        n_trades = len([t for t in self.trades if t['type'] == 'buy'])

        return {
            'total_return': total_return,
            'sharpe': sharpe,
            'max_drawdown': max_drawdown,
            'pd_ratio': pd_ratio,
            'n_trades': n_trades,
            'final_equity': equity[-1]
        }


# ============================================================
# Strategy 1: Dual Moving Average Crossover + ATR Stop Loss
# ============================================================
def generate_trend_signals_ma(df: pd.DataFrame, fast_period: int, slow_period: int,
                               atr_period: int, atr_mult: float) -> pd.Series:
    """Dual moving average crossover + ATR trailing stop loss"""
    close = df['Close']
    high = df['High']
    low = df['Low']

    fast_ma = close.rolling(fast_period).mean()
    slow_ma = close.rolling(slow_period).mean()

    # ATR calculation
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(atr_period).mean()

    signals = pd.Series(0, index=df.index)
    position = 0
    stop_loss = 0

    for i in range(slow_period, len(df)):
        if position == 0:
            if fast_ma.iloc[i] > slow_ma.iloc[i] and fast_ma.iloc[i-1] <= slow_ma.iloc[i-1]:
                signals.iloc[i] = 1
                position = 1
                stop_loss = close.iloc[i] - atr_mult * atr.iloc[i]
        else:
            if fast_ma.iloc[i] < slow_ma.iloc[i] and fast_ma.iloc[i-1] >= slow_ma.iloc[i-1]:
                signals.iloc[i] = -1
                position = 0
            elif close.iloc[i] < stop_loss:
                signals.iloc[i] = -1
                position = 0
            else:
                new_stop = close.iloc[i] - atr_mult * atr.iloc[i]
                stop_loss = max(stop_loss, new_stop)

    return signals


# ============================================================
# Strategy 2: Momentum Breakout Strategy
# ============================================================
def generate_trend_signals_breakout(df: pd.DataFrame, lookback: int,
                                     hold_days: int) -> pd.Series:
    """Buy on price breaking N-day high, sell after fixed holding days or on breaking N-day low"""
    close = df['Close']

    rolling_high = close.rolling(lookback).max()
    rolling_low = close.rolling(lookback).min()

    signals = pd.Series(0, index=df.index)
    position = 0
    entry_day = 0

    for i in range(lookback, len(df)):
        if position == 0:
            if close.iloc[i] >= rolling_high.iloc[i-1]:  # Break above N-day high
                signals.iloc[i] = 1
                position = 1
                entry_day = i
        else:
            # Holding period expired or price broke below N-day low
            if (i - entry_day >= hold_days) or (close.iloc[i] <= rolling_low.iloc[i-1]):
                signals.iloc[i] = -1
                position = 0

    return signals


# ============================================================
# Strategy 3: MACD Trend Strategy
# ============================================================
def generate_trend_signals_macd(df: pd.DataFrame, fast_period: int,
                                 slow_period: int, signal_period: int) -> pd.Series:
    """Buy on MACD bullish crossover, sell on bearish crossover"""
    close = df['Close']

    ema_fast = close.ewm(span=fast_period, adjust=False).mean()
    ema_slow = close.ewm(span=slow_period, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()

    signals = pd.Series(0, index=df.index)
    position = 0

    for i in range(slow_period + signal_period, len(df)):
        if position == 0:
            if macd_line.iloc[i] > signal_line.iloc[i] and macd_line.iloc[i-1] <= signal_line.iloc[i-1]:
                signals.iloc[i] = 1
                position = 1
        else:
            if macd_line.iloc[i] < signal_line.iloc[i] and macd_line.iloc[i-1] >= signal_line.iloc[i-1]:
                signals.iloc[i] = -1
                position = 0

    return signals


# ============================================================
# Strategy 4: Trend Following (Price Above Moving Average)
# ============================================================
def generate_trend_signals_above_ma(df: pd.DataFrame, ma_period: int,
                                     confirm_days: int) -> pd.Series:
    """Buy when price stays above MA for N consecutive days, sell when price drops below MA"""
    close = df['Close']
    ma = close.rolling(ma_period).mean()

    signals = pd.Series(0, index=df.index)
    position = 0

    for i in range(ma_period + confirm_days, len(df)):
        if position == 0:
            # Check if price has been above MA for confirm_days consecutive days
            above_count = sum(close.iloc[i-confirm_days+1:i+1] > ma.iloc[i-confirm_days+1:i+1])
            if above_count == confirm_days:
                signals.iloc[i] = 1
                position = 1
        else:
            if close.iloc[i] < ma.iloc[i]:
                signals.iloc[i] = -1
                position = 0

    return signals


# ============================================================
# Single Asset Optimization Function
# ============================================================
def optimize_single_asset(df: pd.DataFrame, series_name: str, train_end: int) -> Dict:
    """Optimize all strategy types for a single asset, return the best strategy and parameters"""

    results = []

    # ============================================================
    # Strategy 1: Dual Moving Average Crossover + ATR Stop Loss
    # ============================================================
    ma_param_grid = {
        'fast_period': [3, 5, 8, 10, 15, 20],
        'slow_period': [15, 20, 25, 30, 40, 50, 60],
        'atr_period': [10, 14, 20],
        'atr_mult': [1.5, 2.0, 2.5, 3.0, 3.5]
    }

    for fast, slow, atr_p, atr_m in product(
        ma_param_grid['fast_period'],
        ma_param_grid['slow_period'],
        ma_param_grid['atr_period'],
        ma_param_grid['atr_mult']
    ):
        if fast >= slow:
            continue

        try:
            signals = generate_trend_signals_ma(df, fast, slow, atr_p, atr_m)

            # Training set
            train_df = df.iloc[:train_end]
            train_signals = signals.iloc[:train_end]
            bt_train = SimpleBacktest(train_df)
            train_result = bt_train.run(train_signals)

            # Validation set
            valid_df = df.iloc[train_end:]
            valid_signals = signals.iloc[train_end:]
            bt_valid = SimpleBacktest(valid_df)
            valid_result = bt_valid.run(valid_signals)

            # Calculate composite score
            score = (
                0.3 * np.clip(train_result['sharpe'], -2, 2) / 2 +
                0.3 * np.clip(valid_result['sharpe'], -2, 2) / 2 +
                0.2 * np.clip(valid_result['total_return'], -50, 100) / 100 +
                0.2 * (1 - abs(np.clip(valid_result['max_drawdown'], -50, 0)) / 50)
            )

            results.append({
                'strategy': 'ma_crossover',
                'params': {'fast_period': fast, 'slow_period': slow, 'atr_period': atr_p, 'atr_mult': atr_m},
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
    # Strategy 2: Momentum Breakout
    # ============================================================
    breakout_param_grid = {
        'lookback': [5, 10, 15, 20, 25, 30, 40],
        'hold_days': [5, 10, 15, 20, 30, 40, 50]
    }

    for lookback, hold_days in product(
        breakout_param_grid['lookback'],
        breakout_param_grid['hold_days']
    ):
        try:
            signals = generate_trend_signals_breakout(df, lookback, hold_days)

            train_df = df.iloc[:train_end]
            train_signals = signals.iloc[:train_end]
            bt_train = SimpleBacktest(train_df)
            train_result = bt_train.run(train_signals)

            valid_df = df.iloc[train_end:]
            valid_signals = signals.iloc[train_end:]
            bt_valid = SimpleBacktest(valid_df)
            valid_result = bt_valid.run(valid_signals)

            score = (
                0.3 * np.clip(train_result['sharpe'], -2, 2) / 2 +
                0.3 * np.clip(valid_result['sharpe'], -2, 2) / 2 +
                0.2 * np.clip(valid_result['total_return'], -50, 100) / 100 +
                0.2 * (1 - abs(np.clip(valid_result['max_drawdown'], -50, 0)) / 50)
            )

            results.append({
                'strategy': 'breakout',
                'params': {'lookback': lookback, 'hold_days': hold_days},
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
    # Strategy 3: MACD
    # ============================================================
    macd_param_grid = {
        'fast_period': [8, 10, 12, 15],
        'slow_period': [20, 26, 30, 35],
        'signal_period': [5, 7, 9, 12]
    }

    for fast, slow, signal in product(
        macd_param_grid['fast_period'],
        macd_param_grid['slow_period'],
        macd_param_grid['signal_period']
    ):
        if fast >= slow:
            continue

        try:
            signals = generate_trend_signals_macd(df, fast, slow, signal)

            train_df = df.iloc[:train_end]
            train_signals = signals.iloc[:train_end]
            bt_train = SimpleBacktest(train_df)
            train_result = bt_train.run(train_signals)

            valid_df = df.iloc[train_end:]
            valid_signals = signals.iloc[train_end:]
            bt_valid = SimpleBacktest(valid_df)
            valid_result = bt_valid.run(valid_signals)

            score = (
                0.3 * np.clip(train_result['sharpe'], -2, 2) / 2 +
                0.3 * np.clip(valid_result['sharpe'], -2, 2) / 2 +
                0.2 * np.clip(valid_result['total_return'], -50, 100) / 100 +
                0.2 * (1 - abs(np.clip(valid_result['max_drawdown'], -50, 0)) / 50)
            )

            results.append({
                'strategy': 'macd',
                'params': {'fast_period': fast, 'slow_period': slow, 'signal_period': signal},
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
    # Strategy 4: Trend Following (Above Moving Average)
    # ============================================================
    above_ma_param_grid = {
        'ma_period': [10, 15, 20, 30, 40, 50, 60],
        'confirm_days': [1, 2, 3, 5, 7, 10]
    }

    for ma_period, confirm_days in product(
        above_ma_param_grid['ma_period'],
        above_ma_param_grid['confirm_days']
    ):
        try:
            signals = generate_trend_signals_above_ma(df, ma_period, confirm_days)

            train_df = df.iloc[:train_end]
            train_signals = signals.iloc[:train_end]
            bt_train = SimpleBacktest(train_df)
            train_result = bt_train.run(train_signals)

            valid_df = df.iloc[train_end:]
            valid_signals = signals.iloc[train_end:]
            bt_valid = SimpleBacktest(valid_df)
            valid_result = bt_valid.run(valid_signals)

            score = (
                0.3 * np.clip(train_result['sharpe'], -2, 2) / 2 +
                0.3 * np.clip(valid_result['sharpe'], -2, 2) / 2 +
                0.2 * np.clip(valid_result['total_return'], -50, 100) / 100 +
                0.2 * (1 - abs(np.clip(valid_result['max_drawdown'], -50, 0)) / 50)
            )

            results.append({
                'strategy': 'above_ma',
                'params': {'ma_period': ma_period, 'confirm_days': confirm_days},
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

    # Sort by score, return best results
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('score', ascending=False)

    # Save full optimization results for this asset
    results_df.to_csv(RESULTS_PATH / f'trend_{series_name}_optimization.csv', index=False)

    return results_df


def extract_variant_best(results_df: pd.DataFrame, series_name: str) -> List[Dict]:
    """Extract the best parameter combination for each strategy variant from full optimization results"""
    variant_results = []
    for strategy in results_df['strategy'].unique():
        sub = results_df[results_df['strategy'] == strategy]
        best_idx = sub['score'].idxmax()
        best = sub.loc[best_idx]
        # Convert dict parameters to key=value string format
        params = best['params']
        if isinstance(params, dict):
            params_str = ','.join(f'{k}={v}' for k, v in params.items())
        else:
            params_str = str(params)
        variant_results.append({
            'series': series_name,
            'strategy': best['strategy'],
            'params': params_str,
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
    print('Trend/Momentum Strategy Parameter Optimization - Independent Optimization per Asset')
    print('='*80)

    # Load data
    data = load_data()
    print(f'Loaded {len(data)} series')

    # 7:3 split
    TOTAL_DAYS = len(data['series_1'])
    TRAIN_END = int(TOTAL_DAYS * 0.7)
    print(f'Training set: {TRAIN_END} days, Test set: {TOTAL_DAYS - TRAIN_END} days')
    print(f'Trend strategy assets: {TREND_SERIES}')

    # Store optimal parameters for each asset
    optimal_params = {}
    summary_results = []
    variant_summary_results = []

    for series_name in TREND_SERIES:
        print(f'\n{"="*60}')
        print(f'Optimizing {series_name}...')
        print(f'{"="*60}')

        df = data[series_name]
        results_df = optimize_single_asset(df, series_name, TRAIN_END)

        # Get best result
        best = results_df.iloc[0]

        print(f'\n{series_name} Best Strategy:')
        print(f'  Strategy type: {best["strategy"]}')
        print(f'  Parameters: {best["params"]}')
        print(f'  Train return: {best["train_return"]:.2f}%')
        print(f'  Test return: {best["valid_return"]:.2f}%')
        print(f'  Test Sharpe: {best["valid_sharpe"]:.2f}')
        print(f'  Test MaxDD: {best["valid_maxdd"]:.2f}%')
        print(f'  Composite score: {best["score"]:.4f}')

        # Display Top 5 strategies
        print(f'\n{series_name} Top 5 Strategies:')
        for i, row in results_df.head(5).iterrows():
            print(f'  {row["strategy"]}: Test return={row["valid_return"]:.2f}%, Sharpe={row["valid_sharpe"]:.2f}, Score={row["score"]:.4f}')

        # Extract best result for each variant
        variant_results = extract_variant_best(results_df, series_name)
        variant_summary_results.extend(variant_results)

        print(f'\n{series_name} Best result per variant:')
        for vr in variant_results:
            print(f'  {vr["strategy"]:15s} | Score={vr["score"]:.4f} | Test return={vr["valid_return"]:.2f}% | Test Sharpe={vr["valid_sharpe"]:.2f} | Test MaxDD={vr["valid_maxdd"]:.2f}%')

        # Save optimal parameters
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
            'params': str(best['params']),
            'train_return': best['train_return'],
            'valid_return': best['valid_return'],
            'valid_sharpe': best['valid_sharpe'],
            'valid_maxdd': best['valid_maxdd'],
            'score': best['score']
        })

    # ============================================================
    # Summary of Results
    # ============================================================
    print('\n' + '='*80)
    print('Optimal Parameters Summary for All Assets')
    print('='*80)

    summary_df = pd.DataFrame(summary_results)
    print('\n')
    print(summary_df.to_string(index=False))

    # Calculate average returns
    avg_train = summary_df['train_return'].mean()
    avg_valid = summary_df['valid_return'].mean()
    print(f'\nAverage train return: {avg_train:.2f}%')
    print(f'Average test return: {avg_valid:.2f}%')

    # Save results
    summary_df.to_csv(RESULTS_PATH / 'trend_individual_summary.csv', index=False)

    with open(RESULTS_PATH / 'optimal_trend_params.json', 'w') as f:
        json.dump(optimal_params, f, indent=2, default=str)

    # Save best results summary for each variant
    variant_summary_df = pd.DataFrame(variant_summary_results)
    variant_summary_df.to_csv(RESULTS_PATH / 'trend_variant_summary.csv', index=False)

    print('\n' + '='*80)
    print('Best Results Summary per Asset per Variant')
    print('='*80)
    print(variant_summary_df.to_string(index=False))

    print(f'\nResults saved to {RESULTS_PATH}')

    # ============================================================
    # Full Data Backtest Verification
    # ============================================================
    print('\n' + '='*80)
    print('Full Data Backtest Verification (1000 days)')
    print('='*80)

    for series_name in TREND_SERIES:
        df = data[series_name]
        best_params = optimal_params[series_name]
        strategy = best_params['strategy']
        params = best_params['params']

        # Generate signals
        if strategy == 'ma_crossover':
            signals = generate_trend_signals_ma(df, **params)
        elif strategy == 'breakout':
            signals = generate_trend_signals_breakout(df, **params)
        elif strategy == 'macd':
            signals = generate_trend_signals_macd(df, **params)
        elif strategy == 'above_ma':
            signals = generate_trend_signals_above_ma(df, **params)

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
