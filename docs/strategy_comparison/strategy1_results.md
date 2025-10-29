# Strategy 1: Simple Momentum (EMA Crossover) - Backtest Results

## Executive Summary

**Test Date:** 2025-10-29
**Strategy:** SimpleMomentumStrategy (EMA Crossover with RSI)
**Test Period:** 2024-10-30 to 2025-10-22 (245 trading days)
**Symbols:** AAPL, MSFT, GOOGL
**Initial Capital:** $1,000.00

## Key Performance Metrics

| Metric | Value | Status |
|--------|-------|--------|
| **Total Return** | -0.40% | ❌ FAILED |
| **Final Value** | $995.95 | ❌ LOSS |
| **Win Rate** | 0.00% | ❌ FAILED |
| **Sharpe Ratio** | -13.58 | ❌ FAILED |
| **Max Drawdown** | 0.40% | ✅ PASS |
| **Total Trades** | 5 | ⚠️ LOW |

## Profitability Assessment

**STRATEGY IS NOT PROFITABLE** ❌

### Key Issues:
1. **0% Win Rate** - All 5 trades resulted in losses
2. **Negative Returns** - Lost $4.05 (-0.40%)
3. **Very Low Trade Count** - Only 5 trades over 245 days (2% of days)
4. **Extremely Negative Sharpe Ratio** - Indicates poor risk-adjusted returns

## Detailed Metrics

### Return Metrics
- **Total Return:** -0.40%
- **Initial Capital:** $1,000.00
- **Final Value:** $995.95
- **Profit/Loss:** -$4.05

### Risk Metrics
- **Sharpe Ratio:** -13.58 (Target: >1.0) ❌
- **Sortino Ratio:** -3.88
- **Max Drawdown:** 0.40% ✅
- **Max Drawdown Duration:** 190 days
- **Volatility:** 17.79%
- **Calmar Ratio:** 1.00

### Trade Statistics
- **Total Trades:** 5
- **Winning Trades:** 0 (0%)
- **Losing Trades:** 5 (100%)
- **Average Win:** $0.00
- **Average Loss:** -$0.55
- **Largest Win:** $0.00
- **Largest Loss:** -$0.88
- **Profit Factor:** 0.00 (Target: >1.5) ❌

## Strategy Configuration

### Parameters Used:
```python
SimpleMomentumStrategy(
    symbols=['AAPL', 'MSFT', 'GOOGL'],
    rsi_period=14,
    rsi_oversold=30,
    rsi_overbought=70,
    ema_fast=12,
    ema_slow=26,
    macd_signal=9,
    position_size=0.10  # 10% per position
)
```

### Key Features:
- EMA Crossover (12/26 periods)
- RSI confirmation (14-period, 30/70 thresholds)
- MACD signal line crossovers
- Volume confirmation filter (1.2x 20-period MA)
- 2% stop loss
- 3% take profit target

## Root Cause Analysis

### Volume Filter Too Restrictive

The backtest logs show consistent **"Volume filter blocked entry"** messages throughout the entire test period. This indicates that the volume confirmation requirement (volume must be >1.2x the 20-period moving average) was preventing almost all trade entries.

**Example from logs:**
```
DEBUG - Volume filter blocked entry: vol=44649232.0, ma=43564132.35, required=52276958.82
DEBUG - Generated 0 signals for Momentum strategy (including 0 exits)
```

### Impact:
- **Expected trades:** ~56 signals based on RSI thresholds
- **Actual trades:** 5 (only 9% of expected)
- **91% of valid signals were blocked** by volume filter

## Comparison to Validation Thresholds

| Threshold | Target | Actual | Pass/Fail |
|-----------|--------|--------|-----------|
| Sharpe Ratio | ≥ 1.0 | -13.58 | ❌ FAIL |
| Win Rate | ≥ 50% | 0% | ❌ FAIL |
| Max Drawdown | ≤ 20% | 0.40% | ✅ PASS |
| Profit Factor | ≥ 1.5 | 0.0 | ❌ FAIL |

**Overall: FAILED (1/4 criteria met)**

## Recommendations

### Critical Issues to Address:

1. **Disable or Relax Volume Filter**
   - Current 1.2x multiplier is too restrictive
   - Consider reducing to 1.0x or disabling entirely
   - Alternative: Use volume as confirmation, not requirement

2. **Re-optimize RSI Thresholds**
   - Current 30/70 thresholds may not suit these symbols
   - Test with 35/65 or 40/60 ranges
   - Consider dynamic thresholds based on volatility

3. **Reduce Position Size**
   - Current 10% position size is appropriate
   - Keep this for risk management

4. **Add Trend Filter**
   - Only take signals in direction of longer-term trend
   - Use 50 or 200-period SMA as trend filter

### Suggested Parameter Changes:

```python
SimpleMomentumStrategy(
    symbols=['AAPL', 'MSFT', 'GOOGL'],
    rsi_period=14,
    rsi_oversold=35,  # More moderate threshold
    rsi_overbought=65,  # More moderate threshold
    ema_fast=12,
    ema_slow=26,
    macd_signal=9,
    position_size=0.10,
    volume_confirmation=False  # DISABLE volume filter
)
```

## Conclusions

**SimpleMomentumStrategy is NOT READY for paper trading.**

### Why It Failed:
1. Volume confirmation filter blocked 91% of potential trades
2. The 5 trades that executed all lost money (0% win rate)
3. Average loss of $0.55 per trade
4. Strategy is too conservative and misses profitable opportunities

### Next Steps:
1. ❌ **DO NOT** proceed to paper trading
2. ✅ **MUST** fix volume filter issue
3. ✅ **MUST** re-optimize parameters
4. ✅ **MUST** re-run backtest with adjusted settings
5. ✅ Consider testing alternative strategies (Strategy 2-5)

## Files Generated

- **Results JSON:** `/mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/data/backtest_results/strategy1_simple_momentum.json`
- **This Report:** `/mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/docs/strategy_comparison/strategy1_results.md`
- **Full Backtest Log:** `/tmp/backtest_strategy1.log`

## Technical Details

### Backtest Execution
- **Engine:** BacktestEngine (Python)
- **Data Handler:** HistoricalDataHandler (Parquet)
- **Execution:** SimulatedExecutionHandler
- **Commission:** 0.10%
- **Slippage:** 5.0 bps
- **Market Impact:** 2.0 bps/$1M

### Data Quality
- **Source:** Alpaca Markets API
- **Format:** Daily OHLCV bars
- **Bars per Symbol:** 245
- **Data Coverage:** 100% (no gaps)
- **Timezone:** UTC

---

**Report Generated:** 2025-10-29T13:12:00Z
**Test ID:** task-1761743134092-fekht1qng
**Agent:** Code Implementation Agent
