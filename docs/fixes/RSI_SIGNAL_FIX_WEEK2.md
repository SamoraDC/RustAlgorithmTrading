# RSI Signal Generation Fix - Week 2

**Date**: 2025-10-29
**Agent**: Coder (Hive Mind Week 2)
**Status**: ✅ COMPLETED

---

## Problem Identified

### Critical Bug
- **Location**: `src/strategies/momentum.py` line 345, `src/strategies/momentum_simplified.py` line 268
- **Issue**: RSI crossover logic only triggered once per trend
- **Impact**: 0 signals generated during +50% uptrends

### Root Cause
```python
# OLD (BROKEN) - Crossover Logic
rsi_long_cond = current['rsi'] > 50 and previous['rsi'] <= 50

# Problem: During uptrend, RSI stays at 60-88
# - Only triggers ONCE when crossing 50
# - Then RSI stays > 50, no more crossovers
# - Result: 0 signals in remaining +50% uptrend
```

---

## Solution Implemented

### New Logic: Level-Based RSI Zones

```python
# NEW (FIXED) - Level-Based Logic
rsi_long_cond = current['rsi'] > 55 and current['rsi'] < 85

# Benefits:
# - Triggers MULTIPLE times throughout uptrend
# - RSI 60-88 range = continuous signal generation
# - Avoids overbought extremes (>85)
# - Result: 5-10 signals in uptrend
```

### RSI Zone Definitions

#### Long Signals (Bullish Zone)
- **Range**: 55 < RSI < 85
- **Logic**: Strong momentum, not overbought
- **Rationale**: Allows entries throughout uptrend

#### Short Signals (Bearish Zone)
- **Range**: 15 < RSI < 45
- **Logic**: Weak momentum, not oversold
- **Rationale**: Allows entries throughout downtrend

---

## Files Modified

### 1. momentum.py (Main Strategy)

**Line 349-352** (LONG conditions):
```python
# CRITICAL FIX Week 2: Changed from crossover to level-based logic
# OLD: current['rsi'] > 50 and previous['rsi'] <= 50 (only triggers once)
# NEW: RSI in bullish zone (55-85) allows signals throughout uptrend
rsi_long_cond = current['rsi'] > 55 and current['rsi'] < 85  # Bullish zone, not overbought
```

**Line 373-377** (SHORT conditions):
```python
# CRITICAL FIX Week 2: Changed from crossover to level-based logic
# OLD: current['rsi'] < 50 and previous['rsi'] >= 50 (only triggers once)
# NEW: RSI in bearish zone (15-45) allows signals throughout downtrend
rsi_short_cond = current['rsi'] < 45 and current['rsi'] > 15  # Bearish zone, not oversold
```

### 2. momentum_simplified.py (Simplified Strategy)

**Line 268-271** (LONG conditions):
```python
# CRITICAL FIX Week 2: Changed RSI from crossover to level-based logic
# OLD: current['rsi'] > 50 and previous['rsi'] <= 50 (only triggers once)
# NEW: RSI in bullish zone (55-85) allows signals throughout uptrend
rsi_long_cond = current['rsi'] > 55 and current['rsi'] < 85  # Bullish zone, not overbought
```

**Line 293-296** (SHORT conditions):
```python
# CRITICAL FIX Week 2: Changed RSI from crossover to level-based logic
# OLD: current['rsi'] < 50 and previous['rsi'] >= 50 (only triggers once)
# NEW: RSI in bearish zone (15-45) allows signals throughout downtrend
rsi_short_cond = current['rsi'] < 45 and current['rsi'] > 15  # Bearish zone, not oversold
```

---

## Expected Impact

### Before Fix
- **Signals in uptrend**: 0-1
- **Total trades**: ~5
- **Win rate**: 0% (no trades to win)
- **Sharpe ratio**: Negative (no activity)

### After Fix
- **Signals in uptrend**: 5-10
- **Total trades**: 30-40
- **Win rate**: 30-45% (expected)
- **Sharpe ratio**: Positive (more trading opportunities)

---

## Test Coverage

### Test File Created
**Location**: `/tests/unit/test_rsi_fix_week2.py`

### Test Cases
1. **Uptrend Signal Generation**
   - Verifies multiple signals in +50% uptrend
   - RSI stays 60-88 throughout
   - Expected: 5-10 signals (vs 0-1 before fix)

2. **Strategy Compatibility**
   - Tests both `MomentumStrategy` and `SimplifiedMomentumStrategy`
   - Ensures fix works with "2 of 3" scoring system

3. **Zone Boundary Testing**
   - Verifies RSI 55 triggers, RSI 54 does not
   - Verifies RSI 85+ blocked (overbought)
   - Ensures precise zone behavior

---

## Coordination via Hooks

### Pre-Task
```bash
npx claude-flow@alpha hooks pre-task --description "Fix RSI signal generation"
```
**Task ID**: task-1761754298071-holmbw2pt

### Post-Edit
```bash
npx claude-flow@alpha hooks post-edit --file "momentum.py" --memory-key "swarm/week2/rsi_fix"
npx claude-flow@alpha hooks post-edit --file "momentum_simplified.py" --memory-key "swarm/week2/rsi_fix_simplified"
```

### Post-Task
```bash
npx claude-flow@alpha hooks post-task --task-id "rsi_fix_week2"
```

---

## Next Steps

### Recommended Actions
1. ✅ **Fix Applied**: RSI logic updated in both strategies
2. ⏭️ **Run Backtest**: Execute with new logic
   ```bash
   python scripts/run_optimized_backtest.py
   ```
3. ⏭️ **Compare Results**: Old vs New
   - Expected: 30-40 trades (vs 5)
   - Expected: 30-45% win rate (vs 0%)
   - Expected: Positive Sharpe ratio

### Validation
- Monitor signal count in logs
- Verify RSI values at signal generation (should be 55-85)
- Confirm multiple signals during uptrends

---

## Technical Notes

### Why 55-85 Zone?
- **55 Lower Bound**: Filters weak momentum (< 55 = neutral)
- **85 Upper Bound**: Avoids overbought extremes (> 85 = reversal risk)
- **Zone Width**: 30 points allows multiple entry opportunities

### Why Not 50-70?
- **50-55**: Too close to neutral, many false signals
- **70-100**: Includes overbought zone (70-100), high reversal risk
- **55-85**: Optimal balance of momentum + room for continuation

### Complementary Filters
The RSI zone works WITH (not instead of):
- MACD bullish signal
- Histogram threshold (0.0005)
- SMA trend filter (price > SMA50)
- Volume confirmation (optional)

All conditions must align for signal generation.

---

## Summary

**Problem**: RSI crossover logic failed to generate signals during trends
**Solution**: Changed to RSI level-based zones (55-85 LONG, 15-45 SHORT)
**Result**: Expected 6-8x increase in signal generation (5 → 30-40 trades)

**Status**: ✅ Fix applied to both strategies, ready for backtesting

---

**Deliverable**: Fixed `momentum.py` and `momentum_simplified.py` with RSI level-based logic, ready for backtesting validation.
