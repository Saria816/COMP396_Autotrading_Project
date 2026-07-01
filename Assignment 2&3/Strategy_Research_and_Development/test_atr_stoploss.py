"""
ATR Stop-Loss Comparison Test (Portfolio-Level)

Compares signal-driven exits (current approach) against ATR trailing
stop-loss at different multipliers, using the same simplified backtest
methodology as the parameter optimization scripts (no slippage).

Output: robustness_results/atr_stop_loss_test.csv
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict

# Path settings
DATA_PATH = Path('../BT396_Version_0.1.3/DATA/PART2')
OUTPUT_DIR = Path('./robustness_results')
OUTPUT_DIR.mkdir(exist_ok=True)

# Asset classification and parameters (same as Team2.py)
ASSET_CONFIG = {
    'series_1': {'type': 'trend', 'strategy': 'breakout', 'lookback': 25},
    'series_3': {'type': 'trend', 'strategy': 'above_ma', 'ma_period': 20, 'confirm_days': 3},
    'series_4': {'type': 'trend', 'strategy': 'ma_crossover', 'fast': 10, 'slow': 30},
    'series_6': {'type': 'trend', 'strategy': 'above_ma', 'ma_period': 15, 'confirm_days': 2},
    'series_9': {'type': 'trend', 'strategy': 'above_ma', 'ma_period': 15, 'confirm_days': 2},
    'series_2': {'type': 'mr', 'strategy': 'zscore', 'lookback': 20, 'entry_z': 2.0, 'exit_z': 0.0},
    'series_7': {'type': 'mr', 'strategy': 'bollinger', 'lookback': 15, 'std_mult': 2.0},
    'series_8': {'type': 'mr', 'strategy': 'rsi', 'rsi_period': 14, 'oversold': 30},
    'series_10': {'type': 'mr', 'strategy': 'zscore', 'lookback': 25, 'entry_z': 2.5, 'exit_z': 0.0},
    'series_5': {'type': 'short', 'rsi_period': 7, 'overbought': 75, 'oversold': 40},
}

TREND_ASSETS = ['series_1', 'series_3', 'series_4', 'series_6', 'series_9']
MR_ASSETS = ['series_2', 'series_7', 'series_8', 'series_10']
SHORT_ASSETS = ['series_5']

TREND_ALLOCATION = 0.70
OTHER_ALLOCATION = 0.30
TREND_WEIGHT = TREND_ALLOCATION / len(TREND_ASSETS)   # 14%
OTHER_WEIGHT = OTHER_ALLOCATION / (len(MR_ASSETS) + len(SHORT_ASSETS))  # 6%

INITIAL_CASH = 1_000_000


def load_data() -> Dict[str, pd.DataFrame]:
    """Load all 10 series data"""
    data = {}
    for i in range(1, 11):
        filepath = DATA_PATH / f'{i:02d}.csv'
        df = pd.read_csv(filepath)
        date_col = 'Index' if 'Index' in df.columns else 'Date'
        df[date_col] = pd.to_datetime(df[date_col])
        df.set_index(date_col, inplace=True)
        df.sort_index(inplace=True)
        data[f'series_{i}'] = df
    return data


# ==============================================================
# Signal generation functions
# (same logic as optimization scripts and Team2.py)
# ==============================================================

def compute_rsi(close: pd.Series, period: int) -> pd.Series:
    """Compute RSI indicator"""
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / (loss + 1e-10)
    return 100 - (100 / (1 + rs))


def compute_atr(df: pd.DataFrame, period: int) -> pd.Series:
    """Compute ATR indicator"""
    high, low, close = df['High'], df['Low'], df['Close']
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def generate_signals_breakout(df, lookback):
    close = df['Close']
    rolling_high = close.rolling(lookback).max()
    rolling_low = close.rolling(lookback).min()
    signals = pd.Series(0, index=df.index)
    position = 0
    for i in range(lookback, len(df)):
        if position == 0:
            if close.iloc[i] >= rolling_high.iloc[i - 1]:
                signals.iloc[i] = 1
                position = 1
        else:
            if close.iloc[i] <= rolling_low.iloc[i - 1]:
                signals.iloc[i] = -1
                position = 0
    return signals


def generate_signals_above_ma(df, ma_period, confirm_days):
    close = df['Close']
    ma = close.rolling(ma_period).mean()
    signals = pd.Series(0, index=df.index)
    position = 0
    count = 0
    for i in range(ma_period, len(df)):
        if close.iloc[i] > ma.iloc[i]:
            count += 1
        else:
            count = 0

        if position == 0:
            if count >= confirm_days:
                signals.iloc[i] = 1
                position = 1
        else:
            if close.iloc[i] < ma.iloc[i]:
                signals.iloc[i] = -1
                position = 0
    return signals


def generate_signals_ma_crossover(df, fast_period, slow_period):
    close = df['Close']
    fast_ma = close.rolling(fast_period).mean()
    slow_ma = close.rolling(slow_period).mean()
    signals = pd.Series(0, index=df.index)
    position = 0
    for i in range(slow_period, len(df)):
        if position == 0:
            if fast_ma.iloc[i] > slow_ma.iloc[i] and fast_ma.iloc[i - 1] <= slow_ma.iloc[i - 1]:
                signals.iloc[i] = 1
                position = 1
        else:
            if fast_ma.iloc[i] < slow_ma.iloc[i] and fast_ma.iloc[i - 1] >= slow_ma.iloc[i - 1]:
                signals.iloc[i] = -1
                position = 0
    return signals


def generate_signals_zscore(df, lookback, entry_z, exit_z):
    close = df['Close']
    ma = close.rolling(lookback).mean()
    std = close.rolling(lookback).std()
    zscore = (close - ma) / std
    signals = pd.Series(0, index=df.index)
    position = 0
    for i in range(lookback, len(df)):
        z = zscore.iloc[i]
        if position == 0:
            if z < -entry_z:
                signals.iloc[i] = 1
                position = 1
        elif position == 1:
            if z > exit_z:
                signals.iloc[i] = -1
                position = 0
    return signals


def generate_signals_bollinger(df, lookback, std_mult):
    close = df['Close']
    ma = close.rolling(lookback).mean()
    std = close.rolling(lookback).std()
    lower = ma - std_mult * std
    signals = pd.Series(0, index=df.index)
    position = 0
    for i in range(lookback, len(df)):
        if position == 0:
            if close.iloc[i] < lower.iloc[i]:
                signals.iloc[i] = 1
                position = 1
        elif position == 1:
            if close.iloc[i] > ma.iloc[i]:
                signals.iloc[i] = -1
                position = 0
    return signals


def generate_signals_rsi_mr(df, rsi_period, oversold):
    close = df['Close']
    rsi = compute_rsi(close, rsi_period)
    signals = pd.Series(0, index=df.index)
    position = 0
    for i in range(rsi_period + 1, len(df)):
        r = rsi.iloc[i]
        if position == 0:
            if r < oversold:
                signals.iloc[i] = 1
                position = 1
        elif position == 1:
            if r > 50:
                signals.iloc[i] = -1
                position = 0
    return signals


def generate_signals_rsi_short(df, rsi_period, overbought, oversold):
    close = df['Close']
    rsi = compute_rsi(close, rsi_period)
    signals = pd.Series(0, index=df.index)
    position = 0
    for i in range(rsi_period + 1, len(df)):
        r = rsi.iloc[i]
        if position == 0:
            if r > overbought:
                signals.iloc[i] = -2  # Short signal
                position = -1
        elif position == -1:
            if r < oversold or r < 50:
                signals.iloc[i] = 1  # Cover signal
                position = 0
    return signals


def generate_asset_signals(name: str, df: pd.DataFrame) -> pd.Series:
    """Generate signals for a single asset based on its configured strategy"""
    cfg = ASSET_CONFIG[name]
    strategy = cfg.get('strategy', '')

    if cfg['type'] == 'trend':
        if strategy == 'breakout':
            return generate_signals_breakout(df, cfg['lookback'])
        elif strategy == 'above_ma':
            return generate_signals_above_ma(df, cfg['ma_period'], cfg['confirm_days'])
        elif strategy == 'ma_crossover':
            return generate_signals_ma_crossover(df, cfg['fast'], cfg['slow'])
    elif cfg['type'] == 'mr':
        if strategy == 'zscore':
            return generate_signals_zscore(df, cfg['lookback'], cfg['entry_z'], cfg['exit_z'])
        elif strategy == 'bollinger':
            return generate_signals_bollinger(df, cfg['lookback'], cfg['std_mult'])
        elif strategy == 'rsi':
            return generate_signals_rsi_mr(df, cfg['rsi_period'], cfg['oversold'])
    elif cfg['type'] == 'short':
        return generate_signals_rsi_short(
            df, cfg['rsi_period'], cfg['overbought'], cfg['oversold'])

    return pd.Series(0, index=df.index)


# ==============================================================
# Portfolio-level backtest with optional ATR stop-loss
# ==============================================================

def run_portfolio_backtest(data: Dict[str, pd.DataFrame],
                           atr_mult: float = 0.0,
                           atr_period: int = 14,
                           only_trend: bool = False,
                           trailing: bool = True) -> Dict:
    """
    Run portfolio-level backtest across all 10 assets with shared cash pool.

    Args:
        data: dict of asset name -> DataFrame
        atr_mult: ATR multiplier for stop-loss (0 = disabled)
        atr_period: ATR calculation period
        only_trend: if True, ATR stop applies only to trend assets
        trailing: if True, use trailing stop; if False, use fixed stop from entry

    Returns:
        dict with return, max_drawdown, pd_ratio, stop_count
    """
    n_bars = len(next(iter(data.values())))

    # Pre-compute signals and ATR for each asset
    signals = {}
    atrs = {}
    for name, df in data.items():
        signals[name] = generate_asset_signals(name, df)
        apply_atr = (atr_mult > 0
                     and ASSET_CONFIG[name]['type'] != 'short'
                     and (not only_trend or ASSET_CONFIG[name]['type'] == 'trend'))
        if apply_atr:
            atrs[name] = compute_atr(df, atr_period)

    # Portfolio state
    cash = float(INITIAL_CASH)
    positions = {name: 0 for name in data}    # shares held
    stop_levels = {}                           # name -> stop price
    stop_count = 0
    equity_curve = []

    for i in range(n_bars):
        # Current portfolio value
        port_value = cash
        for name, df in data.items():
            price = df['Close'].iloc[i]
            port_value += positions[name] * price

        # Process each asset
        for name, df in data.items():
            cfg = ASSET_CONFIG[name]
            price = df['Close'].iloc[i]
            pos = positions[name]
            sig = signals[name].iloc[i]

            # ATR stop-loss check (long positions only)
            if (atr_mult > 0 and name in atrs and pos > 0):
                atr_val = atrs[name].iloc[i] if not np.isnan(atrs[name].iloc[i]) else 0
                if atr_val > 0:
                    if trailing:
                        new_stop = price - atr_mult * atr_val
                        if name in stop_levels:
                            stop_levels[name] = max(stop_levels[name], new_stop)
                        else:
                            stop_levels[name] = new_stop
                    # For fixed stop, stop_levels[name] was set at entry and never updated

                    if name in stop_levels and price < stop_levels[name] and sig != -1:
                        sig = -1
                        stop_count += 1
                        stop_levels.pop(name, None)

            # Determine weight
            if name in TREND_ASSETS:
                weight = TREND_WEIGHT
            else:
                weight = OTHER_WEIGHT
            target_value = port_value * weight

            # Execute trades
            if cfg['type'] == 'short':
                # Short strategy signals: -2 = open short, 1 = cover
                if sig == -2 and pos >= 0:
                    if pos > 0:
                        cash += pos * price
                        positions[name] = 0
                    shares = int(target_value * 0.95 / price)
                    if shares > 0:
                        positions[name] = -shares
                        cash += shares * price
                elif sig == 1 and pos < 0:
                    cash += pos * price
                    positions[name] = 0
            else:
                # Long strategy signals: 1 = buy, -1 = sell
                if sig == 1 and pos <= 0:
                    if pos < 0:
                        cash += pos * price
                        positions[name] = 0
                    shares = int(target_value * 0.95 / price)
                    if shares > 0:
                        positions[name] = shares
                        cash -= shares * price
                        # Initialize ATR stop level (both fixed and trailing)
                        if atr_mult > 0 and name in atrs:
                            atr_val = atrs[name].iloc[i]
                            if not np.isnan(atr_val) and atr_val > 0:
                                stop_levels[name] = price - atr_mult * atr_val
                elif sig == -1 and pos > 0:
                    cash += pos * price
                    positions[name] = 0
                    stop_levels.pop(name, None)

        # Record portfolio equity
        equity = cash
        for name, df in data.items():
            equity += positions[name] * df['Close'].iloc[i]
        equity_curve.append(equity)

    # Final liquidation
    for name, df in data.items():
        if positions[name] != 0:
            cash += positions[name] * df['Close'].iloc[-1]
            positions[name] = 0

    # Calculate metrics
    equity = np.array(equity_curve)
    total_return = (equity[-1] / INITIAL_CASH - 1) * 100
    cummax = np.maximum.accumulate(equity)
    drawdown = (equity - cummax) / cummax
    max_drawdown = np.min(drawdown) * 100
    pd_ratio = total_return / abs(max_drawdown) if max_drawdown != 0 else 0

    return {
        'total_return': round(total_return, 2),
        'max_drawdown': round(max_drawdown, 2),
        'pd_ratio': round(pd_ratio, 2),
        'stop_count': stop_count,
        'final_equity': equity[-1],
    }


def main():
    print("=" * 60)
    print("ATR Stop-Loss Comparison Test (Portfolio-Level)")
    print("Methodology: SimpleBacktest (no slippage), fixed ATR stop-loss")
    print("=" * 60)

    data = load_data()
    print(f"Loaded {len(data)} assets, {len(next(iter(data.values())))} bars each")

    # Three scenarios: no stop, ATR x2.0, ATR x3.5
    # Uses fixed (non-trailing) stop-loss on all long positions
    scenarios = [
        ("Signal-Driven (No Stop)", 0.0),
        ("ATR x2.0 Fixed Stop", 2.0),
        ("ATR x3.5 Fixed Stop", 3.5),
    ]

    results = []
    for name, atr_mult in scenarios:
        print(f"\nTesting: {name}...")
        res = run_portfolio_backtest(
            data, atr_mult=atr_mult, atr_period=14,
            only_trend=False, trailing=False)
        results.append({
            "Exit Method": name,
            "Return(%)": res['total_return'],
            "Max Drawdown(%)": res['max_drawdown'],
            "PD Ratio": res['pd_ratio'],
            "Stop Triggers": res['stop_count'],
        })
        print(f"  Return: {res['total_return']:.2f}%, Max DD: {res['max_drawdown']:.2f}%, "
              f"PD: {res['pd_ratio']:.2f}, Stops: {res['stop_count']}")

    df = pd.DataFrame(results)
    print("\n" + "=" * 60)
    print("Results (Table 2-14 in report):")
    print("=" * 60)
    print(df.to_string(index=False))

    csv_path = OUTPUT_DIR / "atr_stop_loss_test.csv"
    df.to_csv(csv_path, index=False)
    print(f"\nResults saved to: {csv_path}")


if __name__ == "__main__":
    main()
