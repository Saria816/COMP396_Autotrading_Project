# BT396 策略回测汇总报告

**生成时间**: 2025-11-06 16:56:07

---

## 策略性能对比表

| 策略名称 | 最终价值 | 总收益率 | 年化收益率 | 年化夏普比率 | 最大回撤 |
|---------|---------|---------|-----------|-------------|----------|
| 策略1: 双均线策略 (Series 04) | £1,178,811.78 | 17.88% | 14.87% | 2.069 | 2.58% |
| 策略2: 买入持有策略 (Series 05) | £1,143,133.90 | 14.31% | 11.93% | 1.335 | 5.82% |
| 策略3: 均值回归策略 (Series 09) | £1,002,965.39 | 0.30% | 0.25% | 0.433 | 0.36% |
| 组合策略: CVaR组合 | £1,129,321.25 | 12.93% | 3.12% | 1.061 | 3.86% |

---

## 详细结果路径

- **策略1: 双均线策略 (Series 04)**: `output/individual_strategies/s1_dual_ma/`
- **策略2: 买入持有策略 (Series 05)**: `output/individual_strategies/s2_buy_hold/`
- **策略3: 均值回归策略 (Series 09)**: `output/individual_strategies/s3_mean_reversion/`
- **组合策略: CVaR组合**: `output/combined_strategy/`

---

## 输出文件说明

每个策略目录包含以下文件：

- `run_summary.json` - 性能指标汇总
- `equity_curve.png` - 权益曲线图
- `per_series_pd.json` - 各资产PD比率
- `equity_dashboard.png` - 综合仪表板
- `series_*_cumPnL.png` - 各资产累计盈亏图
