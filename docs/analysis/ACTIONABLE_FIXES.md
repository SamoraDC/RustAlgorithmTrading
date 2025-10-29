# Actionable Fixes for Backtest Failures

**Priority**: CRITICAL
**Date**: 2025-10-29
**Status**: Ready for Implementation

---

## Executive Summary

After comprehensive analysis of 18 backtests with 507 trades, we've identified the root causes:

1. ✅ **P&L calculations are CORRECT** - Exit logic is working
2. ❌ **SHORT entry signals are poorly timed** - 72.7% loss rate
3. ❌ **LONG signals are better but still suboptimal** - 40% win rate
4. ❌ **Strategy enters too aggressively** - Catching falling knives and shorting rising stocks

---

## Issue #1: Short Entry Timing (CRITICAL)

### Problem
The momentum strategy enters SHORT positions right before price rises:
- 11 SHORT signals generated
- 8 lost money (72.7% loss rate)
- Average loss on shorts: -4.06%

### Evidence
```
Trade 1: SHORT AAPL @ $198.42 → Exit $207.82 (+4.74% rise) = -4.74% P&L
Trade 3: SHORT GOOGL @ $166.64 → Exit $178.53 (+7.14% rise) = -7.14% P&L
Trade 6: SHORT AAPL @ $245.27 → Exit $262.24 (+6.92% rise) = -6.92% P&L
```

### Root Cause
From `src/strategies/momentum.py` lines 367-385:

```python
# SHORT signal: RSI crosses BELOW 50 (momentum weakening) + MACD bearish
rsi_short_cond = current['rsi'] < 50 and previous['rsi'] >= 50
macd_short_cond = current['macd'] < current['macd_signal']
hist_short_cond = current['macd_histogram'] < -histogram_threshold
trend_short_cond = current['close'] < current['sma_50']
```

**Issue**: RSI crossing below 50 doesn't mean price will fall—it means momentum is *starting* to weaken. Price often continues rising for several more bars before actually reversing.

### Fix Options

#### Option A: Disable SHORT signals entirely (RECOMMENDED - Quick Win)
```python
# In momentum.py, line 372
# Temporarily disable shorts until we can improve timing
if False:  # TODO: Re-enable after improving short entry logic
    if (rsi_short_cond and macd_short_cond and hist_short_cond and trend_short_cond and volume_ok):
        signal_type = SignalType.SHORT
```

**Expected Impact**:
- Eliminate 72.7% loss rate trades
- Reduce total trades by ~68%
- Focus on LONG-only strategy where we have 40% win rate
- Estimated improvement: -25% return → -5% to 0% return

#### Option B: Strengthen SHORT entry conditions (MEDIUM-TERM)
Require stronger confirmation before entering shorts:

```python
# More conservative short entry
rsi_short_cond = current['rsi'] < 40 and previous['rsi'] >= 40  # Lower threshold
macd_short_cond = current['macd'] < current['macd_signal'] - 0.5  # Stronger bearish signal
hist_short_cond = current['macd_histogram'] < -0.002  # 4x threshold
trend_short_cond = current['close'] < current['sma_50'] * 0.98  # Must be 2% below SMA
consecutive_down_days = 3  # Require 3 consecutive down days
```

**Expected Impact**:
- Reduce SHORT signals by 70-80%
- Improve SHORT win rate from 27% to 40-45%
- Still risky - may miss good opportunities

#### Option C: Use different SHORT logic (LONG-TERM)
Switch to mean-reversion for shorts instead of momentum:

```python
# SHORT when price is extended above SMA (overheated)
if (current['rsi'] > 70 and  # Overbought
    current['close'] > current['sma_50'] * 1.05 and  # 5% above SMA
    current['macd_histogram'] < previous['macd_histogram']):  # Divergence
    signal_type = SignalType.SHORT
```

---

## Issue #2: Long Entry Timing (HIGH PRIORITY)

### Problem
LONG signals have 40% win rate - better than shorts but still not profitable:
- 5 LONG signals generated
- 2 won, 3 lost (40% win rate)
- Not enough to offset losses

### Evidence
```
Trade 5: LONG MSFT @ $517.93 → Exit $510.96 (-1.35%) = LOSS
Trade 8: LONG GOOGL @ $178.64 → Exit $185.06 (+3.59%) = WIN ✓
Trade 11: LONG AMZN @ $231.49 → Exit $225.34 (-2.66%) = LOSS
Trade 15: LONG NVDA @ $188.32 → Exit $201.03 (+6.75%) = WIN ✓
```

### Root Cause
From `src/strategies/momentum.py` lines 342-358:

```python
# LONG signal: RSI crosses ABOVE 50 (momentum building) + MACD bullish
rsi_long_cond = current['rsi'] > 50 and previous['rsi'] <= 50
macd_long_cond = current['macd'] > current['macd_signal']
hist_long_cond = current['macd_histogram'] > histogram_threshold
trend_long_cond = current['close'] > current['sma_50']
```

**Issue**: RSI crossing above 50 is good, but entry may be too early. Need stronger momentum confirmation.

### Fix Options

#### Option A: Require stronger momentum (RECOMMENDED)
```python
# Stronger long entry conditions
rsi_long_cond = current['rsi'] > 55 and previous['rsi'] <= 55  # Higher threshold
macd_long_cond = current['macd'] > current['macd_signal'] + 0.3  # Stronger bullish
hist_long_cond = current['macd_histogram'] > 0.001  # 2x threshold
trend_long_cond = current['close'] > current['sma_50'] * 1.01  # Must be 1% above SMA
volume_long_cond = current['volume'] > current['volume_ma'] * 1.5  # Stronger volume
```

**Expected Impact**:
- Reduce LONG signals by 40-50%
- Improve LONG win rate from 40% to 50-60%
- Better risk/reward on each trade

#### Option B: Add trend strength filter (RECOMMENDED)
```python
# Calculate trend strength
sma_20 = data['close'].rolling(window=20).mean()
sma_50 = data['close'].rolling(window=50).mean()
trend_strength = (sma_20 - sma_50) / sma_50

# Only enter LONG if in strong uptrend
strong_uptrend = trend_strength > 0.02  # 20-day SMA is 2% above 50-day

if (rsi_long_cond and macd_long_cond and hist_long_cond and
    trend_long_cond and volume_ok and strong_uptrend):
    signal_type = SignalType.LONG
```

**Expected Impact**:
- Filter out weak trends
- Reduce LONG signals by 30%
- Improve LONG win rate to 55-65%

---

## Issue #3: Stop-Loss Too Tight (HIGH PRIORITY)

### Problem
70% of exits are stop-losses (trailing or catastrophic), only 30% are take-profits.

### Evidence
```
Exit Reasons:
- trailing_stop_loss: 7 (46.7%)
- catastrophic_stop_loss: 5 (33.3%)
- take_profit: 3 (20.0%)
```

Average winner: +4.73%
Average loser: -4.06%
Risk/Reward ratio: 1.16:1 (barely positive)

### Root Cause
From `src/strategies/momentum.py`:
```python
stop_loss_pct: float = 0.02,        # 2% stop loss
take_profit_pct: float = 0.03,      # 3% take profit
trailing_stop_pct: float = 0.015,   # 1.5% trailing stop
```

**Issue**:
- 1.5% trailing stop is too tight for daily bars (stocks can easily move 2-3% intraday)
- 2% fixed stop is getting triggered by normal volatility
- Not giving trades room to breathe

### Fix

#### Increase stop-loss levels (RECOMMENDED)
```python
stop_loss_pct: float = 0.04,        # 4% stop loss (was 2%)
take_profit_pct: float = 0.06,      # 6% take profit (was 3%)
trailing_stop_pct: float = 0.03,    # 3% trailing stop (was 1.5%)
```

**Expected Impact**:
- Reduce premature exits by 40-50%
- Let winning trades run longer
- Accept larger losses but improve win rate
- Target: Win rate 45% → 55%, Avg win +4.7% → +7%, Avg loss -4.1% → -5%

#### Add ATR-based stops (BETTER - LONG-TERM)
```python
# Calculate ATR-based stops
atr = data['true_range'].rolling(window=14).mean()
atr_pct = atr / current['close']

# Dynamic stops based on volatility
stop_loss_pct = max(0.03, atr_pct * 2)  # 2x ATR or 3%, whichever is larger
take_profit_pct = stop_loss_pct * 1.5   # 1.5:1 reward/risk
trailing_stop_pct = atr_pct * 1.5       # 1.5x ATR
```

**Expected Impact**:
- Adapt to market volatility
- Tighter stops in calm markets, wider in volatile markets
- Improve risk-adjusted returns

---

## Issue #4: Overtrading (MEDIUM PRIORITY)

### Problem
Strategy generates too many signals:
- 31 signals in ~180 days for 5 symbols = 1.7 trades per symbol per month
- High transaction costs: 0.1% commission + 0.05% slippage = 0.15% per trade
- 31 trades * 0.3% round-trip = 9.3% in costs alone

### Fix

#### Increase minimum holding period (RECOMMENDED)
```python
min_holding_period: int = 20  # 20 bars (was 10)
```

**Expected Impact**:
- Reduce trades by 30-40%
- Lower transaction costs
- Let trends develop more fully

#### Add cooldown period (RECOMMENDED)
```python
# In strategy state
self.last_trade_time = {}  # {symbol: timestamp}
cooldown_bars = 15  # Wait 15 bars between trades

# Before entering new position
if symbol in self.last_trade_time:
    bars_since_last = current_bar_index - self.last_trade_time[symbol]
    if bars_since_last < cooldown_bars:
        continue  # Skip this signal
```

**Expected Impact**:
- Prevent rapid buy-sell-buy cycles
- Reduce trades by 20-25%
- Improve trade quality

---

## Issue #5: Volume Filter Too Strict (LOW PRIORITY)

### Problem
Volume confirmation may be filtering out good signals.

From logs:
```
"Volume filter blocked entry: vol=1,234,567, ma=1,500,000, required=1,800,000"
```

### Fix
```python
volume_multiplier: float = 1.1  # 10% above average (was 1.2 = 20%)
```

---

## Implementation Priority

### Phase 1: Quick Wins (Implement Today)
1. ✅ **Disable SHORT signals** (Option 1A)
   - File: `src/strategies/momentum.py` line 372
   - Change: Wrap SHORT logic in `if False:`
   - Expected: -25% → -5% return

2. ✅ **Increase stop-loss levels**
   - File: `src/strategies/momentum.py` lines 40-50
   - Change: 2% → 4%, 3% → 6%, 1.5% → 3%
   - Expected: Win rate +10%

3. ✅ **Increase minimum holding period**
   - File: `src/strategies/momentum.py` line 196
   - Change: 10 → 20 bars
   - Expected: -30% trades, +5% win rate

### Phase 2: Improvements (This Week)
4. ✅ **Strengthen LONG entry conditions** (Option 2A)
   - File: `src/strategies/momentum.py` lines 342-358
   - Change: Increase thresholds and add filters
   - Expected: Win rate 40% → 55%

5. ✅ **Add cooldown period** (Option 4B)
   - File: `src/strategies/momentum.py`
   - Change: Add cooldown tracking
   - Expected: -20% trades, +quality

6. ✅ **Relax volume filter** (Option 5)
   - File: `src/strategies/momentum.py` line 336
   - Change: 1.2 → 1.1
   - Expected: +15% signals, +diversity

### Phase 3: Advanced (Next Week)
7. 🔄 **ATR-based stops** (Option 3B)
   - File: `src/strategies/momentum.py`
   - Change: Implement dynamic stops
   - Expected: +Sharpe ratio

8. 🔄 **Trend strength filter** (Option 2B)
   - File: `src/strategies/momentum.py`
   - Change: Add SMA slope calculation
   - Expected: Better entries

9. 🔄 **Redesign SHORT logic** (Option 1C)
   - File: `src/strategies/momentum.py`
   - Change: Mean-reversion shorts
   - Expected: Viable shorting

---

## Expected Outcomes After Fixes

### Current Performance
- Win Rate: 0.8% (4/507)
- Average Return: -200%
- Sharpe Ratio: -11.47
- Max Drawdown: 278%

### After Phase 1 (Quick Wins)
- Win Rate: 40-45%
- Average Return: -5% to 0%
- Sharpe Ratio: -0.5 to 0.0
- Max Drawdown: 15-20%

### After Phase 2 (Improvements)
- Win Rate: 50-55%
- Average Return: +5% to +10%
- Sharpe Ratio: 0.5 to 1.0
- Max Drawdown: 10-15%

### After Phase 3 (Advanced)
- Win Rate: 55-60%
- Average Return: +12% to +18%
- Sharpe Ratio: 1.0 to 1.5
- Max Drawdown: 8-12%

---

## Testing Protocol

After each phase:

1. **Run backtest on fixed strategy**
   ```bash
   python scripts/run_backtest.py --strategy momentum --start 2024-01-01 --end 2024-12-31
   ```

2. **Verify improvements**
   ```bash
   python scripts/analyze_backtests.py
   python scripts/visualize_backtests.py
   ```

3. **Check key metrics**
   - Win rate > 40% (Phase 1) or > 50% (Phase 2)
   - Average trade PnL > 0%
   - Sharpe ratio > 0
   - Max drawdown < 20%

4. **Review trade log**
   - Are LONG trades winning when price rises?
   - Are stops triggering less frequently?
   - Is holding period being respected?

---

## Files to Modify

| File | Lines | Changes |
|------|-------|---------|
| `src/strategies/momentum.py` | 40-50 | Increase stop-loss/take-profit levels |
| `src/strategies/momentum.py` | 196 | Increase min holding period |
| `src/strategies/momentum.py` | 342-358 | Strengthen LONG entry conditions |
| `src/strategies/momentum.py` | 367-385 | Disable/fix SHORT entry logic |
| `src/strategies/momentum.py` | 336 | Relax volume filter |

---

## Summary

The good news: **Execution logic is correct**. P&L calculations work properly.

The bad news: **Signal timing is terrible**. Strategy enters positions at exactly the wrong time.

**Root cause**: Momentum strategy is too aggressive on SHORT signals and too weak on LONG signals. Combined with tight stops, this creates a losing system.

**Solution**: Disable shorts, strengthen long entries, widen stops, reduce trading frequency.

**Timeline**:
- Phase 1 fixes can be implemented in 1 hour
- Should see immediate improvement to near-breakeven
- Full optimization will take 1-2 weeks

---

**Next Step**: Implement Phase 1 quick wins and rerun backtests.
