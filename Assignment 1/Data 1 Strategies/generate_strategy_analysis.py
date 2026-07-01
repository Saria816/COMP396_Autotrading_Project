#!/usr/bin/env python3
"""
为报告生成策略数据分析图表和统计证据
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from scipy import stats
import json

# 配置matplotlib
plt.rcParams['figure.figsize'] = (12, 6)
plt.rcParams['font.size'] = 10
sns.set_style("whitegrid")

# 输出目录
OUTPUT_DIR = Path("output/report_analysis")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def load_series_data(series_num):
    """加载指定系列的数据"""
    file_path = Path(f"DATA/PART1/{series_num:02d}.csv")
    df = pd.read_csv(file_path, index_col=0, parse_dates=True)
    df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
    return df

def calculate_statistics(df, series_name):
    """计算基本统计数据"""
    returns = df['Close'].pct_change().dropna()

    stats_dict = {
        'Series': series_name,
        'Total Days': len(df),
        'Mean Return (%)': returns.mean() * 100,
        'Std Dev (%)': returns.std() * 100,
        'Sharpe Ratio': (returns.mean() / returns.std()) * np.sqrt(252) if returns.std() > 0 else 0,
        'Min Price': df['Close'].min(),
        'Max Price': df['Close'].max(),
        'Price Range (%)': ((df['Close'].max() - df['Close'].min()) / df['Close'].min()) * 100,
        'Skewness': returns.skew(),
        'Kurtosis': returns.kurtosis(),
    }

    return stats_dict

def analyze_series_04_trend():
    """分析Series 04的趋势特征 - 用于Strategy 1"""
    print("\n" + "="*60)
    print("  分析 Series 04 - 趋势跟踪特征")
    print("="*60)

    df = load_series_data(4)

    # 计算移动平均
    df['SMA_3'] = df['Close'].rolling(window=3).mean()
    df['SMA_24'] = df['Close'].rolling(window=24).mean()
    df['MA_Diff'] = df['SMA_3'] - df['SMA_24']

    # 计算趋势强度
    df['Trend_Signal'] = np.where(df['SMA_3'] > df['SMA_24'], 1, -1)
    df['Trend_Change'] = df['Trend_Signal'].diff().abs()

    # 统计信号
    crossover_count = (df['Trend_Change'] > 0).sum()
    uptrend_days = (df['Trend_Signal'] == 1).sum()
    downtrend_days = (df['Trend_Signal'] == -1).sum()

    # 1. 价格与双均线图
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))

    ax1.plot(df.index, df['Close'], label='Close Price', linewidth=1.5, alpha=0.8)
    ax1.plot(df.index, df['SMA_3'], label='3-Day SMA', linewidth=1.2, linestyle='--')
    ax1.plot(df.index, df['SMA_24'], label='24-Day SMA', linewidth=1.2, linestyle='--')
    ax1.fill_between(df.index, df['SMA_3'], df['SMA_24'],
                     where=(df['SMA_3'] > df['SMA_24']), alpha=0.2, color='green', label='Bullish')
    ax1.fill_between(df.index, df['SMA_3'], df['SMA_24'],
                     where=(df['SMA_3'] <= df['SMA_24']), alpha=0.2, color='red', label='Bearish')
    ax1.set_title('Series 04: Dual Moving Average Analysis (Trend-Following)', fontsize=14, fontweight='bold')
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Price')
    ax1.legend(loc='best')
    ax1.grid(True, alpha=0.3)

    # 2. MA差值图
    ax2.plot(df.index, df['MA_Diff'], label='MA Difference (3-day - 24-day)', color='purple', linewidth=1.2)
    ax2.axhline(y=0, color='black', linestyle='--', linewidth=1)
    ax2.fill_between(df.index, df['MA_Diff'], 0, where=(df['MA_Diff'] > 0), alpha=0.3, color='green')
    ax2.fill_between(df.index, df['MA_Diff'], 0, where=(df['MA_Diff'] <= 0), alpha=0.3, color='red')
    ax2.set_title('MA Crossover Signal Strength', fontsize=12, fontweight='bold')
    ax2.set_xlabel('Date')
    ax2.set_ylabel('Price Difference')
    ax2.legend(loc='best')
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 's1_series04_trend_analysis.png', dpi=150, bbox_inches='tight')
    print(f"✅ 已生成: {OUTPUT_DIR / 's1_series04_trend_analysis.png'}")
    plt.close()

    # 3. 趋势持续性分析
    fig, ax = plt.subplots(figsize=(12, 6))

    trend_duration = []
    current_trend = df['Trend_Signal'].iloc[0]
    current_duration = 0

    for signal in df['Trend_Signal']:
        if signal == current_trend:
            current_duration += 1
        else:
            if current_duration > 0:
                trend_duration.append(current_duration)
            current_trend = signal
            current_duration = 1

    if current_duration > 0:
        trend_duration.append(current_duration)

    ax.hist(trend_duration, bins=30, alpha=0.7, color='steelblue', edgecolor='black')
    ax.axvline(x=np.mean(trend_duration), color='red', linestyle='--', linewidth=2, label=f'Mean: {np.mean(trend_duration):.1f} days')
    ax.set_title('Series 04: Trend Duration Distribution', fontsize=14, fontweight='bold')
    ax.set_xlabel('Trend Duration (days)')
    ax.set_ylabel('Frequency')
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 's1_series04_trend_duration.png', dpi=150, bbox_inches='tight')
    print(f"✅ 已生成: {OUTPUT_DIR / 's1_series04_trend_duration.png'}")
    plt.close()

    # 统计数据
    stats = {
        'Total Crossovers': int(crossover_count),
        'Uptrend Days': int(uptrend_days),
        'Downtrend Days': int(downtrend_days),
        'Uptrend %': f"{(uptrend_days / len(df)) * 100:.2f}%",
        'Avg Trend Duration': f"{np.mean(trend_duration):.1f} days",
        'Max Trend Duration': f"{np.max(trend_duration)} days",
        'Trend Persistence': f"{(len(df) / crossover_count):.1f} days per signal"
    }

    # 保存统计数据
    with open(OUTPUT_DIR / 's1_series04_statistics.json', 'w') as f:
        json.dump(stats, f, indent=2)

    print("\n📊 Series 04 统计数据:")
    for key, value in stats.items():
        print(f"  {key}: {value}")

    return stats

def analyze_series_05_trend():
    """分析Series 05的上涨趋势 - 用于Strategy 2"""
    print("\n" + "="*60)
    print("  分析 Series 05 - 买入持有特征")
    print("="*60)

    df = load_series_data(5)

    # 计算累计回报
    df['Cumulative_Return'] = (1 + df['Close'].pct_change()).cumprod() - 1
    df['Returns'] = df['Close'].pct_change()

    # 计算回撤
    df['Cumulative_Max'] = df['Close'].cummax()
    df['Drawdown'] = (df['Close'] - df['Cumulative_Max']) / df['Cumulative_Max']

    # 计算趋势
    df['SMA_50'] = df['Close'].rolling(window=50).mean()
    df['Above_SMA'] = df['Close'] > df['SMA_50']

    # 1. 价格与累计回报图
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 12))

    # 价格图
    ax1.plot(df.index, df['Close'], label='Close Price', linewidth=1.5, color='darkblue')
    ax1.plot(df.index, df['SMA_50'], label='50-Day SMA', linewidth=1.2, linestyle='--', color='orange')
    ax1.fill_between(df.index, df['Close'], df['SMA_50'],
                     where=(df['Close'] > df['SMA_50']), alpha=0.2, color='green')
    ax1.set_title('Series 05: Price Evolution and Uptrend Confirmation', fontsize=14, fontweight='bold')
    ax1.set_ylabel('Price')
    ax1.legend(loc='best')
    ax1.grid(True, alpha=0.3)

    # 累计回报图
    ax2.plot(df.index, df['Cumulative_Return'] * 100, label='Cumulative Return', linewidth=1.5, color='green')
    ax2.axhline(y=0, color='black', linestyle='--', linewidth=1)
    ax2.fill_between(df.index, df['Cumulative_Return'] * 100, 0, alpha=0.3, color='green')
    ax2.set_title('Cumulative Return Over Time', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Return (%)')
    ax2.legend(loc='best')
    ax2.grid(True, alpha=0.3)

    # 回撤图
    ax3.fill_between(df.index, df['Drawdown'] * 100, 0, alpha=0.3, color='red')
    ax3.plot(df.index, df['Drawdown'] * 100, linewidth=1.2, color='darkred')
    ax3.set_title('Drawdown Analysis', fontsize=12, fontweight='bold')
    ax3.set_xlabel('Date')
    ax3.set_ylabel('Drawdown (%)')
    ax3.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 's2_series05_uptrend_analysis.png', dpi=150, bbox_inches='tight')
    print(f"✅ 已生成: {OUTPUT_DIR / 's2_series05_uptrend_analysis.png'}")
    plt.close()

    # 2. 收益分布图
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    returns_clean = df['Returns'].dropna()

    # 直方图
    ax1.hist(returns_clean * 100, bins=50, alpha=0.7, color='steelblue', edgecolor='black')
    ax1.axvline(x=returns_clean.mean() * 100, color='red', linestyle='--', linewidth=2,
                label=f'Mean: {returns_clean.mean() * 100:.3f}%')
    ax1.set_title('Daily Returns Distribution', fontsize=12, fontweight='bold')
    ax1.set_xlabel('Daily Return (%)')
    ax1.set_ylabel('Frequency')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # Q-Q plot
    stats.probplot(returns_clean, dist="norm", plot=ax2)
    ax2.set_title('Q-Q Plot (Normal Distribution)', fontsize=12, fontweight='bold')
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 's2_series05_returns_distribution.png', dpi=150, bbox_inches='tight')
    print(f"✅ 已生成: {OUTPUT_DIR / 's2_series05_returns_distribution.png'}")
    plt.close()

    # 统计数据
    total_return = (df['Close'].iloc[-1] / df['Close'].iloc[0] - 1) * 100
    positive_days = (df['Returns'] > 0).sum()
    negative_days = (df['Returns'] < 0).sum()
    days_above_sma = df['Above_SMA'].sum()
    max_drawdown = df['Drawdown'].min() * 100

    stats_dict = {
        'Total Return': f"{total_return:.2f}%",
        'Annualized Return': f"{((1 + total_return/100) ** (252/len(df)) - 1) * 100:.2f}%",
        'Positive Days': int(positive_days),
        'Negative Days': int(negative_days),
        'Win Rate': f"{(positive_days / (positive_days + negative_days)) * 100:.2f}%",
        'Days Above 50-SMA': int(days_above_sma),
        '% Time Above SMA': f"{(days_above_sma / len(df)) * 100:.2f}%",
        'Max Drawdown': f"{max_drawdown:.2f}%",
        'Avg Daily Return': f"{returns_clean.mean() * 100:.3f}%",
        'Daily Volatility': f"{returns_clean.std() * 100:.3f}%"
    }

    with open(OUTPUT_DIR / 's2_series05_statistics.json', 'w') as f:
        json.dump(stats_dict, f, indent=2)

    print("\n📊 Series 05 统计数据:")
    for key, value in stats_dict.items():
        print(f"  {key}: {value}")

    return stats_dict

def analyze_series_09_mean_reversion():
    """分析Series 09的均值回归特征 - 用于Strategy 3"""
    print("\n" + "="*60)
    print("分析 Series 09 - 均值回归特征")
    print("="*60)

    df = load_series_data(9)

    # 计算统计指标
    df['SMA_30'] = df['Close'].rolling(window=30).mean()
    df['STD_30'] = df['Close'].rolling(window=30).std()
    df['Z_Score'] = (df['Close'] - df['SMA_30']) / df['STD_30']

    # 计算RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

    # 1. 价格与均值回归图
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 12))

    # 价格与布林带
    ax1.plot(df.index, df['Close'], label='Close Price', linewidth=1.5, color='darkblue')
    ax1.plot(df.index, df['SMA_30'], label='30-Day SMA (Mean)', linewidth=1.2, linestyle='--', color='orange')
    ax1.fill_between(df.index, df['SMA_30'] - 2*df['STD_30'], df['SMA_30'] + 2*df['STD_30'],
                     alpha=0.2, color='gray', label='±2 Std Dev')
    ax1.fill_between(df.index, df['SMA_30'] - df['STD_30'], df['SMA_30'] + df['STD_30'],
                     alpha=0.3, color='lightblue', label='±1 Std Dev')
    ax1.set_title('Series 09: Mean Reversion Analysis with Bollinger Bands', fontsize=14, fontweight='bold')
    ax1.set_ylabel('Price')
    ax1.legend(loc='best')
    ax1.grid(True, alpha=0.3)

    # Z-Score图
    ax2.plot(df.index, df['Z_Score'], label='Z-Score', linewidth=1.2, color='purple')
    ax2.axhline(y=2, color='red', linestyle='--', linewidth=1, label='Overbought (+2σ)')
    ax2.axhline(y=-2, color='green', linestyle='--', linewidth=1, label='Oversold (-2σ)')
    ax2.axhline(y=0, color='black', linestyle='-', linewidth=1, alpha=0.5)
    ax2.fill_between(df.index, -2, 2, alpha=0.1, color='gray')
    ax2.set_title('Z-Score: Deviation from Mean', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Z-Score (σ)')
    ax2.legend(loc='best')
    ax2.grid(True, alpha=0.3)

    # RSI图
    ax3.plot(df.index, df['RSI'], label='RSI(14)', linewidth=1.2, color='darkgreen')
    ax3.axhline(y=70, color='red', linestyle='--', linewidth=1, label='Overbought (70)')
    ax3.axhline(y=30, color='green', linestyle='--', linewidth=1, label='Oversold (30)')
    ax3.fill_between(df.index, 30, 70, alpha=0.1, color='gray')
    ax3.set_title('RSI Indicator', fontsize=12, fontweight='bold')
    ax3.set_xlabel('Date')
    ax3.set_ylabel('RSI')
    ax3.legend(loc='best')
    ax3.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 's3_series09_mean_reversion_analysis.png', dpi=150, bbox_inches='tight')
    print(f"✅ 已生成: {OUTPUT_DIR / 's3_series09_mean_reversion_analysis.png'}")
    plt.close()

    # 2. Z-Score分布与回归证据
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    z_clean = df['Z_Score'].dropna()

    # Z-Score分布
    ax1.hist(z_clean, bins=50, alpha=0.7, color='steelblue', edgecolor='black', density=True)
    # 叠加正态分布
    mu, sigma = z_clean.mean(), z_clean.std()
    x = np.linspace(z_clean.min(), z_clean.max(), 100)
    ax1.plot(x, stats.norm.pdf(x, mu, sigma), 'r-', linewidth=2, label=f'Normal (μ={mu:.2f}, σ={sigma:.2f})')
    ax1.axvline(x=0, color='black', linestyle='--', linewidth=1)
    ax1.set_title('Z-Score Distribution', fontsize=12, fontweight='bold')
    ax1.set_xlabel('Z-Score')
    ax1.set_ylabel('Density')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # 均值回归验证：当前Z-Score vs 未来收益
    df['Future_Return'] = df['Close'].pct_change(5).shift(-5)  # 5天后的收益
    valid_data = df[['Z_Score', 'Future_Return']].dropna()

    ax2.scatter(valid_data['Z_Score'], valid_data['Future_Return'] * 100, alpha=0.3, s=10)
    z = np.polyfit(valid_data['Z_Score'], valid_data['Future_Return'] * 100, 1)
    p = np.poly1d(z)
    ax2.plot(valid_data['Z_Score'].sort_values(), p(valid_data['Z_Score'].sort_values()),
             "r-", linewidth=2, label=f'Regression: slope={z[0]:.3f}')
    ax2.axhline(y=0, color='black', linestyle='--', linewidth=1)
    ax2.axvline(x=0, color='black', linestyle='--', linewidth=1)
    ax2.set_title('Mean Reversion Evidence: Z-Score vs Future Return', fontsize=12, fontweight='bold')
    ax2.set_xlabel('Current Z-Score')
    ax2.set_ylabel('5-Day Future Return (%)')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 's3_series09_mean_reversion_evidence.png', dpi=150, bbox_inches='tight')
    print(f"✅ 已生成: {OUTPUT_DIR / 's3_series09_mean_reversion_evidence.png'}")
    plt.close()

    # 统计数据
    oversold_count = (df['Z_Score'] < -2).sum()
    overbought_count = (df['Z_Score'] > 2).sum()
    rsi_oversold = (df['RSI'] < 30).sum()
    rsi_overbought = (df['RSI'] > 70).sum()

    # 计算均值回归相关性
    correlation = valid_data[['Z_Score', 'Future_Return']].corr().iloc[0, 1]

    stats_dict = {
        'Mean Z-Score': f"{z_clean.mean():.3f}",
        'Z-Score Std Dev': f"{z_clean.std():.3f}",
        'Oversold Events (Z<-2)': int(oversold_count),
        'Overbought Events (Z>2)': int(overbought_count),
        'RSI Oversold (<30)': int(rsi_oversold),
        'RSI Overbought (>70)': int(rsi_overbought),
        'Mean Reversion Correlation': f"{correlation:.3f}",
        'Mean Reversion Slope': f"{z[0]:.4f}",
        'Time in Range (|Z|<1)': f"{((abs(z_clean) < 1).sum() / len(z_clean)) * 100:.2f}%"
    }

    with open(OUTPUT_DIR / 's3_series09_statistics.json', 'w') as f:
        json.dump(stats_dict, f, indent=2)

    print("\n📊 Series 09 统计数据:")
    for key, value in stats_dict.items():
        print(f"  {key}: {value}")

    return stats_dict

def create_summary_table():
    """创建三个系列的对比统计表"""
    print("\n" + "="*60)
    print("  生成三系列对比统计表")
    print("="*60)

    series_data = {}
    for series_num, name in [(4, 'Series 04'), (5, 'Series 05'), (9, 'Series 09')]:
        df = load_series_data(series_num)
        series_data[name] = calculate_statistics(df, name)

    # 创建表格
    df_stats = pd.DataFrame(series_data).T

    # 保存为CSV
    df_stats.to_csv(OUTPUT_DIR / 'series_comparison_table.csv')
    print(f"✅ 已生成: {OUTPUT_DIR / 'series_comparison_table.csv'}")

    # 可视化表格
    fig, ax = plt.subplots(figsize=(14, 4))
    ax.axis('tight')
    ax.axis('off')

    table_data = []
    for idx, row in df_stats.iterrows():
        table_data.append([
            idx,
            f"{row['Total Days']:.0f}",
            f"{row['Mean Return (%)']:.3f}%",
            f"{row['Std Dev (%)']:.3f}%",
            f"{row['Sharpe Ratio']:.3f}",
            f"{row['Price Range (%)']:.2f}%",
            f"{row['Skewness']:.3f}",
            f"{row['Kurtosis']:.3f}"
        ])

    headers = ['Series', 'Days', 'Mean Return', 'Volatility', 'Sharpe', 'Price Range', 'Skewness', 'Kurtosis']

    table = ax.table(cellText=table_data, colLabels=headers, cellLoc='center', loc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 2.5)

    # 设置表头样式
    for i in range(len(headers)):
        table[(0, i)].set_facecolor('#4472C4')
        table[(0, i)].set_text_props(weight='bold', color='white')

    # 设置数据行样式
    colors = ['#E7E6E6', '#F2F2F2', '#E7E6E6']
    for i in range(len(table_data)):
        for j in range(len(headers)):
            table[(i+1, j)].set_facecolor(colors[i])

    plt.title('Statistical Comparison of Selected Series', fontsize=14, fontweight='bold', pad=20)
    plt.savefig(OUTPUT_DIR / 'series_comparison_table.png', dpi=150, bbox_inches='tight')
    print(f"✅ 已生成: {OUTPUT_DIR / 'series_comparison_table.png'}")
    plt.close()

    return df_stats

if __name__ == "__main__":
    print("\n" + "="*60)
    print("BT396 策略数据分析报告生成器")
    print("="*60)

    # 分析各个系列
    s1_stats = analyze_series_04_trend()
    s2_stats = analyze_series_05_trend()
    s3_stats = analyze_series_09_mean_reversion()

    # 生成对比表
    comparison_df = create_summary_table()

    print("\n" + "="*60)
    print("  所有分析图表已生成完毕！")
    print("="*60)
    print(f"\n输出目录: {OUTPUT_DIR}/")
    print("\n生成的文件:")
    for file in sorted(OUTPUT_DIR.glob("*")):
        print(f"  ✅ {file.name}")

    print("\n" + "="*60)
