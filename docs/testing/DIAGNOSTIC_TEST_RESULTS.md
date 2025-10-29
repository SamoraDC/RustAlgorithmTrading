# Diagnostic Test Results - Signal Validation

**Test Date**: 2025-10-29
**Tester**: Hive Mind Tester Agent
**Objective**: Identify root causes of 0% win rate in backtesting

---

## 🔍 Executive Summary

**CRITICAL FINDING**: Momentum strategy is **NOT generating signals** despite having relaxed parameters and clear uptrend data.

### Test Results Overview

| Test Suite | Total | Passed | Failed | Status |
|------------|-------|--------|--------|--------|
| Signal Generation | 2 | 1 | 1 | ⚠️ CRITICAL |
| Signal Type Validation | 2 | 2 | 0 | ✅ PASS |
| Entry/Exit Matching | 2 | 1 | 1 | ⚠️ FAIL |
| Position Tracking | 2 | 1 | 1 | ⚠️ FAIL |
| Signal Metadata | 2 | 2 | 0 | ✅ PASS |
| **TOTAL** | **10** | **7** | **3** | **❌ FAILING** |

---

## ❌ Critical Failures

### 1. Momentum Strategy Generates 0 Signals (CRITICAL)

**Test**: `test_momentum_generates_signals_with_relaxed_params`

**Failure Details**:
```python
AssertionError: Momentum strategy generated 0 signals, expected >0.
This indicates signal generation is broken.
```

**Test Configuration**:
- RSI period: 14
- MACD histogram threshold: 0.0005 (RELAXED from 0.001)
- Volume confirmation: **DISABLED**
- Trailing stops: **DISABLED**
- Data: Clear uptrend from $100 → $150 over 61 days

**Technical Indicators Observed**:
```
Bar 49: TEST @ $139.86 | RSI=69.7, MACD=5.5893, Signal=5.6060, Hist=-0.01669, SMA50=$120.72
Bar 50: TEST @ $142.57 | RSI=69.1, MACD=5.6272, Signal=5.6102, Hist=0.01693, SMA50=$121.48
Bar 54: TEST @ $150.34 | RSI=88.5, MACD=5.8574, Signal=5.5952, Hist=0.26220, SMA50=$124.83
```

**Why Signals Are Missing**:

Looking at the Momentum strategy logic (lines 345-386 in `/src/strategies/momentum.py`):

```python
# Long signal conditions (ALL must be true):
rsi_long_cond = current['rsi'] > 50 and previous['rsi'] <= 50  # ❌ Requires RSI CROSS above 50
macd_long_cond = current['macd'] > current['macd_signal']       # ✅ Often true
hist_long_cond = current['macd_histogram'] > histogram_threshold # ✅ Often true
trend_long_cond = current['close'] > current['sma_50'] and not pd.isna(current['sma_50']) # ✅ Often true
volume_ok = True  # ✅ DISABLED in test

if (rsi_long_cond and macd_long_cond and hist_long_cond and trend_long_cond and volume_ok):
    signal_type = SignalType.LONG
```

**ROOT CAUSE**: The strategy requires **RSI to CROSS above 50** (from <=50 to >50), but in a strong uptrend:
- RSI quickly reaches 70-100 and **stays there**
- No RSI crossover occurs after the initial trend starts
- Result: **ZERO signals generated**

**Evidence from test output**:
- Bar 27-60: RSI ranges from 62.7 to 88.5, but NO crossover at 50
- Price went from $121 → $151 (+25% gain)
- MACD histogram was positive (0.1-0.7)
- Price was above SMA50
- **Yet 0 signals generated**

---

### 2. min_holding_period Parameter Not Defined

**Tests**: `test_momentum_entries_have_exits`, `test_momentum_position_tracking`

**Error**:
```python
TypeError: MomentumStrategy.__init__() got an unexpected keyword argument 'min_holding_period'
```

**Issue**: Tests use `min_holding_period=5` but this parameter is NOT in the `__init__` signature.

**Location in Code**: `/src/strategies/momentum.py` line 196 uses `min_holding_period`:
```python
min_holding_period = self.get_parameter('min_holding_period', 10)
```

But it's **not defined in `__init__`** (lines 32-94), so it defaults to 10 bars even when tests try to set it to 5.

**Impact**: Tests cannot properly control holding period for faster test execution.

---

## ✅ Passing Tests

### 1. Mean Reversion Signal Generation ✅

**Result**: Generated **4 signals** (2 entries + 2 exits)

**Signals Generated**:
```
- SHORT @ $104.94 on 2024-02-04 (price touched upper band)
- EXIT @ $107.94 on 2024-02-06 (stop-loss triggered, -2.86% loss)
- LONG @ $94.56 on 2024-02-20 (price touched lower band)
- EXIT @ $91.72 on 2024-02-22 (stop-loss triggered, -3.0% loss)
```

**Analysis**: Mean Reversion strategy works correctly and generates signals when:
- Price touches Bollinger Bands (oversold/overbought)
- Exit signals properly match entry signals

---

### 2. Signal Type Validation ✅

**Result**: All signals have valid types (`LONG`, `SHORT`, `EXIT`)

**Validation**:
- Momentum: 0 signals (all would be valid if generated)
- Mean Reversion: 4 signals, all have valid types

---

### 3. Signal Metadata ✅

**Result**: All signals contain required metadata fields

**Metadata Validated**:
- Entry signals: `rsi`, `macd`, `sma_20`, `upper_band`, `lower_band`
- Exit signals: `exit_reason`, `pnl_pct`, `entry_price`, `position_type`

---

## 🔬 Detailed Analysis

### Momentum Strategy Signal Generation Logic Issues

**Current Entry Logic** (lines 345-386):
```python
# Long signal: RSI crosses ABOVE 50 (momentum building) + MACD bullish + Price above SMA + Volume
if (rsi_long_cond and macd_long_cond and hist_long_cond and trend_long_cond and volume_ok):
    signal_type = SignalType.LONG
```

**Problem**: RSI crossover condition is **TOO RESTRICTIVE**

In a trending market:
1. Price starts at $100, RSI = 40
2. Day 1: Strong move up → RSI crosses 50 ✅ **SIGNAL GENERATED**
3. Day 2-60: Price continues up, RSI stays at 60-80
4. Days 2-60: **NO crossovers** → **NO MORE SIGNALS**

**Why This Fails**:
- Strategy is designed as a **crossover/reversal strategy**
- It's trying to catch momentum CHANGES, not momentum CONTINUATION
- In a strong trend (which is ideal for momentum trading), it generates **1 signal at most**

**Compare to Mean Reversion**:
Mean Reversion generates signals when price **IS AT** extreme levels (touches bands), not when it CROSSES.
- More signals in oscillating markets ✅
- Works as intended ✅

---

## 📊 Signal Count Analysis

### Momentum Strategy (CRITICAL ISSUE)
- **Uptrend data** (100 → 150): **0 signals**
- **Expected**: 5-10 signals in a 60-day uptrend
- **Actual**: 0 signals
- **Signal rate**: 0%

### Mean Reversion Strategy (WORKING)
- **Oscillating data** (100 ± 15): **4 signals**
- **Expected**: 2-6 signals in oscillating market
- **Actual**: 4 signals (2 entries, 2 exits)
- **Signal rate**: As expected ✅

---

## 🚨 Root Cause Summary

### Primary Issue: Momentum Strategy Design Flaw

**Symptom**: 0 signals generated in backtesting

**Root Cause**: Entry conditions require **RSI crossover at 50**, which:
1. Only occurs ONCE when trend starts
2. Never repeats in strong trending markets
3. Misses entire trend after initial crossover

**Evidence**:
- Test data: $100 → $150 uptrend (+50%)
- RSI: Stayed above 60 for entire period
- MACD: Stayed bullish for entire period
- Price: Always above SMA50
- **Signals generated: 0**

**Impact on Backtesting**:
- Strategy cannot enter positions
- No trades executed
- Win rate: 0% (no trades to win)
- Sharpe ratio: Undefined or negative

---

## 🔧 Recommended Fixes

### Fix 1: Change RSI Entry Condition (CRITICAL)

**Current** (lines 345-348):
```python
rsi_long_cond = current['rsi'] > 50 and previous['rsi'] <= 50  # Requires crossover
```

**Proposed Fix Option A** - RSI Level (No Crossover):
```python
rsi_long_cond = current['rsi'] > 55 and current['rsi'] < 85  # RSI in bullish zone but not overbought
```

**Proposed Fix Option B** - RSI Pullback:
```python
# Allow entries on pullbacks in uptrend
rsi_long_cond = (current['rsi'] > 50 and current['rsi'] < 70 and
                 previous['rsi'] > current['rsi'] - 5)  # RSI pulling back but still bullish
```

**Proposed Fix Option C** - Remove RSI from Entry (Use for Exits Only):
```python
# Use MACD and trend for entries, RSI only for exits
if (macd_long_cond and hist_long_cond and trend_long_cond and volume_ok):
    signal_type = SignalType.LONG
```

### Fix 2: Add min_holding_period to __init__

**File**: `/src/strategies/momentum.py`

**Add to `__init__` signature** (line 32):
```python
def __init__(
    self,
    rsi_period: int = 14,
    rsi_oversold: float = 30,
    rsi_overbought: float = 70,
    # ... other params ...
    min_holding_period: int = 10,  # ← ADD THIS
    parameters: Optional[Dict[str, Any]] = None
):
```

**Add to params dict** (line 72):
```python
params.update({
    'rsi_period': rsi_period,
    # ... other params ...
    'min_holding_period': min_holding_period,  # ← ADD THIS
})
```

### Fix 3: Add Logging for Blocked Signals

**Current**: Limited logging of why signals aren't generated

**Proposed** (lines 359-364):
```python
# Add MORE detailed logging of WHY signals are blocked
elif any([rsi_long_cond, macd_long_cond, hist_long_cond, trend_long_cond]):
    logger.debug(
        f"🟡 LONG signal BLOCKED: RSI_cross={rsi_long_cond}, "
        f"MACD={macd_long_cond}, Hist={hist_long_cond}, "
        f"Trend={trend_long_cond}, Volume={volume_ok}, "
        f"RSI={current['rsi']:.1f}, prev_RSI={previous['rsi']:.1f}"
    )
```

---

## 📈 Integration Test Results

### Tests Created:
1. ✅ `test_long_signal_generates_buy_order` - PASSED
2. ✅ `test_short_signal_generates_sell_order` - PASSED
3. ✅ `test_exit_signal_closes_position` - PASSED
4. ⏳ `test_momentum_strategy_full_flow` - **Not run** (strategy generates 0 signals)
5. ⏳ `test_mean_reversion_strategy_full_flow` - **Not run yet**

**Next Steps**: Once Momentum signal generation is fixed, run full integration tests.

---

## 🎯 Action Items for Hive Mind

### Immediate (Priority 1):
1. **Fix Momentum RSI entry condition** - Choose Option A, B, or C above
2. **Add `min_holding_period` parameter to `__init__`**
3. **Re-run diagnostic tests** to verify fix

### Short-term (Priority 2):
4. **Run full integration tests** with fixed strategy
5. **Backtest with real data** to verify win rate improves
6. **Add more logging** for signal generation debugging

### Long-term (Priority 3):
7. **Review all strategy entry conditions** for similar issues
8. **Add continuous integration tests** to catch regressions
9. **Create signal generation dashboard** for monitoring

---

## 📝 Test Files Delivered

1. `/tests/unit/test_signal_diagnostics.py` - Comprehensive unit tests for signal validation
2. `/tests/integration/test_backtest_signal_flow.py` - End-to-end integration tests
3. `/docs/testing/DIAGNOSTIC_TEST_RESULTS.md` - This detailed report

---

## 🔗 References

- **Momentum Strategy**: `/src/strategies/momentum.py` (lines 100-502)
- **Mean Reversion Strategy**: `/src/strategies/mean_reversion.py` (lines 93-292)
- **Portfolio Handler**: `/src/backtesting/portfolio_handler.py` (lines 92-278)
- **Test Output Log**: `/tests/logs/test_signal_diagnostics_output.log`

---

## 👥 Coordination Notes

**Shared with swarm via memory**:
- Key: `swarm/tester/diagnostics`
- Status: Tests completed, critical issue identified
- Next agent: **Coder** (to fix RSI entry condition)

**Recommended next steps**:
1. Coder: Implement RSI fix (Option A recommended for simplicity)
2. Reviewer: Review fix for correctness
3. Tester: Re-run all diagnostic tests
4. Architect: Evaluate if other strategies have similar issues

---

**End of Diagnostic Report**
