# Selected 4 Series Analysis Report

## Overview
Based on visual analysis of price evolution patterns, 4 series show distinctive and potentially profitable characteristics:
- **Series 04**: V-shaped recovery (decline then strong rally)
- **Series 05**: Sustained uptrend
- **Series 08**: M-shaped pattern (rally, decline, recovery)
- **Series 09**: M-shaped pattern (rally, decline, recovery)

---

## Comparative Statistics

### 1. Performance Metrics

| Metric | Series 04 | Series 05 | Series 08 | Series 09 |
|--------|-----------|-----------|-----------|-----------|
| **Mean Return (%)** | **0.0685** ⭐ | 0.0310 | 0.0057 | 0.0142 |
| **Sharpe Ratio** | **0.456** ⭐ | **0.973** ⭐⭐ | 0.231 | 0.377 |
| **Price Range** | 10.72 - 37.20 | 86.08 - 118.45 | 92.84 - 110.94 | 85.13 - 111.16 |
| **Total Range (%)** | **247%** ⭐⭐ | 37.6% | 19.5% | 30.5% |

**Key Insight**:
- Series 04 has the **highest mean return** and **largest price range**, indicating strong trending potential
- Series 05 has the **best Sharpe ratio**, indicating consistent returns with lower risk
- Series 08/09 have moderate returns but lower volatility

---

### 2. Volatility Characteristics

| Metric | Series 04 | Series 05 | Series 08 | Series 09 |
|--------|-----------|-----------|-----------|-----------|
| **Std Return (%)** | 2.386 | 0.505 | 0.390 | 0.597 |
| **Avg Volatility (%)** | **37.88** ⚠️ | 8.02 | 6.19 | 9.48 |
| **Vol of Vol** | **0.644** ⚠️ | 0.100 | 0.104 | 0.161 |
| **Risk Level** | **HIGH** | LOW | LOW | MEDIUM |

**Key Insight**:
- Series 04 is **highly volatile** (4-5x more than others) - requires careful position sizing
- Series 05, 08 have **low and stable volatility** - safer for consistent strategies
- Series 09 has **medium volatility** - balanced risk/reward

---

### 3. Mean Reversion Properties

| Metric | Series 04 | Series 05 | Series 08 | Series 09 |
|--------|-----------|-----------|-----------|-----------|
| **Hurst Exponent** | 0.126 | 0.156 | 0.137 | 0.123 |
| **Half Life (days)** | 360 | 425 | 123 | 112 |
| **ADF p-value** | 0.914 | 0.868 | 0.432 | 0.334 |
| **Mean Reverting?** | Yes (slow) | Yes (very slow) | Yes (fast) | Yes (fast) |

**Key Insight**:
- Series 04/05 have **long half-lives** (360-425 days) - slow mean reversion, better for trend-following
- Series 08/09 have **short half-lives** (112-123 days) - faster mean reversion, suitable for both strategies
- All series show mean-reverting tendencies (Hurst < 0.5)

---

### 4. Trend Following Potential

| Metric | Series 04 | Series 05 | Series 08 | Series 09 |
|--------|-----------|-----------|-----------|-----------|
| **ACF Lag 1** | 0.0283 | -0.0476 | 0.0390 | 0.0284 |
| **Momentum Score** | 0.0034 | -0.0009 | 0.0004 | 0.0001 |
| **Trend Potential** | ✅ True | ❌ False | ✅ True | ✅ True |
| **Pattern** | V-shaped | Steady rise | M-shaped | M-shaped |

**Key Insight**:
- Series 04 has **strongest momentum** despite V-shape - excellent for breakout strategies
- Series 05 lacks traditional trend signals but shows **consistent directional bias**
- Series 08/09 show **positive momentum** with cyclical patterns

---

## Strategy Recommendations

### 🎯 Series 04: High-Risk, High-Reward Breakout Strategy
**Pattern**: V-shaped recovery (decline then strong rally)

**Strengths**:
- Highest mean return (0.0685%)
- Largest price range (247%)
- Strong momentum potential
- Clear trend-following signals

**Risks**:
- Very high volatility (37.88%)
- Large drawdown potential during decline phase
- Requires precise entry timing

**Recommended Strategy**: **Momentum/Breakout with Strict Risk Management**
- Use technical breakout signals (moving average crossovers, support/resistance breaks)
- **Position size**: 10-15% of capital (due to high volatility)
- Stop-loss: 5-7% below entry
- Entry: After confirming trend reversal at bottom of V
- Exit: Trailing stop or momentum exhaustion signals

---

### 🎯 Series 05: Conservative Long-Only Strategy
**Pattern**: Sustained uptrend with low volatility

**Strengths**:
- Best Sharpe ratio (0.973)
- Lowest volatility (8.02%)
- Consistent positive returns
- Very low drawdown risk

**Risks**:
- Lower absolute returns
- Long mean reversion period (425 days)
- May underperform in range-bound markets

**Recommended Strategy**: **Buy-and-Hold with Momentum Enhancements**
- Simple long bias with occasional rebalancing
- **Position size**: 25-30% of capital (low risk)
- Entry: Dips below moving average (pullback buying)
- Exit: Only on clear trend reversal signals
- Consider this as "core holding" in portfolio

---

### 🎯 Series 08: Balanced Swing Trading Strategy
**Pattern**: M-shaped (rally, decline, recovery)

**Strengths**:
- Low volatility (6.19%)
- Fast mean reversion (123 days)
- Predictable cyclical pattern
- Positive momentum score

**Risks**:
- Lower returns than 04/05
- Requires active management to catch swings

**Recommended Strategy**: **Mean-Reversion Swing Trading**
- Buy at cycle lows, sell at cycle highs
- **Position size**: 20-25% of capital
- Use RSI/Bollinger Bands for entry/exit timing
- Entry: Oversold conditions + support levels
- Exit: Overbought conditions + resistance levels
- Hold time: 50-120 days per cycle

---

### 🎯 Series 09: Combined Strategy (Trend + Mean Reversion)
**Pattern**: M-shaped with stronger volatility

**Strengths**:
- Fast mean reversion (112 days)
- Positive momentum signals
- Medium volatility allows flexibility
- Similar pattern to Series 08 but higher amplitude

**Risks**:
- Higher volatility than Series 08
- Requires more sophisticated strategy

**Recommended Strategy**: **Adaptive Dual Strategy**
- Combine trend-following during strong moves with mean-reversion during consolidation
- **Position size**: 20-25% of capital
- Trend mode: Moving average crossover, momentum confirmation
- Mean-reversion mode: RSI extremes, Bollinger Band bounces
- Dynamic switching based on volatility regime

---

## Portfolio Allocation Recommendation

Based on £1,000,000 starting capital:

| Series | Strategy Type | Allocation | Rationale |
|--------|--------------|------------|-----------|
| **Series 05** | Core Long | £350,000 (35%) | Best Sharpe, lowest risk, steady returns |
| **Series 04** | Opportunistic Breakout | £200,000 (20%) | Highest return potential, but high risk |
| **Series 08** | Swing Trading | £225,000 (22.5%) | Predictable cycles, low risk |
| **Series 09** | Adaptive Trading | £225,000 (22.5%) | Similar to 08 with extra volatility upside |

**Total**: £1,000,000

**Risk Management**:
- Series 05 provides stability and prevents bankruptcy
- Series 04 provides upside potential but capped allocation due to volatility
- Series 08/09 provide consistent swing profits with manageable risk
- Diversification across 4 different pattern types reduces correlation risk

---

## Next Steps for Strategy Development

### Part 1: Individual Strategies (3 required)

**Strategy 1: Series 04 - Momentum Breakout**
- Type: Trend-following with breakout entry
- Entry: Price crosses above 20-day MA with volume confirmation
- Exit: Trailing stop or moving average crossunder
- Risk: 5% stop-loss per trade

**Strategy 2: Series 05 - Buy-and-Hold Plus**
- Type: Strategic long bias with pullback buying
- Entry: Price dips below 10-day MA but above 50-day MA
- Exit: Only on major trend break (price < 50-day MA for 5 days)
- Risk: Soft stop at -10%, hard bankruptcy protection

**Strategy 3: Series 08/09 Combined - Swing Oscillator**
- Type: Mean-reversion swing trading
- Entry: RSI < 30 AND price near Bollinger lower band
- Exit: RSI > 70 OR price near Bollinger upper band
- Risk: 3% stop-loss per swing

### Part 2: Combined Strategy
- Allocate capital as per table above
- Use correlation analysis to optimize entry/exit timing across all 4 series
- Implement portfolio-level stop-loss at -15% total drawdown
- Rebalance monthly if any position exceeds ±5% of target allocation

---

## Data Analysis Evidence Required (Per Assignment)

For each strategy, you'll need to demonstrate:

1. **Market Condition Proof** ✅
   - Already have: Price charts, volatility analysis, mean-reversion tests, trend tests
   - Need: Train/test split analysis showing conditions persist

2. **Technical Specifications** 📝
   - Define exact entry/exit rules
   - Parameter optimization (MA periods, RSI thresholds, etc.)
   - Slippage and commission assumptions

3. **Preliminary Testing** 🧪
   - Train period: First 70% of data
   - Test period: Last 30% of data
   - Out-of-sample results showing strategy validity

---

## Risk Warnings

⚠️ **Series 04**: High volatility requires strict position sizing - do NOT exceed 15% allocation
⚠️ **All Series**: Use the overspend_guard() before all market orders to prevent bankruptcy
⚠️ **Correlation**: Check correlation matrix - if Series 08/09 are highly correlated (>0.7), reduce combined allocation
⚠️ **Final Day**: Use `--end-policy liquidate` to ensure all positions close on last day

