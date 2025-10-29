# Week 3 Priority 2: RSI Zone Tightening - Code Changes

## Overview
This document shows the exact code changes made to tighten RSI zones and reduce overtrading.

---

## Change 1: LONG Entry Zone Tightening

### Location
**File**: `/src/strategies/momentum.py`
**Lines**: 371-375

### Before (Week 2)
```python
# LONG CONDITIONS: Check each condition independently
rsi_long_cond = current['rsi'] > 55 and current['rsi'] < 85  # Bullish zone, not overbought
```

### After (Week 3)
```python
# LONG CONDITIONS: Check each condition independently
# WEEK 3 FIX: Tightened RSI zones to reduce overtrading
# Week 2: 55-85 LONG zone → 69 trades (too many, 73% above target)
# Week 3: 60-80 LONG zone → Target 35-45 trades (tighter thresholds)
# Rationale: Narrower zone captures stronger momentum, filters marginal signals
rsi_long_cond = current['rsi'] > 60 and current['rsi'] < 80  # Tightened bullish zone
```

### Impact
- **Zone width**: 30 points → 20 points (33% reduction)
- **Lower bound**: 55 → 60 (+5 points, filters weak signals)
- **Upper bound**: 85 → 80 (-5 points, prevents overextended entries)
- **Expected trade reduction**: ~20-30 fewer LONG entries

---

## Change 2: SHORT Entry Zone Tightening

### Location
**File**: `/src/strategies/momentum.py`
**Lines**: 428-436

### Before (Week 2)
```python
# SHORT CONDITIONS: Check each condition independently
# CRITICAL FIX Week 2: Changed from crossover to level-based logic
# OLD: current['rsi'] < 50 and previous['rsi'] >= 50 (only triggers once)
# NEW: RSI in bearish zone (15-45) allows signals throughout downtrend
rsi_short_cond = current['rsi'] < 45 and current['rsi'] > 15  # Bearish zone, not oversold
```

### After (Week 3)
```python
# SHORT CONDITIONS: Check each condition independently
# CRITICAL FIX Week 2: Changed from crossover to level-based logic
# OLD: current['rsi'] < 50 and previous['rsi'] >= 50 (only triggers once)
# NEW: RSI in bearish zone (15-45) allows signals throughout downtrend
# WEEK 3 FIX: Tightened RSI zones to reduce overtrading
# Week 2: 15-45 SHORT zone → 69 trades (too many, 73% above target)
# Week 3: 20-40 SHORT zone → Target 35-45 trades (tighter thresholds)
# Rationale: Narrower zone captures stronger momentum, filters marginal signals
rsi_short_cond = current['rsi'] < 40 and current['rsi'] > 20  # Tightened bearish zone
```

### Impact
- **Zone width**: 30 points → 20 points (33% reduction)
- **Lower bound**: 15 → 20 (+5 points, prevents oversold bounces)
- **Upper bound**: 45 → 40 (-5 points, filters weak signals)
- **Expected trade reduction**: ~10-15 fewer SHORT entries

**Note**: SHORT signals are currently **DISABLED** (lines 408-426) due to 72.7% loss rate in Week 2.

---

## Change 3: Class Docstring Update

### Location
**File**: `/src/strategies/momentum.py`
**Lines**: 14-40

### Before (Week 2)
```python
"""
Momentum Strategy using RSI and MACD indicators with comprehensive risk management

Generates signals based on momentum indicators alignment with proper exit logic,
stop-loss, and take-profit mechanisms.

Parameters:
    rsi_period: RSI period (default: 14)
    rsi_oversold: RSI oversold level (default: 30)
    rsi_overbought: RSI overbought level (default: 70)
    ema_fast: Fast EMA period for MACD (default: 12)
    ema_slow: Slow EMA period for MACD (default: 26)
    macd_signal: MACD signal line period (default: 9)
    position_size: Position size fraction (default: 0.15)
    stop_loss_pct: Stop loss percentage (default: 0.02 = 2%)
    take_profit_pct: Take profit percentage (default: 0.03 = 3% for 1.5:1 ratio)
"""
```

### After (Week 3)
```python
"""
Momentum Strategy using RSI and MACD indicators with comprehensive risk management

Generates signals based on momentum indicators alignment with proper exit logic,
stop-loss, and take-profit mechanisms.

WEEK 3 UPDATE - Tightened RSI Zones:
- LONG entries: RSI 60-80 (was 55-85) - Reduced zone by 40%
- SHORT entries: RSI 20-40 (was 15-45) - Reduced zone by 40%
- Target: 35-45 trades (was 69 trades in Week 2)
- Expected win rate improvement from filtering marginal signals

Parameters:
    rsi_period: RSI period (default: 14)
    rsi_oversold: RSI oversold level (default: 30) - Not used in entry logic
    rsi_overbought: RSI overbought level (default: 70) - Not used in entry logic
    ema_fast: Fast EMA period for MACD (default: 12)
    ema_slow: Slow EMA period for MACD (default: 26)
    macd_signal: MACD signal line period (default: 9)
    position_size: Position size fraction (default: 0.15)
    stop_loss_pct: Stop loss percentage (default: 0.02 = 2%)
    take_profit_pct: Take profit percentage (default: 0.03 = 3% for 1.5:1 ratio)

RSI Entry Zones (Week 3):
    LONG: 60 < RSI < 80 (captures strong bullish momentum)
    SHORT: 20 < RSI < 40 (captures strong bearish momentum)
"""
```

### Impact
- Documented Week 3 changes in class-level documentation
- Added explicit RSI entry zones section
- Clarified parameter usage
- Documented expected improvements

---

## Change 4: Comment Update in Condition Scoring

### Location
**File**: `/src/strategies/momentum.py`
**Line**: 382

### Before (Week 2)
```python
rsi_long_cond,      # 1. RSI in bullish zone (55-85)
```

### After (Week 3)
```python
rsi_long_cond,      # 1. RSI in bullish zone (60-80)
```

**Note**: This inline comment was updated to reflect the new zone boundaries.

---

## Supplementary Change: SHORT Signal Disabling

### Location
**File**: `/src/strategies/momentum.py`
**Lines**: 408-426

### Addition (Week 3)
```python
# ============================================================
# WEEK 3 FIX: SHORT SIGNALS DISABLED
# ============================================================
# CRITICAL FINDING FROM WEEK 2 BACKTESTING:
# - SHORT signals: 72.7% loss rate (8 of 11 trades lost)
# - Average loss: -3% to -5% per trade
# - Root cause: Momentum indicators LAG price movements
# - Issue: Strategy enters shorts RIGHT BEFORE prices bounce
#
# IMPACT OF DISABLING SHORTS:
# - Eliminate 72.7% losing trade type
# - Reduce total trades by ~15-20%
# - Improve overall win rate significantly
# - Reduce drawdown from failed shorts
#
# TODO WEEK 4: Re-enable shorts with market regime detection
# - Only short in confirmed bear markets
# - Add additional filters (VIX, trend strength, etc.)
# ============================================================
```

### Impact
- Documents critical decision to disable SHORT signals
- Explains 72.7% loss rate finding
- Provides rationale for disabling
- Sets roadmap for re-enabling in Week 4

**Lines 430-449**: SHORT signal logic now logs warnings instead of executing trades

---

## Summary of All Code Changes

### Files Modified
1. `/src/strategies/momentum.py` (1 file, 4 sections)

### Lines Changed
- **Lines 14-40**: Class docstring updated (26 lines)
- **Lines 371-375**: LONG zone tightened (5 lines)
- **Lines 408-426**: SHORT disable comment block added (19 lines)
- **Lines 428-436**: SHORT zone tightened (9 lines)
- **Line 382**: Inline comment updated (1 line)

### Total Changes
- **60 lines modified** (comments + code)
- **5 critical threshold changes**:
  1. LONG lower bound: 55 → 60
  2. LONG upper bound: 85 → 80
  3. SHORT lower bound: 15 → 20
  4. SHORT upper bound: 45 → 40
  5. SHORT signals: Enabled → Disabled

---

## Visual Diff Summary

```diff
# LONG Entry Zone
- rsi_long_cond = current['rsi'] > 55 and current['rsi'] < 85
+ rsi_long_cond = current['rsi'] > 60 and current['rsi'] < 80

# SHORT Entry Zone
- rsi_short_cond = current['rsi'] < 45 and current['rsi'] > 15
+ rsi_short_cond = current['rsi'] < 40 and current['rsi'] > 20

# Docstring
+ WEEK 3 UPDATE - Tightened RSI Zones:
+ - LONG entries: RSI 60-80 (was 55-85)
+ - SHORT entries: RSI 20-40 (was 15-45)
+ - Target: 35-45 trades (was 69 trades in Week 2)

+ RSI Entry Zones (Week 3):
+     LONG: 60 < RSI < 80
+     SHORT: 20 < RSI < 40
```

---

## Validation Commands

### Check LONG Zone Implementation
```bash
grep -n "rsi_long_cond" src/strategies/momentum.py
# Expected: Line 375 with "current['rsi'] > 60 and current['rsi'] < 80"
```

### Check SHORT Zone Implementation
```bash
grep -n "rsi_short_cond" src/strategies/momentum.py
# Expected: Line 436 with "current['rsi'] < 40 and current['rsi'] > 20"
```

### Verify Week 3 Comments
```bash
grep -n "WEEK 3" src/strategies/momentum.py
# Expected: Lines 20, 371, 402, 432
```

### Check Docstring Update
```bash
sed -n '14,40p' src/strategies/momentum.py
# Expected: Contains "WEEK 3 UPDATE" and "RSI Entry Zones"
```

---

## Rollback Instructions (If Needed)

If backtest results are unsatisfactory, revert zones to Week 2:

```python
# Rollback LONG zone
rsi_long_cond = current['rsi'] > 55 and current['rsi'] < 85  # Week 2 zone

# Rollback SHORT zone
rsi_short_cond = current['rsi'] < 45 and current['rsi'] > 15  # Week 2 zone
```

**Command**:
```bash
git diff src/strategies/momentum.py  # Review changes
git checkout HEAD~1 src/strategies/momentum.py  # Rollback file
```

---

## Next Steps

1. ✅ **Code changes complete**
2. ⏳ **Run backtest validation**
3. ⏳ **Verify trade count**: 35-45 (vs 69)
4. ⏳ **Check win rate**: >20% (vs 13.04%)
5. ⏳ **Validate Sharpe ratio**: >0.0 (vs -0.54)
6. ⏳ **Analyze RSI distribution**: All entries in 60-80 zone

---

**Week 3 Priority 2 Code Changes - COMPLETE** ✅
