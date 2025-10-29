# Week 3 Priority 2: Testing Checklist

## Quick Reference
**Task**: RSI Zone Tightening to Reduce Overtrading
**Status**: ✅ Implementation Complete - Ready for Validation
**Agent**: Coder → Testing Agent

---

## What Changed (TL;DR)

| Component | Week 2 | Week 3 | Expected Impact |
|-----------|--------|--------|----------------|
| **LONG RSI Zone** | 55-85 | 60-80 | -20% LONG entries |
| **SHORT RSI Zone** | 15-45 | 20-40 | -20% SHORT entries |
| **SHORT Signals** | Enabled | Disabled | -100% SHORT trades |
| **Total Trades** | 69 | 35-45 | -35% total |
| **Win Rate** | 13.04% | 20-25% | +7-12 pp |
| **Sharpe Ratio** | -0.54 | 0.0-0.5 | +0.5-1.0 |

---

## Testing Priority Matrix

### 🔴 CRITICAL (Must Pass)
- [ ] **Total trade count**: 35-45 trades
- [ ] **LONG trades only**: 0 SHORT trades
- [ ] **RSI boundaries**: All LONG entries in 60-80 range
- [ ] **Win rate improvement**: >20% (vs 13.04% baseline)

### 🟡 HIGH PRIORITY (Should Pass)
- [ ] **Sharpe ratio**: >0.0 (vs -0.54 baseline)
- [ ] **Avg P&L per trade**: Positive improvement
- [ ] **Max drawdown**: Reduced vs Week 2
- [ ] **No regressions**: Existing functionality intact

### 🟢 NICE TO HAVE (Monitor)
- [ ] **RSI distribution**: Centered around 70 (LONG)
- [ ] **Signal concentration**: 65-75 sweet spot
- [ ] **Trade spacing**: Better temporal distribution
- [ ] **Transaction costs**: Reduced due to fewer trades

---

## Test Suite

### Test 1: Trade Count Validation ⚡ HIGH PRIORITY

**Command**:
```bash
python scripts/run_backtest.py --strategy momentum --start 2024-01-01 --end 2024-12-31
```

**Expected Output**:
```
Total Trades: 35-45
LONG Trades: 35-45
SHORT Trades: 0
```

**Success Criteria**:
- ✅ Total trades in 35-45 range
- ✅ 49-65% reduction from 69 trades
- ✅ Zero SHORT trades (disabled)

**Failure Actions**:
- If <30 trades: Zones too tight, widen by 5 points
- If >50 trades: Zones still too loose, investigate other filters
- If SHORT trades exist: Code error, verify SHORT disable logic

---

### Test 2: RSI Boundary Verification ⚡ CRITICAL

**Command**:
```bash
python scripts/analyze_signals.py --strategy momentum --metric rsi_distribution --output json
```

**Expected Output**:
```json
{
  "long_entries": {
    "min_rsi": 60.1,
    "max_rsi": 79.9,
    "mean_rsi": 69.5,
    "std_rsi": 5.2
  },
  "short_entries": {
    "count": 0
  }
}
```

**Success Criteria**:
- ✅ All LONG entries: 60 < RSI < 80
- ✅ No entries outside zone
- ✅ Mean RSI near 70 (optimal)
- ✅ Zero SHORT entries

**Failure Actions**:
- If entries outside 60-80: Code error, verify threshold logic
- If RSI < 60: Lower bound not enforced
- If RSI > 80: Upper bound not enforced

**Manual Verification**:
```python
import pandas as pd
results = pd.read_json('backtest_results.json')
long_signals = results[results['signal_type'] == 'LONG']
assert long_signals['rsi'].min() >= 60, "RSI below 60 found!"
assert long_signals['rsi'].max() <= 80, "RSI above 80 found!"
```

---

### Test 3: Performance Metrics ⚡ HIGH PRIORITY

**Command**:
```bash
python scripts/analyze_results.py --strategy momentum --compare-baseline week2 --output table
```

**Expected Output**:
```
Metric              | Week 2  | Week 3  | Change   | Status
--------------------|---------|---------|----------|--------
Total Trades        | 69      | 35-45   | -35%     | ✅ PASS
Win Rate            | 13.04%  | 20-25%  | +7-12pp  | ✅ PASS
Sharpe Ratio        | -0.54   | 0.0-0.5 | +0.5-1.0 | ✅ PASS
Avg Win             | TBD     | >Week2  | Improved | ✅ PASS
Avg Loss            | TBD     | ~Week2  | Similar  | ✅ PASS
Max Drawdown        | TBD     | <Week2  | Reduced  | ✅ PASS
```

**Success Criteria**:
- ✅ Win rate >20% (+7pp vs baseline)
- ✅ Sharpe ratio >0.0 (+0.5 vs baseline)
- ✅ Trade count 35-45 (within target)
- ✅ Avg win improved (stronger signals)

**Failure Actions**:
- If win rate <15%: Proceed to Priority 3 (take-profit adjustment)
- If Sharpe <-0.3: Investigate exit logic or position sizing
- If drawdown increased: Check stop-loss effectiveness

---

### Test 4: Signal Quality Analysis 🟢 NICE TO HAVE

**Command**:
```bash
python scripts/validate_signals.py --strategy momentum --verify-zones --output histogram
```

**Expected Output**:
```
LONG Entry RSI Distribution:
60-65: ████████ (20%)
65-70: ████████████████ (40%)
70-75: ████████████████ (40%)
75-80: ████ (10%)

Signal Quality Score: 8.5/10
```

**Success Criteria**:
- ✅ Peak at RSI 65-75 (sweet spot)
- ✅ <10% entries near boundaries (60-62, 78-80)
- ✅ No outliers outside 60-80
- ✅ Quality score >8.0

**Insights to Extract**:
- Are entries concentrated at strong momentum (65-75)?
- Are we avoiding marginal signals (60-62)?
- Are we avoiding overextended signals (78-80)?

---

### Test 5: Regression Testing 🟡 HIGH PRIORITY

**Command**:
```bash
pytest tests/unit/test_momentum_strategy.py -v
pytest tests/integration/test_backtest_momentum.py -v
```

**Expected Output**:
```
test_rsi_calculation ... PASSED
test_long_signal_generation ... PASSED
test_short_signal_disabled ... PASSED
test_exit_logic ... PASSED
test_position_sizing ... PASSED
========================= 5 passed =========================
```

**Success Criteria**:
- ✅ All existing tests pass
- ✅ No new errors introduced
- ✅ SHORT disable logic verified
- ✅ RSI zone enforcement verified

**Failure Actions**:
- If tests fail: Fix regressions before proceeding
- If SHORT test fails: Verify disable logic in lines 408-449
- If zone test fails: Verify thresholds in lines 375, 436

---

## Quick Validation Scripts

### 1-Minute Smoke Test
```bash
#!/bin/bash
echo "🔍 Week 3 RSI Zone Validation"

# Check code changes
echo "1. Checking LONG zone..."
grep -q "current\['rsi'\] > 60 and current\['rsi'\] < 80" src/strategies/momentum.py && echo "✅ LONG zone correct" || echo "❌ LONG zone error"

# Check SHORT zone
echo "2. Checking SHORT zone..."
grep -q "current\['rsi'\] < 40 and current\['rsi'\] > 20" src/strategies/momentum.py && echo "✅ SHORT zone correct" || echo "❌ SHORT zone error"

# Check SHORT disable
echo "3. Checking SHORT disable..."
grep -q "WEEK 3 FIX: SHORT SIGNALS DISABLED" src/strategies/momentum.py && echo "✅ SHORT disabled" || echo "❌ SHORT not disabled"

# Run quick backtest
echo "4. Running quick backtest..."
python scripts/run_backtest.py --strategy momentum --start 2024-11-01 --end 2024-11-30 --quick
```

### Trade Count Quick Check
```python
# scripts/quick_trade_count.py
import json

with open('data/backtest_results/latest.json', 'r') as f:
    results = json.load(f)

total_trades = results['metrics']['total_trades']
long_trades = results['metrics']['long_trades']
short_trades = results['metrics']['short_trades']

print(f"Total Trades: {total_trades}")
print(f"LONG Trades: {long_trades}")
print(f"SHORT Trades: {short_trades}")

# Validation
assert 35 <= total_trades <= 45, f"❌ Trade count out of range: {total_trades}"
assert short_trades == 0, f"❌ SHORT trades exist: {short_trades}"
assert long_trades == total_trades, f"❌ LONG count mismatch"

print("✅ All validations passed!")
```

### RSI Boundary Quick Check
```python
# scripts/quick_rsi_check.py
import pandas as pd

df = pd.read_json('data/backtest_results/signals.json')
long_signals = df[df['signal_type'] == 'LONG']

min_rsi = long_signals['metadata'].apply(lambda x: x['rsi']).min()
max_rsi = long_signals['metadata'].apply(lambda x: x['rsi']).max()

print(f"Min RSI at LONG entry: {min_rsi:.1f}")
print(f"Max RSI at LONG entry: {max_rsi:.1f}")

# Validation
assert min_rsi >= 60, f"❌ Min RSI below 60: {min_rsi:.1f}"
assert max_rsi <= 80, f"❌ Max RSI above 80: {max_rsi:.1f}"

print("✅ RSI boundaries enforced!")
```

---

## Success Criteria Summary

### ✅ MUST PASS (Critical)
1. **Trade Count**: 35-45 (currently 69)
2. **RSI Boundaries**: All entries in 60-80 (LONG)
3. **SHORT Disabled**: Zero SHORT trades
4. **Win Rate**: >20% (currently 13.04%)

### 🟡 SHOULD PASS (High Priority)
5. **Sharpe Ratio**: >0.0 (currently -0.54)
6. **Regression Tests**: All existing tests pass
7. **P&L Improvement**: Better avg returns per trade

### 🟢 NICE TO HAVE (Monitor)
8. **Signal Quality**: RSI centered around 70
9. **Drawdown**: Reduced vs Week 2
10. **Transaction Costs**: Lower due to fewer trades

---

## Failure Scenarios & Actions

| Scenario | Threshold | Action |
|----------|-----------|--------|
| **Too few trades** | <30 | Widen zones by 5 points (55-85, 15-45) |
| **Too many trades** | >50 | Investigate other filters (volume, MACD) |
| **Win rate low** | <15% | Proceed to Priority 3 (take-profit) |
| **Sharpe negative** | <-0.3 | Investigate exit logic |
| **RSI violations** | Any outside 60-80 | Code error, fix immediately |
| **SHORT trades exist** | >0 | Code error, verify disable logic |
| **Regression failures** | Any test fails | Fix before proceeding |

---

## Reporting Template

### Test Results Summary
```markdown
## Week 3 Priority 2 Test Results

**Test Date**: YYYY-MM-DD
**Tester**: [Name]
**Status**: ✅ PASS / ❌ FAIL / ⚠️ PARTIAL

### Critical Tests
- [ ] Trade Count: [actual] (target: 35-45) - [PASS/FAIL]
- [ ] RSI Boundaries: [violations] (target: 0) - [PASS/FAIL]
- [ ] SHORT Disabled: [count] (target: 0) - [PASS/FAIL]
- [ ] Win Rate: [actual]% (target: >20%) - [PASS/FAIL]

### Performance Metrics
| Metric | Week 2 | Week 3 | Change | Status |
|--------|--------|--------|--------|--------|
| Trades | 69 | [actual] | [%] | [✅/❌] |
| Win Rate | 13.04% | [actual]% | [pp] | [✅/❌] |
| Sharpe | -0.54 | [actual] | [Δ] | [✅/❌] |

### Issues Found
1. [Description] - [Severity: Critical/High/Low]
2. ...

### Recommendations
- [Action item 1]
- [Action item 2]

### Sign-off
- [ ] All critical tests passed
- [ ] Ready for Week 3 Priority 3
- [ ] Code review completed
```

---

## File Paths for Testing

**Strategy File**:
```
/mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/src/strategies/momentum.py
```

**Test Scripts**:
```
/mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/scripts/run_backtest.py
/mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/scripts/analyze_signals.py
/mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/scripts/validate_signals.py
```

**Results Directory**:
```
/mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/data/backtest_results/
```

**Documentation**:
```
/mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/docs/fixes/WEEK3_RSI_TIGHTENING.md
/mnt/c/Users/DaviCastroSamora/Documents/SamoraDC/RustAlgorithmTrading/docs/fixes/WEEK3_PRIORITY2_SUMMARY.md
```

---

## Contact & Coordination

**Memory Key**: `swarm/week3/rsi_tighten`
**Task ID**: `rsi_tighten_week3`
**Agent**: Coder → **Testing Agent**
**Status**: ✅ Ready for Validation

**Questions?** Check memory:
```bash
npx claude-flow@alpha hooks session-restore --session-id "swarm-week3"
```

---

**Week 3 Priority 2 Testing - START HERE** 🚀
