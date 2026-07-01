#!/usr/bin/env python3
"""
Data splitter utility for train/test split validation.

Provides functions to load data with date range constraints for
walk-forward testing and out-of-sample validation.
"""

import backtrader as bt
from pathlib import Path
import pandas as pd


class TrainTestDataFeed(bt.feeds.PandasData):
    """
    Custom data feed that can load a subset of data based on row indices.

    This allows us to split the same CSV file into training and testing periods
    without creating duplicate files.
    """
    params = (
        ('fromdate', None),
        ('todate', None),
        ('start_row', None),  # Start from this row index (0-based)
        ('end_row', None),    # End at this row index (exclusive)
    )


def get_data_row_count(filepath):
    """
    Get the total number of data rows in a CSV file (excluding header).

    Args:
        filepath: Path to CSV file

    Returns:
        int: Number of data rows
    """
    df = pd.read_csv(filepath, index_col=0)
    return len(df)


def load_train_test_data(cerebro, data_dir='DATA/PART1', series_list=None,
                         train_split=0.7, cash_per_series=None):
    """
    Load training or testing data for specified series.

    Args:
        cerebro: Backtrader Cerebro instance
        data_dir: Directory containing CSV files
        series_list: List of series numbers to load (e.g., [4, 5, 9])
        train_split: Fraction of data to use for training (default 0.7 for 70%)
        cash_per_series: Starting cash per series (for display only)

    Returns:
        tuple: (train_cerebro, test_cerebro, split_info)
            - train_cerebro: Cerebro instance with training data loaded
            - test_cerebro: Cerebro instance with testing data loaded
            - split_info: Dictionary with split information
    """
    if series_list is None:
        series_list = [4, 5, 9]  # Default to Series 04, 05, 09

    data_path = Path(data_dir)
    split_info = {
        'series_list': series_list,
        'train_split': train_split,
        'train_bars': {},
        'test_bars': {},
        'total_bars': {},
    }

    # Create two separate Cerebro instances
    train_cerebro = bt.Cerebro()
    test_cerebro = bt.Cerebro()

    print("=" * 80)
    print("DATA SPLIT CONFIGURATION")
    print("=" * 80)

    for series_num in series_list:
        filename = f"{series_num:02d}.csv"
        filepath = data_path / filename

        if not filepath.exists():
            print(f"✗ Warning: {filename} not found, skipping...")
            continue

        # Read the full dataset to determine split point
        df = pd.read_csv(filepath, index_col=0, parse_dates=True)
        total_rows = len(df)
        train_rows = int(total_rows * train_split)
        test_rows = total_rows - train_rows

        split_info['total_bars'][series_num] = total_rows
        split_info['train_bars'][series_num] = train_rows
        split_info['test_bars'][series_num] = test_rows

        # Get date ranges
        train_start = df.index[0]
        train_end = df.index[train_rows - 1]
        test_start = df.index[train_rows]
        test_end = df.index[-1]

        # Create training data feed
        train_df = df.iloc[:train_rows].copy()
        train_data = bt.feeds.PandasData(
            dataname=train_df,
            name=f'Series_{series_num:02d}'
        )
        train_cerebro.adddata(train_data)

        # Create testing data feed
        test_df = df.iloc[train_rows:].copy()
        test_data = bt.feeds.PandasData(
            dataname=test_df,
            name=f'Series_{series_num:02d}'
        )
        test_cerebro.adddata(test_data)

        print(f"\n📊 Series {series_num:02d} ({filename}):")
        print(f"   Total bars: {total_rows}")
        print(f"   Training:   {train_rows} bars ({train_split*100:.0f}%) "
              f"[{train_start.date()} to {train_end.date()}]")
        print(f"   Testing:    {test_rows} bars ({(1-train_split)*100:.0f}%) "
              f"[{test_start.date()} to {test_end.date()}]")

    print("\n" + "=" * 80)
    print(f"✓ Loaded {len(series_list)} series into train and test sets")
    print(f"  Train split: {train_split*100:.0f}% | Test split: {(1-train_split)*100:.0f}%")
    print("=" * 80 + "\n")

    return train_cerebro, test_cerebro, split_info


def create_split_cerebro(data_dir='DATA/PART1', series_list=None,
                         mode='train', train_split=0.7):
    """
    Create a single Cerebro instance with either training or testing data.

    Args:
        data_dir: Directory containing CSV files
        series_list: List of series numbers to load
        mode: 'train' or 'test'
        train_split: Fraction of data for training

    Returns:
        Cerebro instance with appropriate data loaded
    """
    if series_list is None:
        series_list = [4, 5, 9]

    data_path = Path(data_dir)
    cerebro = bt.Cerebro()

    print(f"\nLoading {mode.upper()} data...")

    for series_num in series_list:
        filename = f"{series_num:02d}.csv"
        filepath = data_path / filename

        if not filepath.exists():
            continue

        df = pd.read_csv(filepath, index_col=0, parse_dates=True)
        total_rows = len(df)
        train_rows = int(total_rows * train_split)

        if mode == 'train':
            subset_df = df.iloc[:train_rows].copy()
            date_range = f"{subset_df.index[0].date()} to {subset_df.index[-1].date()}"
        else:  # test
            subset_df = df.iloc[train_rows:].copy()
            date_range = f"{subset_df.index[0].date()} to {subset_df.index[-1].date()}"

        data = bt.feeds.PandasData(
            dataname=subset_df,
            name=f'Series_{series_num:02d}'
        )
        cerebro.adddata(data)

        print(f"  ✓ Series {series_num:02d}: {len(subset_df)} bars [{date_range}]")

    return cerebro


def get_split_dates(data_dir='DATA/PART1', series_num=4, train_split=0.7):
    """
    Get the date boundaries for train/test split for a specific series.

    Args:
        data_dir: Directory containing CSV files
        series_num: Series number (e.g., 4 for Series 04)
        train_split: Training fraction

    Returns:
        dict: {'train_start', 'train_end', 'test_start', 'test_end'}
    """
    filepath = Path(data_dir) / f"{series_num:02d}.csv"
    df = pd.read_csv(filepath, index_col=0, parse_dates=True)

    total_rows = len(df)
    train_rows = int(total_rows * train_split)

    return {
        'train_start': df.index[0],
        'train_end': df.index[train_rows - 1],
        'test_start': df.index[train_rows],
        'test_end': df.index[-1],
        'train_rows': train_rows,
        'test_rows': total_rows - train_rows,
        'total_rows': total_rows,
    }


if __name__ == '__main__':
    """
    Test the data splitter utility.
    """
    print("\n" + "="*80)
    print("DATA SPLITTER UTILITY TEST")
    print("="*80)

    # Test with Series 04, 05, 09
    series_list = [4, 5, 9]

    # Show split information for each series
    print("\nDetailed split information:")
    for series_num in series_list:
        info = get_split_dates(series_num=series_num, train_split=0.7)
        print(f"\n📊 Series {series_num:02d}:")
        print(f"   Total: {info['total_rows']} bars")
        print(f"   Train: {info['train_rows']} bars "
              f"({info['train_start'].date()} to {info['train_end'].date()})")
        print(f"   Test:  {info['test_rows']} bars "
              f"({info['test_start'].date()} to {info['test_end'].date()})")

    # Test loading into Cerebro
    print("\n" + "="*80)
    print("Testing Cerebro data loading...")
    print("="*80)

    train_cerebro, test_cerebro, split_info = load_train_test_data(
        cerebro=bt.Cerebro(),
        series_list=series_list,
        train_split=0.7
    )

    print("\n✓ Data splitter utility test complete!")
