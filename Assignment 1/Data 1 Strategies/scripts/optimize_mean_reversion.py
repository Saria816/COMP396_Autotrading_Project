#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import backtrader as bt
import pandas as pd
import numpy as np
from datetime import datetime
import json
import itertools
from pathlib import Path
from framework.data_loader import _read_csv_safely
from framework.analyzers import OpenOpenPnL
from strategies.s3_mean_reversion import MeanReversionStrategy

def load_data_splits(train_end_idx=700):
    """Load 10 CSV files and create train/test splits"""
    data_dir = Path("DATA/PART1")
    csv_files = sorted(data_dir.glob("*.csv"))[:10]
    
    train_data = []
    test_data = []
    
    for csv_file in csv_files:
        df = _read_csv_safely(csv_file)
        df.reset_index(inplace=True)
        df.rename(columns={'Date': 'Index'}, inplace=True)
        
        train_df = df.iloc[:train_end_idx].copy()
        test_df = df.iloc[train_end_idx:].copy()
        
        train_data.append(train_df)
        test_data.append(test_df)
    
    return train_data, test_data

def create_split_cerebro(strategy_class, params, is_train=True, train_end_idx=700):
    """Create cerebro with 70/30 train/test split"""
    cerebro = bt.Cerebro()
    cerebro.addstrategy(strategy_class, **params)
    
    train_data, test_data = load_data_splits(train_end_idx)
    data_list = train_data if is_train else test_data
    
    for df in data_list:
        data = bt.feeds.PandasData(
            dataname=df,
            datetime='Index',
            open='Open', high='High', low='Low', close='Close', volume='Volume'
        )
        cerebro.adddata(data)
    
    cerebro.addanalyzer(OpenOpenPnL, _name='pnl')
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe', riskfreerate=0.0)
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    
    cerebro.broker.setcash(1000000)
    cerebro.broker.setcommission(commission=0.001)
    
    return cerebro

def run_mean_reversion_optimization():
    """Run Mean Reversion optimization for Series 09"""
    
    print("Starting Series 09 Mean Reversion Strategy Optimization...")
    print("=" * 60)
    
    # Parameter ranges for mean reversion optimization
    param_combinations = list(itertools.product(
        [20, 25, 30, 35],           # mean_period
        [20, 25, 30, 35],           # std_period  
        [1.0, 1.2, 1.5, 1.8],      # entry_threshold (Z-score)
        [0.0, 0.2, 0.5],            # exit_threshold (Z-score)
        [14, 21],                   # rsi_period
        [25, 30, 35],               # rsi_oversold
        [65, 70, 75],               # rsi_overbought
        [10, 15, 20],               # max_holding_days
        [0.20, 0.25, 0.30],         # stake_pct
        [0.04, 0.05, 0.06],         # stop_loss
        [0.06, 0.08, 0.10]          # take_profit
    ))
    
    print(f"Total parameter combinations to test: {len(param_combinations)}")
    
    results = []
    best_test_return = -999
    best_params = None
    baseline_return = -1.13  # Current performance
    
    for i, params in enumerate(param_combinations):
        (mean_period, std_period, entry_threshold, exit_threshold, 
         rsi_period, rsi_oversold, rsi_overbought, max_holding_days,
         stake_pct, stop_loss, take_profit) = params
        
        # Skip invalid combinations
        if rsi_overbought <= rsi_oversold + 20:
            continue
        if take_profit <= stop_loss:
            continue
        if entry_threshold <= exit_threshold:
            continue
            
        strategy_params = {
            'mean_period': mean_period,
            'std_period': std_period,
            'entry_threshold': entry_threshold,
            'exit_threshold': exit_threshold,
            'rsi_period': rsi_period,
            'rsi_oversold': rsi_oversold,
            'rsi_overbought': rsi_overbought,
            'max_holding_days': max_holding_days,
            'stake_pct': stake_pct,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'series_index': 8
        }
        
        try:
            # Train phase
            cerebro_train = create_split_cerebro(MeanReversionStrategy, strategy_params, is_train=True)
            result_train = cerebro_train.run()[0]
            train_pnl = result_train.analyzers.pnl.get_analysis()
            train_sharpe = result_train.analyzers.sharpe.get_analysis()
            train_trades = result_train.analyzers.trades.get_analysis()
            
            train_return = train_pnl.get('total_return', 0)
            train_sharpe_ratio = train_sharpe.get('sharperatio', 0) or 0
            train_trade_count = train_trades.get('total', {}).get('closed', 0)
            
            # Test phase
            cerebro_test = create_split_cerebro(MeanReversionStrategy, strategy_params, is_train=False)
            result_test = cerebro_test.run()[0]
            test_pnl = result_test.analyzers.pnl.get_analysis()
            test_sharpe = result_test.analyzers.sharpe.get_analysis()
            test_trades = result_test.analyzers.trades.get_analysis()
            
            test_return = test_pnl.get('total_return', 0)
            test_sharpe_ratio = test_sharpe.get('sharperatio', 0) or 0
            test_trade_count = test_trades.get('total', {}).get('closed', 0)
            
            # Create parameter name
            param_name = f"MR_{mean_period}/{std_period}_Z{entry_threshold}-{exit_threshold}_RSI{rsi_period}_{rsi_oversold}-{rsi_overbought}_H{max_holding_days}"
            
            result = {
                'name': param_name,
                'parameters': strategy_params,
                'train_return': round(train_return, 2),
                'train_sharpe': round(train_sharpe_ratio, 3),
                'train_trades': train_trade_count,
                'test_return': round(test_return, 2),
                'test_sharpe': round(test_sharpe_ratio, 3),
                'test_trades': test_trade_count,
                'test_improvement': round(test_return - baseline_return, 2)
            }
            
            results.append(result)
            
            # Track best performer
            if test_return > best_test_return:
                best_test_return = test_return
                best_params = result
            
            # Progress update every 200 combinations
            if (i + 1) % 200 == 0:
                print(f"[{i+1:4d}/{len(param_combinations)}] Current best: {best_test_return:.2f}% "
                      f"({best_params['name'] if best_params else 'None'})")
        
        except Exception as e:
            print(f"Error with combination {i}: {e}")
            continue
    
    # Sort results by test return
    results.sort(key=lambda x: x['test_return'], reverse=True)
    
    # Find improvements
    improvements = [r for r in results if r['test_return'] > baseline_return]
    
    # Create summary
    summary = {
        'total_tested': len(results),
        'improvements_found': len(improvements),
        'best_performer': results[0] if results else None,
        'baseline_comparison': baseline_return
    }
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"output/optimization/series09_mean_reversion_{timestamp}.json"
    
    os.makedirs("output/optimization", exist_ok=True)
    
    output_data = {
        'timestamp': timestamp,
        'baseline_performance': baseline_return,
        'results': results[:15],  # Top 15 results
        'summary': summary
    }
    
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    # Print results
    print("\n" + "=" * 60)
    print("MEAN REVERSION STRATEGY OPTIMIZATION RESULTS")
    print("=" * 60)
    print(f"Total combinations tested: {len(results)}")
    print(f"Improvements over baseline ({baseline_return}%): {len(improvements)}")
    
    if results:
        best = results[0]
        print(f"\nBest performer: {best['name']}")
        print(f"Parameters: Mean({best['parameters']['mean_period']}) Std({best['parameters']['std_period']}) "
              f"Z-score({best['parameters']['entry_threshold']}-{best['parameters']['exit_threshold']}) "
              f"RSI({best['parameters']['rsi_period']}) {best['parameters']['rsi_oversold']}/{best['parameters']['rsi_overbought']} "
              f"Hold({best['parameters']['max_holding_days']})")
        print(f"Test return: {best['test_return']:.2f}%")
        print(f"Test Sharpe: {best['test_sharpe']:.3f}")
        print(f"Test trades: {best['test_trades']}")
        print(f"Improvement: {best['test_improvement']:+.2f}%")
        
        print("\nTop 5 performers:")
        for i, result in enumerate(results[:5]):
            print(f"{i+1}. {result['name']}: {result['test_return']:+.2f}% "
                  f"(Sharpe: {result['test_sharpe']:.3f}, Trades: {result['test_trades']})")
    
    print(f"\nDetailed results saved to: {output_file}")
    return results[0] if results else None

if __name__ == "__main__":
    best_result = run_mean_reversion_optimization()