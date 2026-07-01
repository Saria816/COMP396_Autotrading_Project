"""
Short/defensive strategy parameter optimization script
Applicable assets: series_5 (Total return < 0)
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

# Short strategy assets
SHORT_SERIES = ['series_5']


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
    """Simplified backtesting engine with short selling support"""

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

            # Short signal (-2)
            if signal == -2 and self.position >= 0:
                if self.position > 0:
                    self.cash += self.position * price
                    self.position = 0
                # Open short position
                shares = int(self.cash * 0.95 / price)
                if shares > 0:
                    self.position = -shares
                    self.cash += shares * price  # Receive funds from short sale
                    self.trades.append({'type': 'short', 'price': price, 'day': i})

            # Cover signal (1)
            elif signal == 1 and self.position < 0:
                self.cash += self.position * price  # Cover short position
                self.trades.append({'type': 'cover', 'price': price, 'day': i})
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

        n_trades = len([t for t in self.trades if t['type'] == 'short'])

        return {
            'total_return': total_return,
            'sharpe': sharpe,
            'max_drawdown': max_drawdown,
            'n_trades': n_trades,
            'final_equity': equity[-1]
        }


# ============================================================
# Strategy 1: Trend Short (short below SMA)
# ============================================================
def generate_short_signals_trend(df: pd.DataFrame, sma_period: int,
                                  stop_loss_pct: float) -> pd.Series:
    """Trend short: short when price breaks below SMA, cover above SMA or on stop loss"""
    close = df['Close']
    sma = close.rolling(sma_period).mean()

    signals = pd.Series(0, index=df.index)
    position = 0
    entry_price = 0

    for i in range(sma_period, len(df)):
        price = close.iloc[i]

        if position == 0:
            if price < sma.iloc[i] and close.iloc[i-1] >= sma.iloc[i-1]:
                signals.iloc[i] = -2  # Short
                position = -1
                entry_price = price
        elif position == -1:
            if price > sma.iloc[i]:
                signals.iloc[i] = 1  # Cover
                position = 0
            elif price > entry_price * (1 + stop_loss_pct):
                signals.iloc[i] = 1  # Stop loss
                position = 0

    return signals


# ============================================================
# Strategy 2: MA Death Cross Short
# ============================================================
def generate_short_signals_ma_cross(df: pd.DataFrame, fast_period: int,
                                     slow_period: int, stop_loss_pct: float) -> pd.Series:
    """MA death cross short: short on death cross, cover on golden cross or stop loss"""
    close = df['Close']
    fast_ma = close.rolling(fast_period).mean()
    slow_ma = close.rolling(slow_period).mean()

    signals = pd.Series(0, index=df.index)
    position = 0
    entry_price = 0

    for i in range(slow_period, len(df)):
        price = close.iloc[i]

        if position == 0:
            # Death cross short
            if fast_ma.iloc[i] < slow_ma.iloc[i] and fast_ma.iloc[i-1] >= slow_ma.iloc[i-1]:
                signals.iloc[i] = -2
                position = -1
                entry_price = price
        elif position == -1:
            # Golden cross cover
            if fast_ma.iloc[i] > slow_ma.iloc[i] and fast_ma.iloc[i-1] <= slow_ma.iloc[i-1]:
                signals.iloc[i] = 1
                position = 0
            elif price > entry_price * (1 + stop_loss_pct):
                signals.iloc[i] = 1  # Stop loss
                position = 0

    return signals


# ============================================================
# Strategy 3: RSI Overbought Short
# ============================================================
def generate_short_signals_rsi(df: pd.DataFrame, rsi_period: int,
                                overbought: float, oversold: float) -> pd.Series:
    """RSI overbought short: short when RSI overbought, cover when oversold or neutral"""
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
            if r > overbought:
                signals.iloc[i] = -2  # Overbought short
                position = -1
        elif position == -1:
            if r < oversold or r < 50:
                signals.iloc[i] = 1  # Cover
                position = 0

    return signals


# ============================================================
# Strategy 4: Bollinger Upper Band Short
# ============================================================
def generate_short_signals_bollinger(df: pd.DataFrame, lookback: int,
                                      std_mult: float) -> pd.Series:
    """Bollinger short: short above upper band, cover at middle band"""
    close = df['Close']

    ma = close.rolling(lookback).mean()
    std = close.rolling(lookback).std()
    upper = ma + std_mult * std

    signals = pd.Series(0, index=df.index)
    position = 0

    for i in range(lookback, len(df)):
        price = close.iloc[i]
        mid = ma.iloc[i]

        if position == 0:
            if price > upper.iloc[i]:
                signals.iloc[i] = -2  # Overbought short
                position = -1
        elif position == -1:
            if price < mid:
                signals.iloc[i] = 1  # Cover
                position = 0

    return signals


# ============================================================
# Parameter grid definition
# ============================================================
TREND_SHORT_GRID = {
    'sma_period': [10, 15, 20, 25, 30, 40, 50, 100, 200],
    'stop_loss_pct': [0.02, 0.03, 0.05, 0.07, 0.10, 0.15]
}

MA_CROSS_SHORT_GRID = {
    'fast_period': [5, 10, 15, 20],
    'slow_period': [20, 30, 40, 50, 60],
    'stop_loss_pct': [0.03, 0.05, 0.07, 0.10]
}

RSI_SHORT_GRID = {
    'rsi_period': [7, 10, 14, 20],
    'overbought': [65, 70, 75, 80],
    'oversold': [30, 35, 40]
}

BOLLINGER_SHORT_GRID = {
    'lookback': [10, 15, 20, 25, 30],
    'std_mult': [1.5, 2.0, 2.5, 3.0]
}


def optimize_short_single_asset(df: pd.DataFrame, series_name: str, train_end: int) -> pd.DataFrame:
    """Iterate all short strategy types and parameter combinations for a single asset"""
    results = []

    # ============================================================
    # Strategy 1: Trend Short
    # ============================================================
    for sma_period, stop_loss in product(
        TREND_SHORT_GRID['sma_period'],
        TREND_SHORT_GRID['stop_loss_pct']
    ):
        try:
            signals = generate_short_signals_trend(df, sma_period, stop_loss)

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
                'strategy': 'trend_short',
                'params': f'sma={sma_period},stop={stop_loss}',
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
    # Strategy 2: MA Death Cross Short
    # ============================================================
    for fast, slow, stop_loss in product(
        MA_CROSS_SHORT_GRID['fast_period'],
        MA_CROSS_SHORT_GRID['slow_period'],
        MA_CROSS_SHORT_GRID['stop_loss_pct']
    ):
        if fast >= slow:
            continue

        try:
            signals = generate_short_signals_ma_cross(df, fast, slow, stop_loss)

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
                'strategy': 'ma_cross_short',
                'params': f'fast={fast},slow={slow},stop={stop_loss}',
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
    # Strategy 3: RSI Overbought Short
    # ============================================================
    for rsi_period, overbought, oversold in product(
        RSI_SHORT_GRID['rsi_period'],
        RSI_SHORT_GRID['overbought'],
        RSI_SHORT_GRID['oversold']
    ):
        try:
            signals = generate_short_signals_rsi(df, rsi_period, overbought, oversold)

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
                'strategy': 'rsi_short',
                'params': f'rsi={rsi_period},ob={overbought},os={oversold}',
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
    # Strategy 4: Bollinger Short
    # ============================================================
    for lookback, std_mult in product(
        BOLLINGER_SHORT_GRID['lookback'],
        BOLLINGER_SHORT_GRID['std_mult']
    ):
        try:
            signals = generate_short_signals_bollinger(df, lookback, std_mult)

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
                'strategy': 'bollinger_short',
                'params': f'lookback={lookback},std={std_mult}',
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
    print('Short/Defensive Strategy Parameter Optimization - series_5')
    print('='*80)

    # Load data
    data = load_data()
    print(f'Loaded {len(data)} series')

    # 7:3 split
    TOTAL_DAYS = len(data['series_1'])
    TRAIN_END = int(TOTAL_DAYS * 0.7)
    print(f'Train set: {TRAIN_END} days, Test set: {TOTAL_DAYS - TRAIN_END} days')
    print(f'Short assets: {SHORT_SERIES}')

    # Parameter combination counts
    n_trend = len(TREND_SHORT_GRID['sma_period']) * len(TREND_SHORT_GRID['stop_loss_pct'])
    n_ma = len(MA_CROSS_SHORT_GRID['fast_period']) * len(MA_CROSS_SHORT_GRID['slow_period']) * len(MA_CROSS_SHORT_GRID['stop_loss_pct'])
    n_rsi = len(RSI_SHORT_GRID['rsi_period']) * len(RSI_SHORT_GRID['overbought']) * len(RSI_SHORT_GRID['oversold'])
    n_bb = len(BOLLINGER_SHORT_GRID['lookback']) * len(BOLLINGER_SHORT_GRID['std_mult'])
    print(f'\nParameter combinations: trend_short={n_trend}, ma_cross={n_ma}, RSI={n_rsi}, bollinger={n_bb}')
    print(f'Total: approx. {n_trend + n_ma + n_rsi + n_bb} combinations')

    # Optimization
    for series_name in SHORT_SERIES:
        print(f'\n{"="*60}')
        print(f'Optimizing {series_name}...')
        print(f'{"="*60}')

        df = data[series_name]
        results_df = optimize_short_single_asset(df, series_name, TRAIN_END)

        # Save full results
        results_df.to_csv(RESULTS_PATH / f'short_{series_name}_all_params.csv', index=False)

        # Get best result
        best = results_df.iloc[0]

        print(f'\nSearched {len(results_df)} parameter combinations')
        print(f'\n{series_name} Best Strategy:')
        print(f'  Strategy type: {best["strategy"]}')
        print(f'  Params: {best["params"]}')
        print(f'  Train return: {best["train_return"]:.2f}%')
        print(f'  Valid return: {best["valid_return"]:.2f}%')
        print(f'  Valid Sharpe: {best["valid_sharpe"]:.2f}')
        print(f'  Valid MaxDD: {best["valid_maxdd"]:.2f}%')
        print(f'  Composite score: {best["score"]:.4f}')

        # Show Top 10 strategies
        print(f'\nTop 10 Strategies:')
        for idx, row in results_df.head(10).iterrows():
            print(f'  {row["strategy"]}: {row["params"]} | valid_return={row["valid_return"]:.2f}%, Sharpe={row["valid_sharpe"]:.2f}')

        # Extract best result for each variant
        variant_results = extract_variant_best(results_df, series_name)

        print(f'\n{series_name} Best Result per Variant:')
        for vr in variant_results:
            print(f'  {vr["strategy"]:18s} | Score={vr["score"]:.4f} | valid_return={vr["valid_return"]:.2f}% | valid_sharpe={vr["valid_sharpe"]:.2f} | valid_maxdd={vr["valid_maxdd"]:.2f}%')

        # Save variant summary
        variant_summary_df = pd.DataFrame(variant_results)
        variant_summary_df.to_csv(RESULTS_PATH / 'short_variant_summary.csv', index=False)

        # Save optimal params
        optimal_params = {
            series_name: {
                'strategy': best['strategy'],
                'params': best['params'],
                'train_return': float(best['train_return']),
                'valid_return': float(best['valid_return']),
                'valid_sharpe': float(best['valid_sharpe']),
                'valid_maxdd': float(best['valid_maxdd'])
            }
        }

        with open(RESULTS_PATH / 'optimal_short_params.json', 'w') as f:
            json.dump(optimal_params, f, indent=2)

    # ============================================================
    # Full data backtest validation
    # ============================================================
    print('\n' + '='*80)
    print('Full Data Backtest Validation (1000 days)')
    print('='*80)

    df = data['series_5']
    best_strategy = best['strategy']
    best_params = best['params']

    # Parse parameters
    params = {}
    for item in best_params.split(','):
        key, val = item.split('=')
        params[key] = float(val) if '.' in val else int(val)

    # Generate signals
    if best_strategy == 'trend_short':
        signals = generate_short_signals_trend(df, params['sma'], params['stop'])
    elif best_strategy == 'ma_cross_short':
        signals = generate_short_signals_ma_cross(df, params['fast'], params['slow'], params['stop'])
    elif best_strategy == 'rsi_short':
        signals = generate_short_signals_rsi(df, params['rsi'], params['ob'], params['os'])
    elif best_strategy == 'bollinger_short':
        signals = generate_short_signals_bollinger(df, params['lookback'], params['std'])

    # Full backtest
    bt = SimpleBacktest(df)
    result = bt.run(signals)

    # Buy-Hold benchmark (for declining assets, Buy-Hold yields negative returns)
    buy_hold_return = (df['Close'].iloc[-1] / df['Close'].iloc[0] - 1) * 100

    print(f'\nseries_5 ({best_strategy}):')
    print(f'  Strategy return: {result["total_return"]:.2f}%')
    print(f'  Buy-Hold: {buy_hold_return:.2f}%')
    print(f'  Excess return: {result["total_return"] - buy_hold_return:.2f}%')
    print(f'  Max drawdown: {result["max_drawdown"]:.2f}%')
    print(f'  Number of trades: {result["n_trades"]}')

    print(f'\nResults saved to {RESULTS_PATH}')


if __name__ == '__main__':
    main()
